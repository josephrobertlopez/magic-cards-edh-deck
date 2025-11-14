# fetch-cards

Fetch Magic: The Gathering card images from Scryfall API and generate JSON manifest.

## Usage

```
/fetch-cards <decklist_file>
```

**Parameters**:
- `decklist_file`: Path to text file containing card names (one per line)

**Output**:
- Downloads card images to `images/` directory
- Generates JSON manifest at `.claude/state/fetch_manifest.json`

**Examples**:
```
/fetch-cards test_decks/phase1_sample.txt
/fetch-cards my_edh_deck.txt
```

## Implementation

```python
#!/usr/bin/env python3
import requests
import os
import time
import urllib.parse
import json
from pathlib import Path
from PIL import Image
import io

def sanitize_filename(name):
    """Sanitize card name for use as filename (FR-011)"""
    name = name.replace("/", "_")
    name = name.replace(":", "_")
    for char in ['?', '*', '<', '>', '|', '"', "'"]:
        name = name.replace(char, "")
    return name.strip()

def validate_image(image_data):
    """Validate image file integrity (FR-016)"""
    try:
        img = Image.open(io.BytesIO(image_data))
        img.verify()  # Verify it's a valid image
        return len(image_data) > 1000  # Basic size check
    except:
        return False

def download_card_with_retry(card_name, output_dir="images", max_retries=3):
    """
    Download card image with exponential backoff retry (FR-013, FR-016)
    Returns: (success: bool, path: str|None, reason: str|None)
    """
    delays = [0.1, 0.2, 0.4]  # Exponential backoff: 100ms, 200ms, 400ms

    for attempt in range(max_retries):
        try:
            clean_name = card_name.strip()

            # Handle double-faced cards (FR-002 clarification: download both faces)
            is_dfc = "//" in clean_name
            if is_dfc:
                front_name, back_name = [part.strip() for part in clean_name.split("//")]
                search_name = front_name
            else:
                search_name = clean_name

            # URL encode and query Scryfall (fuzzy search per FR-003)
            encoded_name = urllib.parse.quote(search_name)
            api_url = f"https://api.scryfall.com/cards/named?fuzzy={encoded_name}"

            print(f"  🔍 [{attempt+1}/{max_retries}] Searching: {card_name}")

            response = requests.get(api_url, timeout=10)

            if response.status_code != 200:
                if attempt < max_retries - 1:
                    time.sleep(delays[attempt])
                    continue
                # FR-014: Fail workflow on unfound cards
                return (False, None, f"Card not found (HTTP {response.status_code})")

            card_data = response.json()

            # Get image URLs
            image_urls = card_data.get('image_uris', {})

            # Handle double-faced cards - get both faces
            faces_to_download = []
            if not image_urls and 'card_faces' in card_data:
                # Double-faced card
                for i, face in enumerate(card_data['card_faces']):
                    face_urls = face.get('image_uris', {})
                    if face_urls:
                        face_name = f"{sanitize_filename(card_name)}_face{i+1}"
                        faces_to_download.append((face_name, face_urls))
            else:
                # Single-faced card
                if image_urls:
                    faces_to_download.append((sanitize_filename(card_name), image_urls))

            if not faces_to_download:
                return (False, None, "No image URLs found")

            # Download all faces
            Path(output_dir).mkdir(exist_ok=True)
            downloaded_paths = []

            for face_name, face_urls in faces_to_download:
                # Prefer normal > large > small quality
                if 'normal' in face_urls:
                    image_url = face_urls['normal']
                elif 'large' in face_urls:
                    image_url = face_urls['large']
                elif 'small' in face_urls:
                    image_url = face_urls['small']
                else:
                    continue

                print(f"    📥 Downloading {face_name}...")
                img_response = requests.get(image_url, timeout=30)

                if img_response.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(delays[attempt])
                        break  # Retry entire card
                    return (False, None, "Image download failed")

                # Validate image (FR-016)
                if not validate_image(img_response.content):
                    if attempt < max_retries - 1:
                        time.sleep(delays[attempt])
                        break  # Retry
                    return (False, None, "Image validation failed (corrupted)")

                # Save image
                filename = f"{face_name}.jpg"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(img_response.content)

                downloaded_paths.append(filepath)
                print(f"    ✅ Saved: {filename}")

            if len(downloaded_paths) == len(faces_to_download):
                # All faces downloaded successfully
                time.sleep(0.1)  # Rate limiting (FR-004)
                return (True, downloaded_paths[0] if len(downloaded_paths) == 1 else downloaded_paths, None)

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
                continue
            return (False, None, f"Exception: {str(e)}")

    return (False, None, "Max retries exceeded")

def main(decklist_file):
    """Main skill execution"""
    import datetime

    # Validate input file exists
    if not os.path.exists(decklist_file):
        print(f"❌ Error: Decklist file not found: {decklist_file}")
        return 1

    # Read decklist
    with open(decklist_file, 'r') as f:
        card_names = [line.strip() for line in f if line.strip()]

    print(f"🎴 Fetching {len(card_names)} cards from Scryfall...")
    print("=" * 60)

    # Track results
    manifest = {
        "timestamp": datetime.datetime.now().isoformat(),
        "decklist_path": decklist_file,
        "total_cards": len(card_names),
        "successful": 0,
        "failed": 0,
        "cards": []
    }

    failed_cards = []

    for i, card_name in enumerate(card_names, 1):
        print(f"\n[{i}/{len(card_names)}] {card_name}")

        success, path, reason = download_card_with_retry(card_name)

        if success:
            manifest["successful"] += 1
            manifest["cards"].append({
                "name": card_name,
                "path": path if isinstance(path, str) else path[0],  # Primary path
                "status": "success"
            })
        else:
            manifest["failed"] += 1
            failed_cards.append(card_name)
            manifest["cards"].append({
                "name": card_name,
                "status": "failed",
                "reason": reason
            })

            # FR-014: Fail workflow on unfound cards
            print(f"\n❌ FATAL: Card '{card_name}' could not be downloaded")
            print(f"   Reason: {reason}")
            print(f"\n⚠️  Workflow stopped. Please fix the decklist and try again.")

            # Save partial manifest
            Path(".claude/state").mkdir(parents=True, exist_ok=True)
            with open(".claude/state/fetch_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)

            return 1  # Exit with error

    # Save manifest
    Path(".claude/state").mkdir(parents=True, exist_ok=True)
    manifest_path = ".claude/state/fetch_manifest.json"

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 60)
    print(f"🎉 All cards fetched successfully!")
    print(f"✅ Successful: {manifest['successful']}/{manifest['total_cards']}")
    print(f"💾 Manifest saved: {manifest_path}")

    return 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: fetch-cards <decklist_file>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
```

