#!/usr/bin/env python3
"""
Skill wrapper for placing images in PowerPoint presentations.

This script provides a CLI interface for the document_generator module.
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from magic_cards import generate_document
from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND, CONVERSION_ERROR


def main():
    """CLI entry point for place-images-in-pptx skill."""
    parser = argparse.ArgumentParser(
        description='Generate PowerPoint presentation from manifest and template'
    )
    parser.add_argument(
        '--manifest',
        required=True,
        help='Path to manifest JSON file'
    )
    parser.add_argument(
        '--template',
        required=True,
        help='Path to PowerPoint template file (.pptx)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Path for output PowerPoint file'
    )

    args = parser.parse_args()

    # Validate inputs exist
    if not os.path.exists(args.manifest):
        format_error_output(
            f"Manifest file not found: {args.manifest}",
            exit_code=NOT_FOUND,
            context={"manifest": args.manifest}
        )

    if not os.path.exists(args.template):
        format_error_output(
            f"Template file not found: {args.template}",
            exit_code=NOT_FOUND,
            context={"template": args.template}
        )

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Execute document generation
    try:
        output_path = generate_document(
            manifest_path=args.manifest,
            template_path=args.template,
            output_path=args.output
        )

        if output_path and os.path.exists(output_path):
            format_success_output({
                "pptx_path": output_path,
                "manifest": args.manifest,
                "template": args.template
            })
        else:
            format_error_output(
                "Document generation failed",
                exit_code=CONVERSION_ERROR,
                context={"expected_output": args.output}
            )

    except Exception as e:
        format_error_output(
            f"Unexpected error during generation: {str(e)}",
            exit_code=CONVERSION_ERROR,
            context={"exception": str(e)}
        )


if __name__ == '__main__':
    main()
