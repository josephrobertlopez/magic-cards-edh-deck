#!/usr/bin/env python3
"""
Generic HTML Content Extractor

Extracts structured content from HTML using CSS selectors.
Domain-agnostic: Works for decklists, recipes, products, articles, etc.

Protocol-first: User provides selector, we extract content.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, COMMAND_ERROR


def extract_list(soup: BeautifulSoup, selector: str) -> List[str]:
    """Extract list items using CSS selector."""
    items = []
    for element in soup.select(selector):
        text = element.get_text(strip=True)
        if text:
            items.append(text)
    return items


def extract_table(soup: BeautifulSoup, selector: str) -> List[Dict[str, str]]:
    """Extract table rows as list of dicts."""
    table = soup.select_one(selector)
    if not table:
        return []
    
    rows = []
    headers = [th.get_text(strip=True) for th in table.select('th')]
    
    for row in table.select('tr'):
        cells = [td.get_text(strip=True) for td in row.select('td')]
        if cells:
            if headers:
                rows.append(dict(zip(headers, cells)))
            else:
                rows.append({"col" + str(i): cell for i, cell in enumerate(cells)})
    
    return rows


def extract_content(
    html_content: str,
    extract_type: str,
    selector: str
) -> Dict[str, Any]:
    """
    Extract content from HTML.
    
    Args:
        html_content: Raw HTML string
        extract_type: 'list' | 'table' | 'article' | 'structured'
        selector: CSS selector for target elements
    
    Returns:
        Dict with extracted content
    """
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except Exception as e:
        soup = BeautifulSoup(html_content, 'html.parser')
    
    if extract_type == 'list':
        items = extract_list(soup, selector)
        return {
            'type': 'list',
            'items': items,
            'count': len(items)
        }
    
    elif extract_type == 'table':
        rows = extract_table(soup, selector)
        return {
            'type': 'table',
            'rows': rows,
            'count': len(rows)
        }
    
    elif extract_type == 'article':
        element = soup.select_one(selector)
        if element:
            text = element.get_text(separator='\n', strip=True)
            return {
                'type': 'article',
                'content': text,
                'length': len(text)
            }
        return {'type': 'article', 'content': '', 'length': 0}
    
    else:
        raise ValueError(f"Unknown extract_type: {extract_type}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract structured content from HTML using CSS selectors'
    )
    parser.add_argument(
        '--content-file',
        help='Path to HTML file'
    )
    parser.add_argument(
        '--content',
        help='HTML content as string (use "-" for stdin)'
    )
    parser.add_argument(
        '--extract-type',
        required=True,
        choices=['list', 'table', 'article', 'structured'],
        help='Type of content to extract'
    )
    parser.add_argument(
        '--selector',
        required=True,
        help='CSS selector for target elements (e.g., ".card-item", "table.products")'
    )
    parser.add_argument(
        '--output',
        help='Output file path (default: stdout as JSON)'
    )
    
    args = parser.parse_args()
    
    # Read HTML content
    if args.content == '-':
        html_content = sys.stdin.read()
    elif args.content:
        html_content = args.content
    elif args.content_file:
        with open(args.content_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        format_error_output(
            "Must provide --content-file or --content",
            COMMAND_ERROR,
            {}
        )
        # format_error_output calls sys.exit() internally
    
    # Extract content
    try:
        result = extract_content(html_content, args.extract_type, args.selector)
        
        # Save output
        if args.output:
            if args.extract_type == 'list':
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(result['items']))
            elif args.extract_type == 'table':
                import csv
                with open(args.output, 'w', encoding='utf-8', newline='') as f:
                    if result['rows']:
                        writer = csv.DictWriter(f, fieldnames=result['rows'][0].keys())
                        writer.writeheader()
                        writer.writerows(result['rows'])
            else:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result.get('content', ''))
        
        # Output A2A JSON
        format_success_output({
            'extract_type': args.extract_type,
            'selector': args.selector,
            'result': result,
            'output_file': args.output
        })
        sys.exit(0)
        
    except Exception as e:
        format_error_output(
            f"Extraction failed: {str(e)}",
            COMMAND_ERROR,
            {'selector': args.selector, 'type': args.extract_type}
        )
        # format_error_output calls sys.exit() internally


if __name__ == "__main__":
    main()
