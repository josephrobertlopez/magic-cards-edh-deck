#!/usr/bin/env python3
"""
Fetch Web Content Skill

Fetches raw content from a URL and saves it.
Does NOT parse - just fetches and returns raw content.

Protocol-first: Outputs A2A-compatible JSON.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NETWORK_ERROR

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


def fetch_content(url: str, output_file: str = None) -> Dict[str, Any]:
    """
    Fetch raw content from URL.

    Args:
        url: URL to fetch
        output_file: Optional file to save raw content

    Returns:
        Dict with url, content, content_length, output_file
    """
    print(f"\n🌐 Fetching: {url}", file=sys.stderr)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        content = response.text
        content_length = len(content)

        print(f"✅ Fetched {content_length} bytes", file=sys.stderr)
        print(f"   Status: {response.status_code}", file=sys.stderr)
        print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}", file=sys.stderr)

        # Save to file if requested
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"💾 Saved to: {output_file}", file=sys.stderr)

        return {
            "url": url,
            "content": content,
            "content_length": content_length,
            "output_file": output_file,
            "status_code": response.status_code,
            "content_type": response.headers.get('Content-Type', 'unknown')
        }

    except requests.RequestException as e:
        raise Exception(f"HTTP request failed: {str(e)}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Fetch raw content from URL'
    )
    parser.add_argument(
        '--url',
        required=True,
        help='URL to fetch'
    )
    parser.add_argument(
        '--output',
        help='Output file for raw content'
    )

    args = parser.parse_args()

    try:
        result = fetch_content(args.url, args.output)

        # Print summary
        print("\n" + "=" * 70, file=sys.stderr)
        print("✅ CONTENT FETCH COMPLETE", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n📍 URL: {result['url']}", file=sys.stderr)
        print(f"📦 Size: {result['content_length']} bytes", file=sys.stderr)
        print(f"📝 Type: {result['content_type']}", file=sys.stderr)

        if result.get('output_file'):
            print(f"💾 Saved: {result['output_file']}", file=sys.stderr)

        print("=" * 70, file=sys.stderr)

        # Output A2A protocol JSON to stdout
        format_success_output(result)

    except Exception as e:
        format_error_output(
            f"Content fetch failed: {str(e)}",
            exit_code=NETWORK_ERROR,
            context={"url": args.url, "exception": str(e)}
        )


if __name__ == '__main__':
    main()
