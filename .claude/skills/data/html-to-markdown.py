#!/usr/bin/env python3
"""
Generic HTML to Markdown converter.

Domain-agnostic: Works for documentation, articles, research, any HTML content.
"""
import argparse
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
from html.parser import HTMLParser

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

try:
    import html2text
except ImportError:
    print("ERROR: html2text not installed. Run: pip install html2text", file=sys.stderr)
    sys.exit(1)

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, COMMAND_ERROR


def convert_html_to_markdown(html_content: str, options: Dict[str, Any]) -> str:
    """
    Convert HTML to Markdown using html2text library.

    Args:
        html_content: Raw HTML string
        options: Conversion options
            - strip_tags: List of tags to remove (default: ['script', 'style'])
            - preserve_links: Keep links (default: True)
            - preserve_images: Keep images (default: True)
            - heading_style: 'atx' (#) or 'setext' (underline)
            - body_width: Line wrap width (0 = no wrap)

    Returns:
        Markdown string
    """
    h = html2text.HTML2Text()

    # Configure html2text based on options
    h.ignore_links = not options.get('preserve_links', True)
    h.ignore_images = not options.get('preserve_images', True)
    h.body_width = options.get('body_width', 0)  # No wrapping by default
    h.ignore_emphasis = options.get('ignore_emphasis', False)

    # Strip unwanted tags
    strip_tags = options.get('strip_tags', ['script', 'style', 'nav', 'footer'])
    for tag in strip_tags:
        pattern = re.compile(f'<{tag}[^>]*>.*?</{tag}>', re.DOTALL | re.IGNORECASE)
        html_content = pattern.sub('', html_content)

    # Convert
    markdown = h.handle(html_content)

    # Clean up extra newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)

    return markdown.strip()


def main():
    parser = argparse.ArgumentParser(
        description='Convert HTML files to Markdown'
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
        '--output',
        help='Output markdown file path (default: stdout)'
    )
    parser.add_argument(
        '--no-links',
        action='store_true',
        help='Strip links from output'
    )
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Strip images from output'
    )
    parser.add_argument(
        '--strip-tags',
        default='script,style,nav,footer',
        help='Comma-separated list of tags to strip (default: script,style,nav,footer)'
    )

    args = parser.parse_args()

    # Read HTML content
    if args.content == '-':
        html_content = sys.stdin.read()
    elif args.content:
        html_content = args.content
    elif args.content_file:
        content_path = Path(args.content_file)
        if not content_path.exists():
            format_error_output(
                f"File not found: {args.content_file}",
                COMMAND_ERROR,
                {'file': args.content_file}
            )
        html_content = content_path.read_text(encoding='utf-8')
    else:
        format_error_output(
            "Must provide --content-file or --content",
            COMMAND_ERROR,
            {}
        )

    # Configure options
    options = {
        'preserve_links': not args.no_links,
        'preserve_images': not args.no_images,
        'strip_tags': args.strip_tags.split(',') if args.strip_tags else [],
        'body_width': 0  # No wrapping
    }

    # Convert
    try:
        markdown = convert_html_to_markdown(html_content, options)

        # Save output
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(markdown, encoding='utf-8')

        # Output A2A JSON
        format_success_output({
            'markdown_length': len(markdown),
            'output_file': args.output,
            'options': options
        })

        # Print markdown to stdout if no output file
        if not args.output:
            print("\n---MARKDOWN---", file=sys.stderr)
            print(markdown)

        sys.exit(0)

    except Exception as e:
        format_error_output(
            f"Conversion failed: {str(e)}",
            COMMAND_ERROR,
            {'options': options}
        )


if __name__ == "__main__":
    main()
