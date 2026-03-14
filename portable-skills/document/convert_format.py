#!/usr/bin/env python3
"""Convert documents between formats: MD→PPTX, MD→PDF, PPTX→PDF. Uses Marp CLI + LibreOffice."""

import argparse
import os
import shutil
import subprocess
import sys


SUPPORTED_CONVERSIONS = {
    (".md", ".pptx"): "marp",
    (".md", ".pdf"): "marp",
    (".md", ".html"): "marp",
    (".pptx", ".pdf"): "libreoffice",
    (".docx", ".pdf"): "libreoffice",
    (".odt", ".pdf"): "libreoffice",
}


def convert_with_marp(input_path, output_path, output_format):
    """Convert Markdown to presentation using Marp CLI."""
    marp = shutil.which("marp")
    if not marp:
        print("Error: Marp CLI not found. Install with: npm install -g @marp-team/marp-cli", file=sys.stderr)
        sys.exit(1)

    format_flag = {
        ".pptx": "--pptx",
        ".pdf": "--pdf",
        ".html": "--html",
    }.get(output_format)

    if not format_flag:
        print(f"Error: Unsupported Marp output format: {output_format}", file=sys.stderr)
        sys.exit(1)

    cmd = [marp, format_flag, input_path, "-o", output_path, "--allow-local-files"]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Marp error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"Converted: {input_path} → {output_path}")
    return output_path


def convert_with_libreoffice(input_path, output_path, output_format):
    """Convert documents using LibreOffice headless mode."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("Error: LibreOffice not found. Install with: apt install libreoffice", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.dirname(output_path) or "."
    format_name = output_format.lstrip(".")

    cmd = [soffice, "--headless", "--convert-to", format_name, "--outdir", output_dir, input_path]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"LibreOffice error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # LibreOffice names output based on input filename
    expected = os.path.join(output_dir, os.path.splitext(os.path.basename(input_path))[0] + output_format)
    if expected != output_path and os.path.exists(expected):
        os.rename(expected, output_path)

    print(f"Converted: {input_path} → {output_path}")
    return output_path


def convert(input_path, output_path, output_format=None):
    """Convert a document between supported formats.

    Args:
        input_path: Source file path
        output_path: Destination file path
        output_format: Override output format (default: infer from output_path)
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    input_ext = os.path.splitext(input_path)[1].lower()
    if output_format:
        out_ext = f".{output_format.lstrip('.')}"
    else:
        out_ext = os.path.splitext(output_path)[1].lower()

    key = (input_ext, out_ext)
    engine = SUPPORTED_CONVERSIONS.get(key)

    if not engine:
        supported = ", ".join(f"{a}→{b}" for a, b in SUPPORTED_CONVERSIONS)
        print(f"Error: Unsupported conversion {input_ext}→{out_ext}", file=sys.stderr)
        print(f"Supported: {supported}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if engine == "marp":
        return convert_with_marp(input_path, output_path, out_ext)
    elif engine == "libreoffice":
        return convert_with_libreoffice(input_path, output_path, out_ext)


def main():
    parser = argparse.ArgumentParser(description="Convert documents: MD→PPTX/PDF, PPTX→PDF")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--format", "-f", help="Output format override (pptx, pdf, html)")
    args = parser.parse_args()

    convert(args.input, args.output, args.format)


if __name__ == "__main__":
    main()
