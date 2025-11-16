#!/usr/bin/env python3
"""
Document Format Conversion Skill Executor

Generic document conversion using LibreOffice.
Supports PPTX→PDF, DOCX→PDF, PPTX→PNG, and more.
"""

import sys
import json
import argparse
from typing import Dict, Any, List
from pathlib import Path
import subprocess


def convert_format(
    input_file: str,
    output_format: str,
    output_dir: str = None,
    quality: str = "medium",
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Convert document between formats using LibreOffice.

    Args:
        input_file: Path to input document
        output_format: Target format (pdf, png, jpg)
        output_dir: Output directory (defaults to input file directory)
        quality: Quality level (low=50, medium=75, high=90)
        overwrite: Whether to overwrite existing files

    Returns:
        Dictionary with keys:
        - path: Path to converted file (single-file conversions)
        - items: List of output paths (multi-file conversions like PPTX→PNG)
        - count: Number of files generated
        - size_bytes: Total size in bytes
        - skipped: True if conversion was skipped

    Raises:
        Exception: On conversion failure or LibreOffice not found
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise Exception(f"FILE_NOT_FOUND: {input_file}")

    # Determine output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = input_path.parent

    out_dir.mkdir(parents=True, exist_ok=True)

    # Quality mapping
    quality_map = {"low": 50, "medium": 75, "high": 90}
    quality_value = quality_map.get(quality, 75)

    # Determine if multi-file output
    is_multi_file = output_format.lower() in ["png", "jpg", "jpeg"]

    # Check if output exists (single-file only)
    if not is_multi_file:
        output_path = out_dir / f"{input_path.stem}.{output_format.lower()}"
        if output_path.exists() and not overwrite:
            return {
                "path": str(output_path),
                "items": [str(output_path)],
                "count": 1,
                "size_bytes": output_path.stat().st_size,
                "skipped": True
            }

    # Build LibreOffice command
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", output_format.lower(),
        "--outdir", str(out_dir),
        str(input_path)
    ]

    # Execute conversion
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
    except FileNotFoundError:
        raise Exception(
            "TOOL_NOT_FOUND: LibreOffice not installed. "
            "Install with: sudo apt-get install libreoffice (Ubuntu/Debian) "
            "or brew install --cask libreoffice (macOS)"
        )
    except subprocess.CalledProcessError as e:
        raise Exception(f"CONVERSION_ERROR: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise Exception("CONVERSION_TIMEOUT: LibreOffice conversion took > 120s")

    # Collect output files
    if is_multi_file:
        # For PNG/JPG, LibreOffice may create multiple files
        # Pattern varies, so we look for new files with the target extension
        output_files = sorted(out_dir.glob(f"*.{output_format.lower()}"))

        # Filter to only files created/modified recently (last minute)
        # This prevents picking up old files
        import time
        recent_files = [
            f for f in output_files
            if (time.time() - f.stat().st_mtime) < 60
        ]

        if not recent_files:
            # Fallback: look for files matching input name pattern
            pattern = f"{input_path.stem}*.{output_format.lower()}"
            recent_files = sorted(out_dir.glob(pattern))

        items = [str(f) for f in recent_files]
        total_size = sum(f.stat().st_size for f in recent_files)

        return {
            "path": str(recent_files[0]) if recent_files else None,
            "items": items,
            "count": len(items),
            "size_bytes": total_size,
            "skipped": False
        }
    else:
        # Single file output (PDF)
        output_path = out_dir / f"{input_path.stem}.{output_format.lower()}"

        if not output_path.exists():
            raise Exception(f"CONVERSION_FAILED: Expected output not found: {output_path}")

        return {
            "path": str(output_path),
            "items": [str(output_path)],
            "count": 1,
            "size_bytes": output_path.stat().st_size,
            "skipped": False
        }


def main():
    """CLI entry point for skill executor."""
    parser = argparse.ArgumentParser(description="Convert documents between formats")
    parser.add_argument("--input-file", required=True,
                       help="Input document path")
    parser.add_argument("--output-format", required=True,
                       choices=["pdf", "png", "jpg", "jpeg"],
                       help="Target format")
    parser.add_argument("--output-dir",
                       help="Output directory (defaults to input file directory)")
    parser.add_argument("--quality", default="medium",
                       choices=["low", "medium", "high"],
                       help="Quality level")
    parser.add_argument("--overwrite", type=lambda x: x.lower() == "true", default=True,
                       help="Overwrite existing files (true/false)")

    args = parser.parse_args()

    try:
        result = convert_format(
            input_file=args.input_file,
            output_format=args.output_format,
            output_dir=args.output_dir,
            quality=args.quality,
            overwrite=args.overwrite
        )

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "path": None,
            "items": []
        }
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
