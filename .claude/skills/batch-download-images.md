# batch-download-images

Download images from URLs with rate limiting, retry logic, and manifest caching.

## Usage

```
/batch-download-images <urls.json> <output_dir> [--rate-limit 10]
```

**Parameters**:
- `urls.json`: JSON file with array of `{name, url}` objects (required)
- `output_dir`: Directory to save images (required)
- `--rate-limit`: Maximum requests per second (optional, default: 10)

**Output**:
- Downloaded images in `output_dir/`
- Manifest JSON tracking success/failure
- Progress indicators with ✅/❌ status

**Examples**:
```
/batch-download-images card_urls.json images/
/batch-download-images urls.json output/ --rate-limit 5
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

def sanitize_filename(name):
    """Sanitize name for use as filename"""
    name = name.replace("/", "_")
    name = name.replace(":", "_")
    for char in ['?', '*', '<', '>', '|', '"', "'"]:
        name = name.replace(char, "")
    return name.strip()

def download_with_retry(url, output_path, max_retries=3):
    """
    Download file with exponential backoff retry.

    Args:
        url: URL to download from
        output_path: Where to save the file
        max_retries: Maximum retry attempts

    Returns:
        Tuple of (success: bool, error: str|None)
    """
    delays = [0.1, 0.2, 0.4]  # Exponential backoff

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                if attempt < max_retries - 1:
                    time.sleep(delays[attempt])
                    continue
                return (False, f"HTTP {response.status_code}")

            # Validate content type (should be image)
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                return (False, f"Invalid content type: {content_type}")

            # Validate minimum file size
            if len(response.content) < 1000:
                return (False, "File too small (likely error page)")

            # Save file
            with open(output_path, 'wb') as f:
                f.write(response.content)

            return (True, None)

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
                continue
            return (False, "Timeout")

        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
                continue
            return (False, "Connection error")

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
                continue
            return (False, str(e))

    return (False, "Max retries exceeded")

def batch_download(urls_file, output_dir, rate_limit=10):
    """
    Batch download images with rate limiting.

    Args:
        urls_file: JSON file with [{name, url}, ...]
        output_dir: Directory to save images
        rate_limit: Max requests per second

    Returns:
        Dictionary with download statistics
    """
    urls_file = Path(urls_file).resolve()
    output_dir = Path(output_dir).resolve()

    if not urls_file.exists():
        raise FileNotFoundError(f"URLs file not found: {urls_file}")

    # Load URLs
    with open(urls_file, 'r') as f:
        urls_data = json.load(f)

    if not isinstance(urls_data, list):
        raise ValueError("URLs file must contain JSON array")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track results
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "source": str(urls_file),
        "total": len(urls_data),
        "successful": 0,
        "failed": 0,
        "items": []
    }

    # Rate limiting
    delay_between_requests = 1.0 / rate_limit

    print(f"📥 Batch Image Downloader")
    print("=" * 70)
    print(f"📄 Source: {urls_file}")
    print(f"📁 Output: {output_dir}")
    print(f"⏱️  Rate limit: {rate_limit} req/sec")
    print(f"🎴 Total items: {len(urls_data)}")
    print("=" * 70)
    print()

    # Download each item
    for i, item in enumerate(urls_data, 1):
        if not isinstance(item, dict) or 'url' not in item or 'name' not in item:
            print(f"[{i}/{len(urls_data)}] ❌ Invalid item (missing 'url' or 'name')")
            manifest["failed"] += 1
            manifest["items"].append({
                "index": i - 1,
                "status": "failed",
                "error": "Invalid item structure"
            })
            continue

        name = item['name']
        url = item['url']

        # Sanitize filename
        filename = sanitize_filename(name) + ".jpg"
        output_path = output_dir / filename

        print(f"[{i}/{len(urls_data)}] {name[:40]:<40}", end=" ")

        success, error = download_with_retry(url, output_path)

        if success:
            print("✅")
            manifest["successful"] += 1
            manifest["items"].append({
                "index": i - 1,
                "name": name,
                "status": "success",
                "path": str(output_path),
                "url": url
            })
        else:
            print(f"❌ ({error})")
            manifest["failed"] += 1
            manifest["items"].append({
                "index": i - 1,
                "name": name,
                "status": "failed",
                "error": error,
                "url": url
            })

        # Rate limiting
        time.sleep(delay_between_requests)

    # Save manifest
    manifest_path = output_dir / "download_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print()
    print("=" * 70)
    print(f"📊 Results: {manifest['successful']}/{manifest['total']} successful")
    print(f"💾 Manifest: {manifest_path}")
    print("=" * 70)

    return manifest

def main():
    """Main skill execution"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch download images with rate limiting and retry"
    )
    parser.add_argument("urls_file", help="JSON file with [{name, url}, ...]")
    parser.add_argument("output_dir", help="Output directory for images")
    parser.add_argument("--rate-limit", type=int, default=10,
                        help="Max requests per second (default: 10)")

    args = parser.parse_args()

    try:
        manifest = batch_download(args.urls_file, args.output_dir, args.rate_limit)

        if manifest['failed'] > 0:
            print(f"\\n⚠️  {manifest['failed']} downloads failed")
            return 1

        print("\\n🎉 All downloads successful!")
        return 0

    except FileNotFoundError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except ValueError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Input JSON Format

```json
[
  {
    "name": "Lightning Bolt",
    "url": "https://cards.scryfall.io/normal/front/a/b/abc123.jpg"
  },
  {
    "name": "Counterspell",
    "url": "https://cards.scryfall.io/normal/front/d/e/def456.jpg"
  }
]
```

**Required fields**:
- `name`: Display name for the item (used for filename)
- `url`: Full URL to download from

## Output Example

```
📥 Batch Image Downloader
======================================================================
📄 Source: card_urls.json
📁 Output: images/
⏱️  Rate limit: 10 req/sec
🎴 Total items: 100
======================================================================

