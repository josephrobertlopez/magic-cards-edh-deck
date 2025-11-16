#!/usr/bin/env python3
"""
HTML CSS Selector Extraction Skill Executor

Generic HTML data extraction using CSS selectors.
Works with any HTML structure - decklists, product catalogs, tables, menus, articles.
"""

import sys
import json
import argparse
from typing import Dict, Any, List
from pathlib import Path
from bs4 import BeautifulSoup


def extract_css(
    html_content: str,
    selector: str,
    extract_type: str = "text",
    attribute: str = None
) -> Dict[str, Any]:
    """
    Extract data from HTML using CSS selectors.

    Args:
        html_content: HTML string or file path
        selector: CSS selector (e.g., '.card-name', '#content', 'a[href]')
        extract_type: What to extract - 'text', 'html', or 'attribute'
        attribute: Attribute name if extract_type='attribute' (e.g., 'href', 'src')

    Returns:
        Dictionary with keys:
        - items: List of extracted values
        - count: Number of items extracted

    Raises:
        Exception: On parsing failure or invalid selector
    """
    # Check if html_content is a file path
    if Path(html_content).exists():
        with open(html_content, 'r', encoding='utf-8') as f:
            html_str = f.read()
    else:
        html_str = html_content

    try:
        soup = BeautifulSoup(html_str, 'lxml')
    except Exception:
        # Fallback to html.parser if lxml fails
        try:
            soup = BeautifulSoup(html_str, 'html.parser')
        except Exception as e:
            raise Exception(f"HTML_PARSE_ERROR: {str(e)}")

    try:
        elements = soup.select(selector)
    except Exception as e:
        raise Exception(f"INVALID_SELECTOR: {str(e)}")

    items = []

    for elem in elements:
        if extract_type == "text":
            value = elem.get_text(strip=True)
        elif extract_type == "html":
            value = str(elem)
        elif extract_type == "attribute":
            if not attribute:
                raise Exception("MISSING_ATTRIBUTE: attribute parameter required for extract_type='attribute'")
            value = elem.get(attribute)
            if value is None:
                continue  # Skip elements without the attribute
        else:
            raise Exception(f"INVALID_EXTRACT_TYPE: {extract_type} (must be 'text', 'html', or 'attribute')")

        if value:  # Skip empty values
            items.append(value)

    return {
        "items": items,
        "count": len(items)
    }


def main():
    """CLI entry point for skill executor."""
    parser = argparse.ArgumentParser(description="Extract data from HTML using CSS selectors")
    parser.add_argument("--html-content", required=True,
                       help="HTML string or file path")
    parser.add_argument("--selector", required=True,
                       help="CSS selector (e.g., '.card-name', 'a[href]')")
    parser.add_argument("--extract-type", default="text",
                       choices=["text", "html", "attribute"],
                       help="What to extract from matched elements")
    parser.add_argument("--attribute",
                       help="Attribute name (required if extract-type=attribute)")

    args = parser.parse_args()

    try:
        result = extract_css(
            html_content=args.html_content,
            selector=args.selector,
            extract_type=args.extract_type,
            attribute=args.attribute
        )

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "items": [],
            "count": 0
        }
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
