---
name: "document/convert-format"
description: "Convert documents between formats (PPTX→PDF, DOCX→PDF, PPTX→PNG)"
version: "1.0.0"
supports_batch: false

inputs:
  - name: input_file
    type: string
    required: true
    description: "Path to input document file"

  - name: output_format
    type: string
    required: true
    description: "Target format (pdf, png, jpg)"

  - name: output_dir
    type: string
    required: false
    description: "Output directory for multi-file conversions (PNG, JPG)"

  - name: quality
    type: string
    required: false
    default: "medium"
    description: "Output quality level (low, medium, high)"

  - name: overwrite
    type: boolean
    required: false
    default: true
    description: "Overwrite existing output files"

outputs:
  - name: path
    type: string
    description: "Path to converted file (single-file conversions)"

  - name: items
    type: list
    description: "List of output file paths (multi-file conversions like PPTX→PNG)"

  - name: count
    type: integer
    description: "Number of output files generated"

  - name: size_bytes
    type: integer
    description: "Total size of output files in bytes"

  - name: skipped
    type: boolean
    description: "True if conversion was skipped (file exists, overwrite=false)"
---

# document/convert-format

Convert documents between formats using LibreOffice.

## Purpose

This skill provides domain-agnostic document conversion for any file type supported by LibreOffice. It works with presentations (PPTX), documents (DOCX), spreadsheets (XLSX), and can output to PDF, PNG, JPG, and other formats.

## Implementation

### Prerequisites

- Python 3.9+
- LibreOffice installed (`libreoffice` command available)
- pathlib (stdlib)
- subprocess (stdlib)

### Supported Conversions

**Input Formats**:
- PPTX (PowerPoint presentations)
- DOCX (Word documents)
- XLSX (Excel spreadsheets)
- ODP, ODT, ODS (OpenDocument formats)

**Output Formats**:
- PDF (single file)
- PNG (one file per slide/page)
- JPG (one file per slide/page)

### Algorithm

1. **Validate Input**: Check input file exists and format is supported
2. **Determine Output Path**: Calculate output path based on format
3. **Check Existing**: If output exists and overwrite=false, skip conversion
4. **Quality Mapping**: Map quality level to LibreOffice options
   - low: --quality=50
   - medium: --quality=75 (default)
   - high: --quality=90
5. **Execute Conversion**: Run LibreOffice in headless mode
6. **Collect Output**: For multi-file formats (PNG/JPG), collect all generated files
7. **Calculate Metrics**: Count files, measure total size
8. **Return Result**: {path, items, count, size_bytes, skipped}

### Error Handling

- **Missing input file**: Raise FILE_NOT_FOUND error
- **Unsupported format**: Raise UNSUPPORTED_FORMAT error
- **LibreOffice not installed**: Raise TOOL_NOT_FOUND error with installation instructions
- **Conversion failure**: Raise CONVERSION_ERROR with stderr output
- **Output directory missing**: Create parent directories automatically

### Pseudo-code

```python
from pathlib import Path
import subprocess
import os

def execute_document_convert_format(args):
    input_file = Path(args["input_file"])
    output_format = args["output_format"].lower()
    output_dir = Path(args.get("output_dir", input_file.parent))
    quality = args.get("quality", "medium")
    overwrite = args.get("overwrite", True)

    # Validate input
    if not input_file.exists():
        raise Exception(f"FILE_NOT_FOUND: {input_file}")

    # Quality mapping
    quality_map = {"low": 50, "medium": 75, "high": 90}
    quality_value = quality_map.get(quality, 75)

    # Determine output path
    if output_format == "pdf":
        output_path = output_dir / f"{input_file.stem}.pdf"
        is_multi_file = False
    elif output_format in ["png", "jpg"]:
        output_path = output_dir
        is_multi_file = True
    else:
        raise Exception(f"UNSUPPORTED_FORMAT: {output_format}")

    # Check existing (single-file only)
    if not is_multi_file and output_path.exists() and not overwrite:
        return {
            "path": str(output_path),
            "items": [str(output_path)],
            "count": 1,
            "size_bytes": output_path.stat().st_size,
            "skipped": True
        }

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build LibreOffice command
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", output_format,
        "--outdir", str(output_dir),
        str(input_file)
    ]

    # Add quality option for image formats
    if output_format in ["png", "jpg"]:
        cmd.insert(2, f"--quality={quality_value}")

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
        # For PNG/JPG, LibreOffice creates files like: slide1.png, slide2.png, ...
        pattern = f"{input_file.stem}_*.{output_format}"
        output_files = sorted(output_dir.glob(pattern))

        # Fallback: Sometimes LibreOffice names them differently
        if not output_files:
            pattern = f"*.{output_format}"
            output_files = sorted(output_dir.glob(pattern))

        items = [str(f) for f in output_files]
        count = len(items)
        total_size = sum(f.stat().st_size for f in output_files)

        return {
            "path": str(output_files[0]) if output_files else None,
            "items": items,
            "count": count,
            "size_bytes": total_size,
            "skipped": False
        }
    else:
        # Single file (PDF)
        return {
            "path": str(output_path),
            "items": [str(output_path)],
            "count": 1,
            "size_bytes": output_path.stat().st_size,
            "skipped": False
        }
```

## Usage Examples

### Example 1: PPTX to PDF (High Quality)

```yaml
- name: convert_to_pdf
  skill: document/convert-format
  args:
    input_file: "{{steps.generate_slides.outputs.pptx_path}}"
    output_format: "pdf"
    quality: "high"
  outputs:
    pdf_path: "{{result.path}}"
```

### Example 2: DOCX to PDF (Preserve Formatting)

```yaml
- name: convert_report
  skill: document/convert-format
  args:
    input_file: "/tmp/reports/monthly_report.docx"
    output_format: "pdf"
    quality: "medium"
  outputs:
    pdf_path: "{{result.path}}"
```

### Example 3: PPTX to PNG (One PNG Per Slide)

```yaml
- name: export_slides_as_images
  skill: document/convert-format
  args:
    input_file: "{{pptx_file}}"
    output_format: "png"
    output_dir: "/tmp/slide_images"
    quality: "high"
  outputs:
    image_paths: "{{result.items}}"
    image_count: "{{result.count}}"
```

## Domain-Agnostic Design

This skill contains **zero domain-specific logic**. It works equally well for:

- Gaming: Card proxy PDFs, deck list exports
- Business: Presentation archives, report distribution
- Education: Lecture slide PDFs, assignment sheets
- Marketing: Campaign material exports, client deliverables
- Publishing: Print-ready PDFs, image galleries

The skill accepts any document file and converts to any supported format without assumptions about content type or purpose.

## LibreOffice Installation

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install libreoffice
```

**macOS**:
```bash
brew install --cask libreoffice
```

**Fedora**:
```bash
sudo dnf install libreoffice
```

**Verification**:
```bash
libreoffice --version
```
