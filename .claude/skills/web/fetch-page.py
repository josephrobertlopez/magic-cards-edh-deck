#!/usr/bin/env python3
"""
Web Page Fetch Skill

Fetches content from specific URLs and extracts structured information.
Useful for downloading decklists, card data, or other resources from known sources.

Protocol-first: Outputs A2A-compatible JSON for skill chaining.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, COMMAND_ERROR


def fetch_url(
    url: str,
    extract_type: str = "text",
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch content from URL.

    Args:
        url: URL to fetch
        extract_type: Type of extraction (text, decklist, json, html)
        output_file: Optional file to save raw content

    Returns:
        Dict with url, extract_type, content_preview
    """
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid URL format: {url}")

    # Determine source type for optimized extraction
    source_type = "generic"
    if "scryfall.com" in url:
        source_type = "scryfall"
    elif "edhrec.com" in url:
        source_type = "edhrec"
    elif "mtggoldfish.com" in url:
        source_type = "mtggoldfish"
    elif "moxfield.com" in url or "archidekt.com" in url:
        source_type = "deck_builder"

    print(f"\n🌐 Fetching URL: {url}", file=sys.stderr)
    print(f"   Source Type: {source_type}", file=sys.stderr)
    print(f"   Extract As: {extract_type}", file=sys.stderr)

    return {
        "url": url,
        "source_type": source_type,
        "extract_type": extract_type,
        "output_file": output_file,
        "note": "Content will be fetched by MCP server with WebFetch tool"
    }


def fetch_decklist(
    url: str,
    output_format: str = "txt"
) -> Dict[str, Any]:
    """
    Fetch decklist from URL and extract card names.

    Args:
        url: URL of decklist page
        output_format: Output format (txt, json, yaml)

    Returns:
        Dict with decklist extraction parameters
    """
    print(f"\n📋 Fetching Decklist: {url}", file=sys.stderr)
    print(f"   Output Format: {output_format}", file=sys.stderr)

    # Determine deck builder platform
    platform = "unknown"
    if "moxfield.com" in url:
        platform = "moxfield"
    elif "archidekt.com" in url:
        platform = "archidekt"
    elif "mtggoldfish.com" in url:
        platform = "mtggoldfish"
    elif "edhrec.com" in url:
        platform = "edhrec"

    return {
        "url": url,
        "fetch_type": "decklist",
        "platform": platform,
        "output_format": output_format,
        "extraction_strategy": f"{platform}_decklist_parser",
        "note": f"Will extract card list from {platform} deck page"
    }


def fetch_card_data(
    card_name: str = None,
    scryfall_id: str = None
) -> Dict[str, Any]:
    """
    Fetch card data from Scryfall API.

    Args:
        card_name: Card name to look up
        scryfall_id: Scryfall ID for direct lookup

    Returns:
        Dict with Scryfall API parameters
    """
    if not card_name and not scryfall_id:
        raise ValueError("Must provide either card_name or scryfall_id")

    if scryfall_id:
        url = f"https://api.scryfall.com/cards/{scryfall_id}"
        print(f"\n🎴 Fetching Card by ID: {scryfall_id}", file=sys.stderr)
    else:
        # URL encode card name
        encoded_name = card_name.replace(" ", "+")
        url = f"https://api.scryfall.com/cards/named?exact={encoded_name}"
        print(f"\n🎴 Fetching Card: {card_name}", file=sys.stderr)

    print(f"   API: {url}", file=sys.stderr)

    return {
        "url": url,
        "fetch_type": "card_data",
        "api": "scryfall",
        "card_name": card_name,
        "scryfall_id": scryfall_id,
        "note": "Will fetch structured card data from Scryfall API"
    }


def main():
    """CLI entry point for web fetch skill"""
    parser = argparse.ArgumentParser(
        description='Fetch content from URLs (decklists, card data, pages)'
    )

    # Fetch type
    fetch_group = parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument(
        '--url',
        help='Generic URL to fetch'
    )
    fetch_group.add_argument(
        '--decklist-url',
        help='Fetch decklist from deck builder URL'
    )
    fetch_group.add_argument(
        '--card-name',
        help='Fetch card data from Scryfall by name'
    )
    fetch_group.add_argument(
        '--scryfall-id',
        help='Fetch card data from Scryfall by ID'
    )

    # Optional parameters
    parser.add_argument(
        '--extract-type',
        default='text',
        choices=['text', 'decklist', 'json', 'html'],
        help='Type of content extraction (default: text)'
    )
    parser.add_argument(
        '--output-format',
        default='txt',
        choices=['txt', 'json', 'yaml'],
        help='Output format for decklists (default: txt)'
    )
    parser.add_argument(
        '--output',
        help='Output file for results JSON (default: stdout)'
    )

    args = parser.parse_args()

    try:
        # Determine fetch type and execute
        if args.url:
            result = fetch_url(args.url, args.extract_type)
        elif args.decklist_url:
            result = fetch_decklist(args.decklist_url, args.output_format)
        elif args.card_name or args.scryfall_id:
            result = fetch_card_data(args.card_name, args.scryfall_id)
        else:
            raise ValueError("No fetch parameters provided")

        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Fetch params saved to: {args.output}", file=sys.stderr)

        # Print result summary
        print("\n" + "=" * 70, file=sys.stderr)
        print("🌐 WEB FETCH PREPARED", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n📍 URL: {result['url']}", file=sys.stderr)
        print(f"   Type: {result.get('fetch_type', 'generic')}", file=sys.stderr)

        if result.get('platform'):
            print(f"   Platform: {result['platform']}", file=sys.stderr)
        if result.get('api'):
            print(f"   API: {result['api']}", file=sys.stderr)

        if result.get('note'):
            print(f"\n📌 {result['note']}", file=sys.stderr)

        print("=" * 70, file=sys.stderr)

        # Output to stdout for skill chaining (A2A protocol)
        format_success_output(result)

    except Exception as e:
        format_error_output(
            f"Web fetch preparation failed: {str(e)}",
            exit_code=COMMAND_ERROR,
            context={
                "url": args.url,
                "card_name": args.card_name,
                "exception": str(e)
            }
        )


if __name__ == '__main__':
    main()