[1/100] Lightning Bolt                         ✅
[2/100] Counterspell                           ✅
[3/100] Fake Card XYZ                          ❌ (HTTP 404)
[4/100] Goblin Guide                           ✅
...

======================================================================
📊 Results: 97/100 successful
💾 Manifest: images/download_manifest.json
======================================================================

⚠️  3 downloads failed
```

## Manifest Output

Generated manifest at `output_dir/download_manifest.json`:

```json
{
  "timestamp": "2025-11-07T15:30:00Z",
  "source": "/path/to/card_urls.json",
  "total": 100,
  "successful": 97,
  "failed": 3,
  "items": [
    {
      "index": 0,
      "name": "Lightning Bolt",
      "status": "success",
      "path": "/path/to/images/Lightning_Bolt.jpg",
      "url": "https://..."
    },
    {
      "index": 2,
      "name": "Fake Card XYZ",
      "status": "failed",
      "error": "HTTP 404",
      "url": "https://..."
    }
  ]
}
```

## Error Handling

**Common Errors**:

**`URLs file not found`**:
```
❌ Error: URLs file not found: /path/to/urls.json
```

**`Invalid JSON structure`**:
```
❌ Error: URLs file must contain JSON array
```

**`Invalid item (missing fields)`**:
```
[5/100] ❌ Invalid item (missing 'url' or 'name')
```

**`HTTP errors`**:
```
[12/100] Card Name                              ❌ (HTTP 404)
[23/100] Card Name                              ❌ (HTTP 500)
```

**`Timeout`**:
```
[45/100] Card Name                              ❌ (Timeout)
```

## Features

**Rate Limiting**:
- Configurable requests per second (default: 10)
- Automatic delay between requests
- Prevents API rate limit violations

**Retry Logic**:
- 3 attempts per download
- Exponential backoff (100ms, 200ms, 400ms)
- Automatic retry on transient failures

**Content Validation**:
- Checks Content-Type header (must be image/*)
- Validates minimum file size (>1000 bytes)
- Prevents saving error pages as images

**Progress Tracking**:
- Real-time progress indicators (N/M)
- Visual success/failure markers (✅/❌)
- Final statistics summary

**Manifest Generation**:
- Tracks success/failure for each item
- Saves metadata for retry/debugging
- Preserves original URLs and names

## Use Cases

**Scryfall Card Batch Download**:
- Download card art for entire decks
- Batch fetch with Scryfall's rate limits respected
- Cache images for offline use

**General Image Collections**:
- Download product images from API
- Batch fetch profile pictures
- Archive web images locally

**Content Migration**:
- Move images from old CDN to new storage
- Batch download for backup
- Rehost images locally

## Exit Codes

- `0`: All downloads successful
- `1`: Some downloads failed (partial success)
