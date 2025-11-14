#!/usr/bin/env python3
"""
Select Template by Card Size Skill

Given a card size identifier (mtg, pokemon, yugioh, mini, etc.), returns the
appropriate PPTX template path from the template registry.

Protocol-first: Uses template_registry.yaml as source of truth.
"""

import argparse
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND


def load_template_registry() -> Dict[str, Any]:
    """Load template registry from config"""
    registry_path = project_root / ".config" / "template_registry.yaml"

    if not registry_path.exists():
        return {
            "default": {
                "template": "template_2v6h_FIXED.pptx",
                "card_size": "mtg"
            },
            "card_sizes": {}
        }

    with open(registry_path) as f:
        return yaml.safe_load(f)


def resolve_card_size(card_size_query: str, registry: Dict[str, Any]) -> str:
    """
    Resolve card size query to canonical size name.

    Handles aliases like "pokemon" → "mtg" (same size)

    Args:
        card_size_query: User input like "mtg", "pokemon", "yugioh"
        registry: Loaded template registry

    Returns:
        Canonical card size name (e.g., "mtg")
    """
    query_lower = card_size_query.lower().strip()

    # Direct match
    if query_lower in registry["card_sizes"]:
        return query_lower

    # Check aliases
    for size_key, size_def in registry["card_sizes"].items():
        aliases = size_def.get("aliases", [])
        if query_lower in [a.lower() for a in aliases]:
            return size_key

    # Default fallback
    return registry["default"]["card_size"]


def select_template(card_size: str = "mtg", explicit_template: str = None) -> Dict[str, Any]:
    """
    Select appropriate template for given card size.

    Args:
        card_size: Card size identifier (mtg, yugioh, pokemon, mini, etc.)
        explicit_template: Optional explicit template path to use (bypasses selection)

    Returns:
        Dict with template_path, card_size_name, dimensions
    """
    # If explicit template provided, use it
    if explicit_template:
        return {
            "template_path": explicit_template,
            "card_size": card_size,
            "card_size_name": f"Custom ({card_size})",
            "explicit_override": True,
            "note": f"Using explicitly provided template: {explicit_template}"
        }

    registry = load_template_registry()

    # Resolve to canonical size
    canonical_size = resolve_card_size(card_size, registry)

    # Get size definition
    size_def = registry["card_sizes"].get(canonical_size)

    if not size_def:
        # Fallback to default
        default = registry["default"]
        return {
            "template_path": default["template"],
            "card_size": default["card_size"],
            "card_size_name": "Magic: The Gathering (default)",
            "width_inches": 2.5,
            "height_inches": 3.5,
            "fallback_used": True,
            "reason": f"Card size '{card_size}' not found, using default"
        }

    # Check if template exists
    template_path = size_def["template"]
    full_template_path = project_root / template_path

    if not full_template_path.exists():
        # Template file missing - use default
        default = registry["default"]
        return {
            "template_path": default["template"],
            "card_size": canonical_size,
            "card_size_name": size_def["name"],
            "width_inches": size_def["width_inches"],
            "height_inches": size_def["height_inches"],
            "fallback_used": True,
            "reason": f"Template '{template_path}' not found, using default MTG template",
            "note": size_def.get("notes", "")
        }

    # Template found
    return {
        "template_path": template_path,
        "card_size": canonical_size,
        "card_size_name": size_def["name"],
        "width_inches": size_def["width_inches"],
        "height_inches": size_def["height_inches"],
        "width_mm": size_def["width_mm"],
        "height_mm": size_def["height_mm"],
        "aspect_ratio": size_def["aspect_ratio"],
        "fallback_used": False,
        "note": size_def.get("notes", "")
    }


def main():
    """CLI entry point for template selection skill"""
    parser = argparse.ArgumentParser(
        description='Select PPTX template based on card size'
    )
    parser.add_argument(
        '--card-size',
        default='mtg',
        help='Card size identifier (mtg, pokemon, yugioh, mini, tarot, business)'
    )
    parser.add_argument(
        '--explicit-template',
        default=None,
        help='Explicit template path to use (bypasses card size selection)'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output file for result JSON (default: stdout)'
    )

    args = parser.parse_args()

    try:
        # Select template
        result = select_template(args.card_size, args.explicit_template)

        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Template selection saved to: {args.output}", file=sys.stderr)

        # Print results to stderr for user
        print("\n" + "=" * 70, file=sys.stderr)
        print("📐 TEMPLATE SELECTION RESULT", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n🎴 Card Size: {result['card_size_name']}", file=sys.stderr)
        print(f"   Template: {result['template_path']}", file=sys.stderr)

        # Only show dimensions if available (not present for explicit overrides)
        if 'width_inches' in result and 'height_inches' in result:
            print(f"   Dimensions: {result['width_inches']}\" × {result['height_inches']}\"", file=sys.stderr)

        if result.get('fallback_used'):
            print(f"\n⚠️  Fallback: {result['reason']}", file=sys.stderr)

        if result.get('note'):
            print(f"\n📝 Note: {result['note']}", file=sys.stderr)

        print("=" * 70, file=sys.stderr)

        # Output to stdout for skill chaining (A2A protocol)
        format_success_output(result)

    except Exception as e:
        format_error_output(
            f"Template selection failed: {str(e)}",
            exit_code=NOT_FOUND,
            context={"card_size": args.card_size, "exception": str(e)}
        )


if __name__ == '__main__':
    main()
