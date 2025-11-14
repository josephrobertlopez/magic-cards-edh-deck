#!/usr/bin/env python3
"""
Skill wrapper for fetching resources from APIs.

This script provides a CLI interface for the data_fetcher module.
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from magic_cards import fetch_resources_from_list
from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND, NETWORK_ERROR


def main():
    """CLI entry point for fetch-from-api skill."""
    parser = argparse.ArgumentParser(
        description='Fetch resources from API based on decklist'
    )
    parser.add_argument(
        '--list-strategies',
        action='store_true',
        help='List available strategy configs and exit'
    )

    # Check for --list-strategies early (before required args)
    if '--list-strategies' in sys.argv:
        from magic_cards.config_loader import load_strategy_configs
        strategies = load_strategy_configs()
        print("\n📋 Available Strategy Configs:")
        print("=" * 70)
        for domain, config in strategies.items():
            version = config.get('version', 'N/A')
            patterns = list(config.get('detection_patterns', {}).keys())
            print(f"  • {domain} (v{version})")
            print(f"    Detection patterns: {', '.join(patterns)}")
        print("=" * 70)
        print(f"\nTotal: {len(strategies)} strategy config(s) loaded\n")
        sys.exit(0)

    parser.add_argument(
        '--decklist',
        required=True,
        help='Path to decklist file'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory to save downloaded resources'
    )
    parser.add_argument(
        '--manifest',
        default=None,
        help='Path to output manifest JSON (default: .claude/state/<decklist>_manifest.json)'
    )
    parser.add_argument(
        '--api-url',
        required=True,
        help='API URL template with {identifier} placeholder (e.g., "https://api.scryfall.com/cards/named?fuzzy={identifier}")'
    )
    parser.add_argument(
        '--schema',
        required=True,
        help='JSON string with response schema (e.g., \'{"image_url": "sprites.front_default", "name": "name"}\')'
    )
    parser.add_argument(
        '--size-hints',
        required=True,
        help='JSON string with target dimensions (e.g., \'{"width_px": 750, "height_px": 1050, "dpi": 300, "source": "provider"}\')'
    )
    args = parser.parse_args()

    # Validate decklist exists
    if not os.path.exists(args.decklist):
        format_error_output(
            f"Decklist file not found: {args.decklist}",
            exit_code=NOT_FOUND,
            context={"decklist": args.decklist}
        )

    # Generate manifest path if not provided
    manifest_path = args.manifest
    if not manifest_path:
        decklist_name = Path(args.decklist).stem
        manifest_path = f".claude/state/{decklist_name}_manifest.json"

    # Ensure output directories exist
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

    # Parse schema if provided
    response_schema = None
    if args.schema:
        import json
        try:
            response_schema = json.loads(args.schema)
        except json.JSONDecodeError as e:
            format_error_output(
                f"Invalid schema JSON: {str(e)}",
                exit_code=NOT_FOUND,
                context={"schema": args.schema}
            )

    # Parse and validate size_hints (required parameter)
    import json
    try:
        size_hints = json.loads(args.size_hints)
        # Validate required fields
        required_fields = ["width_px", "height_px", "dpi", "source"]
        missing_fields = [f for f in required_fields if f not in size_hints]
        if missing_fields:
            format_error_output(
                f"size_hints missing required fields: {missing_fields}",
                exit_code=NOT_FOUND,
                context={"missing_fields": missing_fields}
            )

        # Validate field types
        if not isinstance(size_hints["width_px"], int) or size_hints["width_px"] <= 0:
            format_error_output(
                "size_hints.width_px must be positive integer",
                exit_code=NOT_FOUND,
                context={"width_px": size_hints.get("width_px")}
            )
        if not isinstance(size_hints["height_px"], int) or size_hints["height_px"] <= 0:
            format_error_output(
                "size_hints.height_px must be positive integer",
                exit_code=NOT_FOUND,
                context={"height_px": size_hints.get("height_px")}
            )
        if not isinstance(size_hints["dpi"], int) or size_hints["dpi"] <= 0:
            format_error_output(
                "size_hints.dpi must be positive integer",
                exit_code=NOT_FOUND,
                context={"dpi": size_hints.get("dpi")}
            )
        if size_hints["source"] not in ["provider", "template", "hybrid"]:
            format_error_output(
                "size_hints.source must be 'provider', 'template', or 'hybrid'",
                exit_code=NOT_FOUND,
                context={"source": size_hints.get("source")}
            )
    except json.JSONDecodeError as e:
        format_error_output(
            f"Invalid size_hints JSON: {str(e)}",
            exit_code=NOT_FOUND,
            context={"size_hints": args.size_hints}
        )

    # Execute fetch operation
    try:
        exit_code = fetch_resources_from_list(
            resource_list_file=args.decklist,
            output_dir=args.output_dir,
            manifest_path=manifest_path,
            api_url_template=args.api_url,
            response_schema=response_schema,
            size_hints=size_hints  # Required: dimension-optimized fetching
        )

        if exit_code == SUCCESS:
            format_success_output({
                "manifest_path": manifest_path,
                "output_dir": args.output_dir,
                "decklist": args.decklist
            })
        else:
            format_error_output(
                "Resource fetching failed",
                exit_code=NETWORK_ERROR,
                context={"manifest_path": manifest_path}
            )

    except Exception as e:
        format_error_output(
            f"Unexpected error during fetch: {str(e)}",
            exit_code=NETWORK_ERROR,
            context={"exception": str(e)}
        )


if __name__ == '__main__':
    main()
