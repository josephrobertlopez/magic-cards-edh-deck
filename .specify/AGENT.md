# Magic Card Proxy Generator - Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-07

## Active Technologies

**Language/Version**: Python 3.9+

**Primary Dependencies**:
- `python-pptx` >= 0.6.21 - PowerPoint file creation and manipulation
- `Pillow` >= 10.0.0 - Image processing (loading, resizing, rotation)
- `requests` >= 2.31.0 - HTTP requests to Scryfall API
- `LibreOffice` - System dependency for PPTX → PDF conversion

**Testing**: Manual validation with regression test decks (Krenko 100 cards, Frog Tribal 75 cards)

**Target Platform**: Cross-platform CLI (Linux/macOS/Windows via Python)

**Performance Goals**:
- <5 seconds execution time (excluding network downloads)
- Scryfall API rate limit compliance (10 req/sec)

**Constraints**:
- Single CLI entry point
- ≤8 total files (excluding outputs/tests)
- ≤300 lines core logic
- Exactly 1 canonical template file

## Project Structure

```text
magic-cards-edh-deck/
├── proxy_generator.py       # CLI entry point (argparse)
├── template_2v6h_FIXED.pptx # Canonical template (11.0" x 8.5")
├── requirements.txt         # Python dependencies
├── README.md                # User documentation
│
├── magic_cards/             # Core modules
│   ├── __init__.py          # Module exports
│   ├── fetch.py             # Scryfall API integration, DFC support
│   ├── template.py          # Template slot detection (2v+6h layout)
│   ├── layout.py            # Card placement, rotation, aspect ratio handling
│   └── export.py            # PPTX → PDF conversion via LibreOffice
│
├── decklists/               # Input: card lists
│   ├── krenko_mob_boss.txt
│   └── frog_tribal.txt
│
├── outputs/                 # Generated artifacts (gitignored)
│   ├── *.pptx
│   └── *.pdf
│
├── .claude/
│   ├── cards/               # Downloaded card images (cached)
│   │   ├── card_name.jpg
│   │   └── card_name_face_*.jpg  # DFC faces
│   └── state/
│       └── *_manifest.json  # Card fetch metadata
│
└── specs/                   # Feature specifications
    └── 002-consolidate-codebase/
        ├── spec.md          # Feature requirements
        ├── plan.md          # Implementation plan
        ├── research.md      # Technical research
        ├── data-model.md    # Data structures
        ├── quickstart.md    # User guide
        ├── contracts/       # Module contracts
        └── tasks.md         # Task breakdown (pending)
```

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Generate proxies from decklist
python proxy_generator.py decklists/my_deck.txt

# Custom template
python proxy_generator.py decklists/my_deck.txt --template custom.pptx

# Force re-download
python proxy_generator.py decklists/my_deck.txt --force

# Skip PDF (PPTX only)
python proxy_generator.py decklists/my_deck.txt --no-pdf
```

### Testing
```bash
# Regression test 1: Krenko deck (100 cards)
python proxy_generator.py decklists/krenko_mob_boss.txt

# Regression test 2: Frog Tribal deck (75 cards)
python proxy_generator.py decklists/frog_tribal.txt

# Verify outputs match existing FIXED versions
diff outputs/krenko_mob_boss.pptx krenko_mob_boss_FIXED.pptx
```

### System Dependencies
```bash
# Linux (Debian/Ubuntu)
sudo apt install libreoffice

# Linux (Fedora/RHEL)
sudo dnf install libreoffice

# macOS
brew install --cask libreoffice

# Windows: Download from libreoffice.org
```

## Code Style

### Python Style Guidelines

**Import Organization**:
```python
# Standard library
import os
import json
import math

# Third-party
from pptx import Presentation
from pptx.util import Inches
from PIL import Image
import requests

# Local modules
from magic_cards import fetch, template, layout, export
```

**Function Documentation**:
```python
def fetch_cards(decklist_path: str, force: bool = False) -> str:
    """
    Download card images from Scryfall API and create manifest.

    Args:
        decklist_path: Path to decklist text file
        force: Re-download even if cached

    Returns:
        Path to generated manifest JSON file

    Raises:
        FileNotFoundError: Decklist doesn't exist
    """
