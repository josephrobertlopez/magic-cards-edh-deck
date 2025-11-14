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
        'rate_limit': 1,
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
    
    # Output JSON for A2A
    output = {
        "status": "success",
        "manifest_path": manifest_path,
        "pages": manifest['pages'],
        "total": manifest['total'],
        "successful": manifest['successful'],
        "failed": manifest['failed']
    }
    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
