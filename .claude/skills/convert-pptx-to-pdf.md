# convert-pptx-to-pdf

Convert PowerPoint presentations to PDF using LibreOffice headless mode.

## Usage

```
/convert-pptx-to-pdf <input.pptx> [output_dir]
```

**Parameters**:
- `input.pptx`: PowerPoint file to convert (required)
- `output_dir`: Output directory for PDF (optional, defaults to same directory as input)

**Output**:
- Creates PDF with same basename as input (e.g., `deck.pptx` → `deck.pdf`)
- Preserves slide dimensions and formatting
- 300 DPI resolution suitable for printing

**Examples**:
```
/convert-pptx-to-pdf presentation.pptx
/convert-pptx-to-pdf slides.pptx outputs/
```

## Implementation

```python
#!/usr/bin/env python3
import subprocess
import os
import sys
import shutil
from pathlib import Path

def find_libreoffice():
    """
    Cross-platform LibreOffice binary detection.
    Returns path to binary or None if not found.
    """
    # Common binary names/paths
    candidates = [
        "libreoffice",  # Linux default
        "soffice",      # Alternative Linux name
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",   # Windows
        "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe"  # Windows 32-bit
    ]

    for binary in candidates:
        # Check if in PATH
        if shutil.which(binary):
            return binary
        # Check if absolute path exists
        if os.path.exists(binary):
            return binary

    return None

def convert_pptx_to_pdf(pptx_path, output_dir=None):
    """
    Convert PPTX to PDF using LibreOffice headless.

    Args:
        pptx_path: Path to input PPTX file
        output_dir: Output directory (default: same as input)

    Returns:
        Path to generated PDF file

    Raises:
        FileNotFoundError: PPTX or LibreOffice not found
        subprocess.CalledProcessError: Conversion failed
        TimeoutError: Conversion took >60 seconds
    """
    # Validate input file
    pptx_path = Path(pptx_path).resolve()
    if not pptx_path.exists():
        raise FileNotFoundError(f"Input file not found: {pptx_path}")

    if not pptx_path.suffix.lower() in ['.pptx', '.ppt']:
        raise ValueError(f"Input must be PowerPoint file (.pptx or .ppt), got: {pptx_path.suffix}")

    # Find LibreOffice
    libreoffice_binary = find_libreoffice()
    if not libreoffice_binary:
        raise FileNotFoundError(
            "LibreOffice not found. Install from https://www.libreoffice.org/\\n"
            "Or use --no-pdf flag to skip PDF generation"
        )

    # Determine output directory
    if output_dir:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = pptx_path.parent

    # Expected output path
    pdf_path = output_dir / f"{pptx_path.stem}.pdf"

    print(f"📄 Converting to PDF...")
    print(f"   Input:  {pptx_path}")
    print(f"   Output: {pdf_path}")

    # Build LibreOffice command
    cmd = [
        libreoffice_binary,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(output_dir),
        str(pptx_path)
    ]

    try:
        # Run conversion with 60 second timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False  # Don't raise on non-zero exit, we'll handle it
        )

        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=f"LibreOffice conversion failed: {error_msg}"
            )

        # Verify PDF was created
        if not pdf_path.exists():
            raise FileNotFoundError(
                f"PDF was not created at expected path: {pdf_path}\\n"
                f"LibreOffice may have saved to different location"
            )

        # Get file size
        size_mb = pdf_path.stat().st_size / (1024 * 1024)

        print(f"✅ Saved: {pdf_path}")
        print(f"📊 Size: {size_mb:.2f} MB")

        return str(pdf_path)

    except subprocess.TimeoutExpired:
        raise TimeoutError(
            f"Conversion timeout (>60 seconds). File may be too large or LibreOffice hung."
        )

def main(pptx_path, output_dir=None):
    """Main skill execution"""
    try:
        pdf_path = convert_pptx_to_pdf(pptx_path, output_dir)
        print(f"\\n🎉 Conversion complete!")
        return 0

    except FileNotFoundError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except ValueError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except subprocess.CalledProcessError as e:
        print(f"\\n❌ Conversion failed:")
        print(f"   {e.stderr if e.stderr else 'Unknown error'}")
        return 5

    except TimeoutError as e:
        print(f"\\n❌ {e}")
        return 5

    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: convert-pptx-to-pdf <input.pptx> [output_dir]")
        sys.exit(1)

    pptx_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    sys.exit(main(pptx_path, output_dir))
```

## Error Handling

**Common Errors**:

**`LibreOffice not found`**:
```
❌ Error: LibreOffice not found. Install from https://www.libreoffice.org/
   Or use --no-pdf flag to skip PDF generation
```
**Solution**: Install LibreOffice and ensure `soffice` or `libreoffice` is in PATH

**`Input file not found`**:
```
❌ Error: Input file not found: /path/to/file.pptx
```
**Solution**: Check file path is correct and file exists

**`Conversion timeout (>60 seconds)`**:
```
❌ Conversion timeout (>60 seconds). File may be too large or LibreOffice hung.
```
**Solution**: Try with smaller presentation, or kill hung LibreOffice processes

**`LibreOffice conversion failed`**:
```
❌ Conversion failed: Error: source file could not be loaded
```
**Solution**: PPTX file may be corrupted or have unsupported features

## Platform Support

**Linux**:
- Binary: `libreoffice` or `soffice`
- Install: `sudo apt install libreoffice` (Debian/Ubuntu)
- Install: `sudo dnf install libreoffice` (Fedora/RHEL)

**macOS**:
- Binary: `/Applications/LibreOffice.app/Contents/MacOS/soffice`
- Install: `brew install --cask libreoffice`

**Windows**:
- Binary: `C:\\Program Files\\LibreOffice\\program\\soffice.exe`
- Install: Download from [libreoffice.org](https://www.libreoffice.org/download/)

## Performance

**Typical conversion times**:
- Small presentation (10 slides): ~3-5 seconds
- Medium presentation (50 slides): ~8-12 seconds
- Large presentation (200+ slides): ~30-60 seconds

**Bottleneck**: LibreOffice startup time (~2-3 seconds) dominates for small files

## Exit Codes

- `0`: Success
- `1`: File not found or invalid input
- `5`: Conversion failed or timeout
