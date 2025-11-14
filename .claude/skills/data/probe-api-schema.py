#!/usr/bin/env python3
"""
Schema Probe Skill: Auto-discover API response schemas

This skill probes an API endpoint to infer the response schema,
making it easier to integrate new APIs without manual schema writing.

Usage:
    ./probe-api-schema.py --api-url "https://pokeapi.co/api/v2/pokemon/pikachu" \
                          --sample-id "pikachu"

Output: Inferred schema JSON
"""

import argparse
import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND, NETWORK_ERROR


def find_image_urls(data: Any, path="") -> List[tuple]:
    """
    Recursively find all URL fields that might be images.

    Returns list of (json_path, url_value) tuples
    """
    results = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # Check if this looks like an image URL
            if isinstance(value, str) and (
                ".png" in value.lower() or
                ".jpg" in value.lower() or
                ".jpeg" in value.lower() or
                ".gif" in value.lower() or
                "/sprites/" in value or
                "/images/" in value or
                "image" in key.lower() or
                "sprite" in key.lower() or
                "picture" in key.lower() or
                "photo" in key.lower()
            ):
                results.append((current_path, value))

            # Recurse into nested dicts/lists
            elif isinstance(value, (dict, list)):
                results.extend(find_image_urls(value, current_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]" if i == 0 else f"{path}[]"  # Use [] for array notation
            if isinstance(item, (dict, list)):
                results.extend(find_image_urls(item, current_path))

    return results


def find_name_fields(data: Any, path="") -> List[tuple]:
    """Find fields that might be the item name/title."""
    results = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, str) and key.lower() in ["name", "title", "label", "id", "identifier"]:
                results.append((current_path, value))

            elif isinstance(value, dict):
                results.extend(find_name_fields(value, current_path))

    return results


def probe_api_endpoint(api_url: str, sample_id: str) -> Dict[str, Any]:
    """
    Probe API endpoint and infer response schema.

    Args:
        api_url: URL template with {identifier} placeholder
        sample_id: Sample identifier to test with

    Returns:
        Inferred schema dict
    """
    # Construct test URL
    test_url = api_url.replace("{identifier}", sample_id)

    print(f"🔍 Probing API: {test_url}", file=sys.stderr)

    # Fetch sample response
    try:
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch from API: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"API response is not valid JSON: {e}")

    print(f"✅ Got response ({len(json.dumps(data))} bytes)", file=sys.stderr)

    # Analyze response structure
    image_fields = find_image_urls(data)
    name_fields = find_name_fields(data)

    print(f"\n📸 Found {len(image_fields)} potential image fields:", file=sys.stderr)
    for path, url in image_fields[:5]:  # Show first 5
        print(f"  - {path}: {url[:60]}...", file=sys.stderr)

    print(f"\n📛 Found {len(name_fields)} potential name fields:", file=sys.stderr)
    for path, value in name_fields[:3]:  # Show first 3
        print(f"  - {path}: {value}", file=sys.stderr)

    # Build inferred schema
    schema = {}

    # Primary image URL
    if image_fields:
        # Prefer single image over array
        single_images = [p for p, _ in image_fields if "[]" not in p]
        array_images = [p for p, _ in image_fields if "[]" in p]

        if single_images:
            schema["image_url"] = single_images[0]
        if array_images:
            schema["image_url_multi"] = array_images[0]

        # Add fallback if multiple found
        if len(single_images) > 1:
            schema["image_url_fallback"] = single_images[1]

    # Name field
    if name_fields:
        schema["name_field"] = name_fields[0][0]

    # Infer min image size based on API type
    if any("sprite" in p.lower() for p, _ in image_fields):
        schema["min_image_size"] = 100  # Sprites are usually small
    else:
        schema["min_image_size"] = 500  # Regular images

    return schema


def main():
    """CLI entry point for probe-api-schema skill."""
    parser = argparse.ArgumentParser(
        description='Probe API endpoint to infer response schema'
    )
    parser.add_argument(
        '--api-url',
        required=True,
        help='API URL template with {identifier} placeholder'
    )
    parser.add_argument(
        '--sample-id',
        required=True,
        help='Sample identifier to test probe with (e.g., "pikachu", "Forest")'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output file for schema JSON (default: stdout)'
    )

    args = parser.parse_args()

    try:
        schema = probe_api_endpoint(args.api_url, args.sample_id)

        # Output schema
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(schema, f, indent=2)
            print(f"\n💾 Schema saved to: {args.output}", file=sys.stderr)

        # Also output to stdout for skill chaining
        format_success_output({
            "schema": schema,
            "api_url": args.api_url,
            "sample_id": args.sample_id
        })

    except ValueError as e:
        format_error_output(
            str(e),
            exit_code=NETWORK_ERROR,
            context={"api_url": args.api_url, "sample_id": args.sample_id}
        )
    except Exception as e:
        format_error_output(
            f"Unexpected error during probe: {str(e)}",
            exit_code=NETWORK_ERROR,
            context={"exception": str(e)}
        )


if __name__ == '__main__':
    main()
