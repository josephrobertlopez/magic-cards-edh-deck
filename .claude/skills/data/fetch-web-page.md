# fetch-web-page

Generic web page fetching with header customization and rate limiting.

## A2A Interface

**REQUEST Message**:
```json
{
  "urls": [
    "https://example.com/page1",
    "https://example.com/page2"
  ],
  "output_dir": "downloads/html",
  "options": {
    "headers": {
      "User-Agent": "Mozilla/5.0"
    },
    "rate_limit": 1,      // requests per second
    "timeout": 30,
    "follow_redirects": true
  }
}
```

**RESPONSE Message**:
```json
{
  "manifest_path": ".claude/state/web_fetch_manifest.json",
  "pages": [
    {
      "url": "https://example.com/page1",
      "html_path": "downloads/html/page1.html",
      "status": "success",
      "status_code": 200
    }
  ],
  "total": 2,
  "successful": 2,
  "failed": 0
}
```

## Domain-Agnostic Uses

- **Documentation Scraping**: Fetch API docs, GitHub READMEs
- **Research**: Fetch articles, papers, blog posts
- **Competitive Analysis**: Fetch competitor websites
- **Archive**: Backup web content
- **Content Aggregation**: Collect content from multiple sources

## Parameters

- `urls` (required): List of URLs to fetch
- `output_dir` (optional): Download directory (default: "downloads/html")
- `options` (optional): Fetch options (headers, rate limit, timeout)

## Usage

**Fetch single page**:
```bash
/data/fetch-web-page https://example.com/article
```

**Fetch multiple pages**:
```bash
/data/fetch-web-page \
  --urls urls.txt \
  --output downloads/html \
  --rate-limit 1
```

**Fetch with custom headers**:
```bash
/data/fetch-web-page \
  --url https://api.example.com/docs \
  --header "Authorization: Bearer TOKEN" \
  --output api-docs
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import os
import requests
import time
from pathlib import Path
import json
from urllib.parse import urlparse

def sanitize_filename(url):
    """Convert URL to safe filename"""
    parsed = urlparse(url)
    filename = parsed.path.replace('/', '_').strip('_')
    if not filename:
        filename = parsed.netloc.replace('.', '_')
    return filename + '.html'

def fetch_page(url, options):
    """Fetch single web page"""
    headers = options.get('headers', {'User-Agent': 'Mozilla/5.0'})
    timeout = options.get('timeout', 30)
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        return {
            'url': url,
            'html': response.text,
            'status_code': response.status_code,
            'success': True
        }
    except Exception as e:
        return {
            'url': url,
            'error': str(e),
            'success': False
        }

def main():
    if len(sys.argv) < 2:
        print("Error: urls required", file=sys.stderr)
        sys.exit(1)
    
    urls = []
    if os.path.isfile(sys.argv[1]):
        with open(sys.argv[1]) as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = [sys.argv[1]]
    
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads/html"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    options = {
        'rate_limit': 1,  # 1 request per second
        'timeout': 30
    }
    
    manifest = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total': len(urls),
        'successful': 0,
        'failed': 0,
        'pages': []
    }
    
    for url in urls:
        print(f"📥 Fetching: {url}")
        
        result = fetch_page(url, options)
        
        if result['success']:
            filename = sanitize_filename(url)
            html_path = os.path.join(output_dir, filename)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(result['html'])
            
            manifest['pages'].append({
                'url': url,
                'html_path': html_path,
                'status': 'success',
                'status_code': result['status_code']
            })
            manifest['successful'] += 1
            print(f"  ✅ Saved: {html_path}")
        else:
            manifest['pages'].append({
                'url': url,
                'status': 'failed',
                'error': result['error']
            })
            manifest['failed'] += 1
            print(f"  ❌ Failed: {result['error']}")
        
        time.sleep(1.0 / options['rate_limit'])
    
    # Save manifest
    Path(".claude/state").mkdir(parents=True, exist_ok=True)
    manifest_path = ".claude/state/web_fetch_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n📊 Results: {manifest['successful']}/{manifest['total']} pages fetched")
    print(manifest_path)
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Error Codes

- `0`: Success
- `1`: No URLs provided
