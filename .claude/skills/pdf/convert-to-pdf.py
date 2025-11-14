#!/usr/bin/env python3
"""
Skill wrapper for converting files to PDF.

This script provides a CLI interface for the format_transformer module.
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from magic_cards import transform_to_pdf
from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND, CONVERSION_ERROR


def main():
    """CLI entry point for convert-to-pdf skill."""
    parser = argparse.ArgumentParser(
        description='Convert file to PDF format'
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Path to source file (e.g., .pptx, .docx)'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory for output PDF file'
    )

    args = parser.parse_args()

    # Validate source exists
    if not os.path.exists(args.source):
        format_error_output(
            f"Source file not found: {args.source}",
            exit_code=NOT_FOUND,
            context={"source": args.source}
        )

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Execute PDF conversion
    try:
        pdf_path = transform_to_pdf(
            source_path=args.source,
            output_dir=args.output_dir
        )

        if pdf_path and os.path.exists(pdf_path):
            format_success_output({
                "pdf_path": pdf_path,
                "source": args.source,
                "output_dir": args.output_dir
            })
        else:
            format_error_output(
                "PDF conversion failed - LibreOffice may not be installed",
                exit_code=CONVERSION_ERROR,
                context={"source": args.source}
            )

    except FileNotFoundError as e:
        format_error_output(
            "LibreOffice not found - required for PDF conversion",
            exit_code=CONVERSION_ERROR,
            context={"exception": str(e)}
        )
    except Exception as e:
        format_error_output(
            f"Unexpected error during conversion: {str(e)}",
            exit_code=CONVERSION_ERROR,
            context={"exception": str(e)}
        )


if __name__ == '__main__':
    main()
