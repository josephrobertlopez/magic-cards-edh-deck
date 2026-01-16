# MTG Deck Proxy Generator

Automatically generate printable MTG deck proxies from a card list.

## Features

- Fetches card images from Scryfall API
- Generates print-ready PDFs with proper MTG card dimensions (2.5" × 3.5")
- Optimized layout: 8 cards per page on US Letter paper (8.5" × 11")
- Centered layout with white background
- Ready to print, cut, and sleeve

## Quick Start

### Prerequisites

```bash
pip install python-pptx pillow requests
```

### Usage

1. Create a text file with your card list (one card per line):

```text
Sol Ring
Lightning Bolt
Swords to Plowshares
...
```

2. Run the generator:

```bash
python3 generate_deck.py decklists/your_deck.txt
```

3. Print the PDF:

```bash
outputs/deck.pdf
```

**Important**: Print at **100% scale** (no fit-to-page) to maintain correct card dimensions.

## Output Files

- `outputs/deck.pdf` - Print-ready PDF
- `outputs/deck.pptx` - Editable PowerPoint source
- `images/` - Downloaded card images (cached for reuse)

## Card Layout

```
┌─────────────────────────┐
│  [Card] [Card]          │  Row 1
│  [Card] [Card]          │  Row 2
│  [Card] [Card]          │  Row 3
│  [Card] [Card]          │  Row 4
└─────────────────────────┘
    8.5" × 11" Letter
```

- 8 cards per page in 2×4 grid
- Cards rotated landscape for efficient layout
- Each card: 2.5" × 3.5" (standard MTG size)
- Compatible with standard card sleeves

## Example

See `decklists/user_deck.txt` for an example 71-card Green-White counters deck.

```bash
python3 generate_deck.py decklists/user_deck.txt
```

Generates 9 pages (8 cards × 9 pages = 71 cards total).

## Notes

- Card images are cached in `images/` directory
- Subsequent runs are faster (no re-downloading)
- Requires internet connection for first run
- LibreOffice optional for PDF conversion (otherwise generates PPTX only)

## Legal

This tool is for personal use only. All card images are © Wizards of the Coast.
Do not use for commercial purposes.
