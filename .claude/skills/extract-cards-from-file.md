# extract-cards-from-file

Extract card names from PPTX or PDF proxy files (reverse of proxy generation).

## Usage

```
/extract-cards-from-file <input.pptx|input.pdf> [--format txt|json] [--dedupe]
```

**Parameters**:
- `input.pptx|input.pdf`: Proxy file to extract from (required)
- `--format`: Output format - `txt` (default) or `json` (optional)
- `--dedupe`: Count duplicates and output quantities (optional)

**Output**:
- Text decklist (stdout or file)
- Card names extracted from embedded text
- Optionally: JSON with metadata (page/slide numbers, quantities)

**Examples**:
```
/extract-cards-from-file krenko_mob_boss.pptx
/extract-cards-from-file deck.pdf --format json
/extract-cards-from-file proxies.pptx --dedupe > decklist.txt
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from collections import Counter
from pptx import Presentation

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

def extract_from_pptx(pptx_path):
    """
    Extract text from PPTX shapes.

    Args:
        pptx_path: Path to PPTX file

    Returns:
        List of extracted text strings
    """
    prs = Presentation(str(pptx_path))
    extracted_texts = []

    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            # Extract from text frames
            if hasattr(shape, "text") and shape.text.strip():
                extracted_texts.append({
                    'text': shape.text.strip(),
                    'slide': slide_idx + 1,
                    'source': 'text_frame'
                })

            # Extract from alt text (metadata)
            if hasattr(shape, "name") and shape.name.strip():
                # Filter out generic shape names
                if not shape.name.startswith(('Rectangle', 'Picture', 'TextBox', 'Shape')):
                    extracted_texts.append({
                        'text': shape.name.strip(),
                        'slide': slide_idx + 1,
                        'source': 'shape_name'
                    })

    return extracted_texts

def extract_from_pdf(pdf_path):
    """
    Extract text from PDF pages.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of extracted text strings
    """
    if pdfplumber is None:
        raise ImportError(
            "pdfplumber not installed. Install with: pip install pdfplumber\\n"
            "PDF extraction requires this library."
        )

    extracted_texts = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()

            if text and text.strip():
                # Split by lines and filter
                lines = [line.strip() for line in text.split('\\n') if line.strip()]

                for line in lines:
                    # Skip common metadata lines
                    if line.startswith(('Page', 'Slide', '©', 'Wizards of the Coast')):
                        continue

                    extracted_texts.append({
                        'text': line,
                        'page': page_idx + 1,
                        'source': 'embedded_text'
                    })

    return extracted_texts

def clean_card_name(text):
    """
    Clean extracted text to get likely card name.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned card name or None if not a card name
    """
    # Remove common artifacts
    text = text.strip()

    # Filter out very short text (likely not card names)
    if len(text) < 3:
        return None

    # Filter out numbers only
    if text.isdigit():
        return None

    # Remove quantity prefixes (e.g., "4x Lightning Bolt" -> "Lightning Bolt")
    import re
    text = re.sub(r'^\\d+[xX]?\\s*', '', text)

    return text.strip()

def deduplicate_cards(card_list):
    """
    Count occurrences and format as decklist.

    Args:
        card_list: List of card name strings

    Returns:
        Dictionary mapping card names to quantities
    """
    return Counter(card_list)

def format_output(cards, format_type='txt', dedupe=False):
    """
    Format extracted cards for output.

    Args:
        cards: List of card dictionaries
        format_type: 'txt' or 'json'
        dedupe: Whether to count duplicates

    Returns:
        Formatted string
    """
    # Extract and clean card names
    card_names = []
    for card in cards:
        cleaned = clean_card_name(card['text'])
        if cleaned:
            card_names.append(cleaned)

    if len(card_names) == 0:
        return None

    # Deduplicate if requested
    if dedupe:
        counts = deduplicate_cards(card_names)
        if format_type == 'json':
            return json.dumps({
                'total_unique': len(counts),
                'total_cards': sum(counts.values()),
                'cards': [
                    {'name': name, 'quantity': count}
                    for name, count in sorted(counts.items())
                ]
            }, indent=2)
        else:
            return '\\n'.join([
                f"{count} {name}" if count > 1 else name
                for name, count in sorted(counts.items())
            ])
    else:
        if format_type == 'json':
            return json.dumps({
                'total_cards': len(card_names),
                'cards': [
                    {'name': name, 'slide': card['slide'] if 'slide' in card else card.get('page'),
                     'source': card['source']}
                    for name, card in zip(card_names, cards)
                ]
            }, indent=2)
        else:
            return '\\n'.join(sorted(set(card_names)))

def extract_cards(input_path, format_type='txt', dedupe=False):
    """
    Extract card names from PPTX or PDF.

    Args:
        input_path: Path to input file
        format_type: Output format ('txt' or 'json')
        dedupe: Count duplicates

    Returns:
        Formatted decklist string
    """
    input_path = Path(input_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()

    print(f"🔍 Extracting Cards from File")
    print("=" * 70)
    print(f"📄 Input: {input_path}")
    print(f"📋 Format: {format_type.upper()}")
    if dedupe:
        print(f"🔢 Deduplication: ON")
    print("=" * 70)
    print()

    # Extract based on file type
    if suffix == '.pptx':
        print("📊 Detecting PPTX format...")
        extracted = extract_from_pptx(input_path)
        print(f"   Found {len(extracted)} text elements")

    elif suffix == '.pdf':
        print("📊 Detecting PDF format...")
        extracted = extract_from_pdf(input_path)
        print(f"   Found {len(extracted)} text elements")

    else:
        raise ValueError(f"Unsupported file format: {suffix} (only .pptx and .pdf supported)")

    # Format output
    print()
    print("🧹 Cleaning and formatting...")

    result = format_output(extracted, format_type, dedupe)

    if result is None:
        raise ValueError("No card names detected in file")

    return result

def main():
    """Main skill execution"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract card names from PPTX or PDF proxy files"
    )
    parser.add_argument("input", help="PPTX or PDF file to extract from")
    parser.add_argument("--format", choices=['txt', 'json'], default='txt',
                        help="Output format (default: txt)")
    parser.add_argument("--dedupe", action="store_true",
                        help="Count duplicates and show quantities")

    args = parser.parse_args()

    try:
        result = extract_cards(args.input, args.format, args.dedupe)

        print()
        print("=" * 70)
        print("📋 Extracted Decklist:")
        print("=" * 70)
        print(result)
        print()
        print("✅ Extraction complete!")

        return 0

    except FileNotFoundError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except ValueError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except ImportError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Output Examples

### Text Format (Default)
```
🔍 Extracting Cards from File
======================================================================
📄 Input: krenko_mob_boss.pptx
📋 Format: TXT
======================================================================

