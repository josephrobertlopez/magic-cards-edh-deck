# convert-to-pdf

Generic file-to-PDF conversion using LibreOffice headless mode.

## A2A Interface

**REQUEST Message**:
```json
{
  "source_path": "document.pptx",  // or .docx, .xlsx, .odt, etc.
  "output_dir": "outputs",
  "timeout": 60
}
```

**RESPONSE Message**:
```json
{
  "pdf_path": "outputs/document.pdf",
  "size_mb": 5.20
}
```

## Domain-Agnostic Uses

- **PPTX → PDF**: Convert presentations
- **DOCX → PDF**: Convert Word documents
- **XLSX → PDF**: Convert spreadsheets
- **ODT → PDF**: Convert OpenDocument files
- **HTML → PDF**: Convert web pages

## Supported Formats

LibreOffice can convert:
- Office: `.pptx`, `.ppt`, `.docx`, `.doc`, `.xlsx`, `.xls`
- OpenDocument: `.odp`, `.odt`, `.ods`
- Web: `.html`

## Parameters

- `source_path` (required): Source file path
- `output_dir` (optional): Output directory (default: same as source)
- `timeout` (optional): Conversion timeout in seconds (default: 60)

## CLI Usage

**Standalone Invocation** (User Story 1):
```bash
python3 .claude/skills/pdf/convert-to-pdf.py \
  --source outputs/my_deck.pptx \
  --output-dir outputs
```

**Parameters**:
- `--source` (required): Path to source file (e.g., .pptx, .docx, .xlsx)
- `--output-dir` (required): Directory for output PDF file

**Success Output** (JSON to stdout):
```json
{
  "status": "success",
  "pdf_path": "/home/joey/Documents/GitHub/magic-cards-edh-deck/outputs/my_deck.pdf",
  "source": "outputs/my_deck.pptx",
  "output_dir": "outputs"
}
```

**Error Output** (JSON to stderr):
```json
{
  "status": "error",
  "error": "LibreOffice not found - required for PDF conversion",
  "exit_code": 5,
  "context": {"exception": "..."}
}
```

**Exit Codes**:
- `0`: Success
- `1`: Source file not found
- `5`: LibreOffice not installed or conversion error

## Runtime Dependencies

- LibreOffice installed:
  - Linux: `libreoffice` or `soffice` in PATH
  - macOS: `/Applications/LibreOffice.app/Contents/MacOS/soffice`
  - Windows: `C:\Program Files\LibreOffice\program\soffice.exe`

## Implementation

```python
#!/usr/bin/env python3
import sys
import os

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from magic_cards import transform_to_pdf

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: source_path required", file=sys.stderr)
        sys.exit(1)
    
    source_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        pdf_path = transform_to_pdf(source_path=source_path, output_dir=output_dir)
        print(pdf_path)
        sys.exit(0)
    except FileNotFoundError as e:
        if "LibreOffice" in str(e):
            sys.exit(5)  # LibreOffice not found
        else:
            sys.exit(1)  # Source file not found
```

## Error Codes

- `0`: Success
- `1`: Source file not found
- `5`: LibreOffice not installed
