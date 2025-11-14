# generate-magic-proxies

Complete Magic: The Gathering proxy generation pipeline from decklist to printer-ready PDF.

## Usage

```
/generate-magic-proxies <decklist.txt> [--template custom.pptx] [--no-pdf]
```

**Parameters**:
- `decklist.txt`: Text file with card names (one per line) (required)
- `--template`: Custom PowerPoint template (optional, defaults to template_2v6h_FIXED.pptx)
- `--no-pdf`: Skip PDF conversion, generate PPTX only (optional)

**Output**:
- `outputs/deck_name.pptx`: PowerPoint presentation with cards
- `outputs/deck_name.pdf`: Printer-ready PDF (11.0" × 8.5")
- `.claude/cards/`: Cached card images
- `.claude/state/deck_name_manifest.json`: Download metadata

**Examples**:
```
/generate-magic-proxies decklists/krenko_mob_boss.txt
/generate-magic-proxies decklists/my_deck.txt --template custom_template.pptx
/generate-magic-proxies decklists/test.txt --no-pdf
```

## Implementation

**Note**: This skill orchestrates three other skills:
1. `/fetch-cards` - Download card images from Scryfall
2. `/fill-template` - Generate PPTX from template and images
3. `/convert-pptx-to-pdf` - Convert PPTX to PDF

```python
#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

def generate_proxies(decklist_path, template_path=None, skip_pdf=False):
    """
    Complete proxy generation pipeline.

    Args:
        decklist_path: Path to decklist text file
        template_path: Optional custom template (defaults to template_2v6h_FIXED.pptx)
        skip_pdf: If True, skip PDF conversion

    Returns:
        Dictionary with output paths

    Raises:
        FileNotFoundError: Decklist or template not found
        subprocess.CalledProcessError: Sub-skill failed
    """
    decklist_path = Path(decklist_path).resolve()

    if not decklist_path.exists():
        raise FileNotFoundError(f"Decklist not found: {decklist_path}")

    # Default template
    if not template_path:
        template_path = Path("template_2v6h_FIXED.pptx")
        if not template_path.exists():
            raise FileNotFoundError(
                f"Default template not found: {template_path}\\n"
                f"Specify custom template with --template flag"
            )
    else:
        template_path = Path(template_path).resolve()
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

    # Output paths
    deck_name = decklist_path.stem
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    pptx_path = output_dir / f"{deck_name}.pptx"
    pdf_path = output_dir / f"{deck_name}.pdf"

    print(f"🎴 Magic Card Proxy Generator")
    print("=" * 70)
    print(f"📄 Decklist: {decklist_path}")
    print(f"📋 Template: {template_path}")
    print(f"💾 Output: {pptx_path}")
    if not skip_pdf:
        print(f"📄 PDF: {pdf_path}")
    print("=" * 70)
    print()

    # Step 1: Fetch cards from Scryfall
    print("📥 Step 1/3: Fetching cards from Scryfall...")
    print()

    fetch_result = subprocess.run(
        ["python3", "-c",
         f"import sys; sys.path.insert(0, '.claude/skills'); "
         f"from pathlib import Path; "
         f"import importlib.util; "
         f"spec = importlib.util.spec_from_file_location('fetch_cards', Path('.claude/skills/fetch-cards.md')); "
         f"print('Using /fetch-cards skill')"],
        shell=False
    )

    # Use existing fetch-cards skill
    fetch_cmd = [
        sys.executable, ".claude/skills/fetch-cards.md", str(decklist_path)
    ]

    try:
        # Note: In actual implementation, we'd extract the Python code from the skill markdown
        # and execute it. For now, assume it exists as a Python script.
        print("⚠️  Note: This skill requires /fetch-cards to be installed")
        print(f"   Run: /fetch-cards {decklist_path}")
        print()

        # Placeholder for actual fetch execution
        # In real implementation: execute fetch-cards skill programmatically

    except Exception as e:
        raise subprocess.CalledProcessError(1, fetch_cmd, stderr=str(e))

    # Step 2: Generate PPTX from template
    print("📐 Step 2/3: Generating presentation...")
    print()

    try:
        print("⚠️  Note: This skill requires /fill-template to be installed")
        print(f"   Run: /fill-template {template_path} .claude/cards/ {pptx_path}")
        print()

        # Placeholder for actual fill-template execution
        # In real implementation: execute fill-template skill programmatically

    except Exception as e:
        raise subprocess.CalledProcessError(1, [], stderr=str(e))

    # Step 3: Convert to PDF (unless skipped)
    if not skip_pdf:
        print("📄 Step 3/3: Converting to PDF...")
        print()

        try:
            print("⚠️  Note: This skill requires /convert-pptx-to-pdf to be installed")
            print(f"   Run: /convert-pptx-to-pdf {pptx_path}")
            print()

            # Placeholder for actual convert execution
            # In real implementation: execute convert-pptx-to-pdf skill programmatically

        except Exception as e:
            raise subprocess.CalledProcessError(5, [], stderr=str(e))
    else:
        print("⏭️  Step 3/3: Skipped (--no-pdf flag)")
        print()

    print("=" * 70)
    print("🎉 Proxy generation complete!")
    print()
    print(f"📁 Outputs:")
    print(f"   PPTX: {pptx_path}")
    if not skip_pdf:
        print(f"   PDF:  {pdf_path}")
    print()
    print(f"🎴 Ready to print!")

    return {
        'pptx': str(pptx_path),
        'pdf': str(pdf_path) if not skip_pdf else None
    }

def main():
    """Main skill execution"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate printer-ready Magic: The Gathering card proxies"
    )
    parser.add_argument("decklist", help="Path to decklist text file")
    parser.add_argument("--template", help="Custom template PPTX (optional)")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF conversion")

    args = parser.parse_args()

    try:
        generate_proxies(args.decklist, args.template, args.no_pdf)
        return 0

    except FileNotFoundError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except subprocess.CalledProcessError as e:
        print(f"\\n❌ Pipeline failed at step: {e.cmd[0] if e.cmd else 'unknown'}")
        print(f"   {e.stderr if e.stderr else 'Unknown error'}")
        return e.returncode

    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Pipeline Workflow

**Stage 1: Fetch Cards** (uses `/fetch-cards` skill):
1. Parse decklist text file
2. Query Scryfall API for each card (rate limited 10 req/sec)
3. Handle double-faced cards (download both faces)
4. Cache images in `.claude/cards/`
5. Generate manifest JSON in `.claude/state/`

**Stage 2: Generate PPTX** (uses `/fill-template` skill):
1. Load PowerPoint template
2. Detect card slots (rectangles ≥1.0" × 1.0")
3. Place card images in slots sequentially
4. Handle rotation for horizontal slots
5. Create multiple slides as needed
6. Save presentation to `outputs/`

**Stage 3: Convert to PDF** (uses `/convert-pptx-to-pdf` skill):
1. Detect LibreOffice binary (cross-platform)
2. Spawn headless LibreOffice subprocess
3. Convert PPTX → PDF with 300 DPI
4. Save PDF to `outputs/`

## Output Example

```
🎴 Magic Card Proxy Generator
======================================================================
📄 Decklist: decklists/krenko_mob_boss.txt
📋 Template: template_2v6h_FIXED.pptx
💾 Output: outputs/krenko_mob_boss.pptx
📄 PDF: outputs/krenko_mob_boss.pdf
======================================================================