## Error Handling

**Common Errors**:
- `Decklist file not found`: Check file path is correct
- `Card not found (HTTP 404)`: Card name misspelled or doesn't exist
- `Max retries exceeded`: Network issues or Scryfall API unavailable
- `Image validation failed`: Downloaded image is corrupted

**Fail-Fast Behavior** (FR-014):
- Workflow stops on first unfound card
- Partial manifest is saved
- User must fix decklist before continuing

## Manifest Schema

Output JSON structure (`.claude/state/fetch_manifest.json`):

```json
{
  "timestamp": "2025-11-06T10:30:00Z",
  "decklist_path": "test_decks/phase1_sample.txt",
  "total_cards": 10,
  "successful": 9,
  "failed": 1,
  "cards": [
    {
      "name": "Lightning Bolt",
      "path": "images/Lightning_Bolt.jpg",
      "status": "success"
    },
    {
      "name": "Invalid Card",
      "status": "failed",
      "reason": "Card not found (HTTP 404)"
    }
  ]
}
```

## Requirements Satisfied

- **FR-001**: Fetches card images from Scryfall using card names
- **FR-002**: Supports double-faced cards (downloads both faces)
- **FR-003**: Uses fuzzy name matching
- **FR-004**: Respects rate limits (100ms between requests)
- **FR-011**: Sanitizes filenames
- **FR-012**: Batch processes entire decklists
- **FR-013**: Retries with exponential backoff (100ms, 200ms, 400ms)
- **FR-014**: Fails workflow on unfound cards
- **FR-016**: Validates image integrity, retries corrupted downloads