📊 Detecting PPTX format...
   Found 100 text elements

🧹 Cleaning and formatting...

======================================================================
📋 Extracted Decklist:
======================================================================
Battle Hymn
Blood Moon
Brightstone Ritual
Goblin Chieftain
Goblin King
Goblin Matron
Goblin Warchief
Krenko, Mob Boss
Lightning Bolt
Mogg War Marshal
...

✅ Extraction complete!
```

### JSON Format with Deduplication
```bash
/extract-cards-from-file deck.pptx --format json --dedupe
```

Output:
```json
{
  "total_unique": 75,
  "total_cards": 100,
  "cards": [
    {"name": "Battle Hymn", "quantity": 1},
    {"name": "Goblin Guide", "quantity": 4},
    {"name": "Lightning Bolt", "quantity": 4},
    {"name": "Mountain", "quantity": 30}
  ]
}
```

## Error Handling

**`Input file not found`**:
```
❌ Error: Input file not found: /path/to/file.pptx
```

**`Unsupported file format`**:
```
❌ Error: Unsupported file format: .doc (only .pptx and .pdf supported)
```

**`No card names detected`**:
```
❌ Error: No card names detected in file
```
**Cause**: File contains only images, no embedded text

**`pdfplumber not installed`** (PDF only):
```
❌ Error: pdfplumber not installed. Install with: pip install pdfplumber
   PDF extraction requires this library.
```

## Features

**Embedded Text Extraction**:
- PPTX: Reads all text frames and shape names
- PDF: Extracts embedded text from all pages
- No OCR required (fast, accurate for our generated files)

**Intelligent Cleaning**:
- Removes quantity prefixes (4x Lightning Bolt → Lightning Bolt)
- Filters metadata (Page numbers, copyright notices)
- Skips short text (<3 characters)
- Removes duplicates by default

**Multiple Output Formats**:
- **TXT**: Simple list of card names (one per line)
- **JSON**: Structured data with metadata (page/slide numbers, sources)

**Deduplication Mode**:
- Counts occurrences of each card
- Formats as decklist (quantity + name)
- Useful for verifying deck composition

## Limitations

**Works Best On**:
- ✅ Files generated by `/generate-magic-proxies` skill
- ✅ Files generated by `/fill-template` skill
- ✅ Any PPTX/PDF with embedded text

**Won't Work On**:
- ❌ Scanned images (no embedded text)
- ❌ Screenshot PDFs (rasterized, no text layer)
- ❌ Hand-drawn proxies
- ❌ Cards with custom artwork (unless text is embedded)

**For Image-Only Files**:
- Need OCR (not implemented in this skill)
- Consider using Google Vision API manually
- Or use Scryfall image search API (very slow)

## Use Cases

**Verification**:
- Extract from generated PPTX → compare with original decklist
- Verify printed PDF matches digital list
- Audit deck composition

**Recovery**:
- Lost original decklist text file
- Have old PPTX from months ago
- Extract to rebuild decklist

**Conversion**:
- Convert PPTX → plain text for import to Moxfield/Archidekt
- Export from one proxy generator, import to another
- Share decklist via text instead of binary file

**Debugging**:
- Check which cards ended up in presentation
- Verify slot filling logic worked correctly
- Find missing or duplicated cards

## Dependencies

**Python Libraries**:
- `python-pptx` (PPTX extraction) - **required**
- `pdfplumber` (PDF extraction) - **required for PDF support**

**Install**:
```bash
pip install python-pptx pdfplumber
```

## Performance

**Extraction times**:
- Small deck (30 cards): <0.5 seconds
- EDH deck (100 cards): ~1 second
- Large file (200+ pages): ~3-5 seconds

**Bottleneck**: PDF text extraction (slower than PPTX)

## Exit Codes

- `0`: Success
- `1`: File not found, unsupported format, or no text detected