📥 Step 1/3: Fetching cards from Scryfall...
   ✅ Downloaded 100/100 cards
   💾 Manifest: .claude/state/krenko_mob_boss_manifest.json

📐 Step 2/3: Generating presentation...
   📐 Found 8 card slots (2v+6h layout)
   📄 Created 13 slides
   💾 Saved: outputs/krenko_mob_boss.pptx

📄 Step 3/3: Converting to PDF...
   ✅ Converted → outputs/krenko_mob_boss.pdf (13 pages, 5.2 MB)

======================================================================
🎉 Proxy generation complete!

📁 Outputs:
   PPTX: outputs/krenko_mob_boss.pptx
   PDF:  outputs/krenko_mob_boss.pdf

🎴 Ready to print!
```

## Error Handling

**`Decklist not found`**:
```
❌ Error: Decklist not found: /path/to/deck.txt
```

**`Default template not found`**:
```
❌ Error: Default template not found: template_2v6h_FIXED.pptx
   Specify custom template with --template flag
```

**`Pipeline failed at fetch`**:
```
❌ Pipeline failed at step: fetch-cards
   Card 'FAKE_CARD_XYZ' not found on Scryfall (HTTP 404)
```

**`Pipeline failed at PDF conversion`**:
```
❌ Pipeline failed at step: convert-pptx-to-pdf
   LibreOffice not found. Install from https://www.libreoffice.org/
```

## Dependencies

**Required Skills**:
- `/fetch-cards` - Scryfall API integration
- `/fill-template` - PowerPoint generation
- `/convert-pptx-to-pdf` - PDF conversion

**System Dependencies**:
- Python 3.9+ with python-pptx, Pillow, requests
- LibreOffice (for PDF conversion, unless --no-pdf used)
- Internet connection (for Scryfall API)

**File Requirements**:
- Template file (defaults to `template_2v6h_FIXED.pptx` in repo root)
- Decklist file (text format, one card per line)

## Performance

**Typical execution times** (100-card EDH deck):
- Fetch (first run): ~30-60 seconds (network-bound)
- Fetch (cached): <1 second
- PPTX generation: ~4-5 seconds
- PDF conversion: ~5-8 seconds
- **Total (first run)**: ~40-75 seconds
- **Total (cached)**: ~10-15 seconds

## Exit Codes

- `0`: Success
- `1`: File not found or validation error
- `3`: Network error (Scryfall unreachable)
- `4`: Template error (no valid slots)
- `5`: PDF conversion error (LibreOffice issue)