```

**Error Handling**:
- Use descriptive error messages with actionable guidance
- Log warnings for partial failures, errors for complete failures
- Return meaningful exit codes (see contracts/cli_entry_point.md)

**Naming Conventions**:
- Functions: `snake_case` (e.g., `fetch_cards`, `get_slot_positions`)
- Classes: `PascalCase` (minimal classes expected)
- Constants: `UPPER_SNAKE_CASE` (e.g., `SCRYFALL_API_URL`)
- Private functions: Leading underscore (e.g., `_sanitize_filename`)

**Module Organization**:
- Each module has single responsibility (fetch, template, layout, export)
- Public API at top of module
- Helper functions below
- Main execution guard: `if __name__ == "__main__":`

## Recent Changes

### Feature 001: Scryfall Skills (Completed)
**Added**: Claude Code skills for fetching Magic cards and generating presentations
- `.claude/skills/fetch_scryfall_cards.md`
- `.claude/skills/generate_magic_card_pptx.md`
- Working scripts: `run_fetch_krenko.py`, `create_correct_template_layout.py`
- Test outputs: `krenko_mob_boss_FIXED.pptx/pdf`, `frog_tribal_FIXED.pptx/pdf`

### Feature 002: Codebase Consolidation (In Planning)
**Status**: Planning phase complete, ready for task generation
- Specification created: `specs/002-consolidate-codebase/spec.md`
- Implementation plan: `specs/002-consolidate-codebase/plan.md`
- Research completed: All technical questions resolved
- Data model defined: Card metadata, manifest, template slots
- Contracts documented: All 5 modules (fetch, template, layout, export, CLI)
- User guide: `specs/002-consolidate-codebase/quickstart.md`
**Next**: Run `/speckit.tasks` to generate task breakdown

## Technical Context

### Module Responsibilities

**`magic_cards/fetch.py`**:
- Scryfall API integration (fuzzy card name search)
- DFC (double-faced card) handling
- Image caching in `.claude/cards/`
- Manifest JSON generation
- Rate limiting compliance (10 req/sec)

**`magic_cards/template.py`**:
- PowerPoint template analysis
- Card slot detection (rectangles ≥1.0" × 1.0")
- Orientation classification (vertical vs horizontal)
- Slot position sorting

**`magic_cards/layout.py`**:
- PPTX presentation generation
- Card image placement in slots
- Aspect ratio preservation
- Card rotation (portrait → horizontal slots)
- White background for printing

**`magic_cards/export.py`**:
- PPTX → PDF conversion
- LibreOffice subprocess management
- Cross-platform binary detection
- Error handling for missing dependencies

**`proxy_generator.py`**:
- Command-line argument parsing
- Module coordination (fetch → layout → export)
- Progress reporting
- Error messages and exit codes

### Key Algorithms

**Slot Detection** (`template.py`):
1. Iterate template slide shapes
2. Filter by type (rectangle/auto-shape) and size (≥1.0")
3. Calculate aspect ratio (width/height)
4. Classify orientation (>1.0 = horizontal, ≤1.0 = vertical)
5. Sort by position (top, then left)

**Card Placement** (`layout.py`):
1. Flatten card list (expand DFCs into separate slots)
2. Calculate slides needed (cards ÷ slots per slide, round up)
3. For each slide:
   - Create blank slide with white background
   - For each slot:
     - Get next card
     - Load image
     - Calculate fit (preserve aspect ratio)
     - Rotate if needed (portrait card in horizontal slot)
     - Center in slot
     - Add to slide

**Rotation Logic**:
- Vertical slots: Portrait cards as-is, landscape cards as-is
- Horizontal slots: Portrait cards rotated 90° clockwise, landscape cards as-is

### Data Contracts

**Manifest JSON**:
```json
{
    "decklist": "path/to/decklist.txt",
    "timestamp": "2025-11-07T15:30:00Z",
    "total_cards": 75,
    "successful": 73,
    "failed": 2,
    "cards": [
        {
            "name": "Card Name",
            "status": "success",
            "path": ".claude/cards/card_name.jpg",  # Single-faced
            "faces": 1
        },
        {
            "name": "DFC Name",
            "status": "success",
            "faces": 2,
            "paths": ["face_0.jpg", "face_1.jpg"]  # Multi-faced
        }
    ]
}
```

**Template Slot**:
```python
{
    "left": 0.5,          # inches
    "top": 0.75,          # inches
    "width": 2.5,         # inches
    "height": 3.5,        # inches
    "orientation": "vertical",   # "vertical" | "horizontal"
    "aspect_ratio": 0.714        # width / height
}
```

### Consolidation Goals

**Files to DELETE** (16-20 iteration artifacts):
- `analyze_templates.py`
- `correct_template.pptx`
- `create_correct_template_layout.py` (extract logic first)
- `example_output.pptx`
- `fetch_krenko.sh`
- `generate_frog_deck.py`
- `run_fetch_krenko.py` (extract logic first)
- `run_fetch_frogs.py`
- `TEMPLATE_ANALYSIS_REPORT.md`
- 10-12 additional template PPTX files

**Files to CREATE**:
- `magic_cards/__init__.py`
- `magic_cards/fetch.py`
- `magic_cards/template.py`
- `magic_cards/layout.py`
- `magic_cards/export.py`
- `proxy_generator.py`
- `requirements.txt`

**Validation Criteria**:
- Generated PPTX matches existing `*_FIXED.pptx` files visually
- PDF dimensions: 11.0" × 8.5" (US Letter landscape)
- Card orientation correct (2 vertical + 6 horizontal per page)
- White backgrounds for printing
- No clipping or aspect ratio distortion

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
