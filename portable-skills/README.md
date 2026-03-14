# Portable Skills Toolkit

A decoupled, standalone toolkit for document conversion, HTTP fetching, and presentation generation. Works locally — no sandbox restrictions.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Marp CLI (for MD → PPTX/PDF)
npm install -g @marp-team/marp-cli

# Convert markdown to presentation
python3 document/convert_format.py slides.md slides.pptx --format pptx

# Convert PPTX to PDF
python3 document/convert_format.py deck.pptx deck.pdf --format pdf

# Generate grid layout from images
python3 document/grid_layout.py images/*.jpg --output proxies.pptx --cols 4 --rows 2

# Fetch JSON from any API (bypasses sandbox)
python3 http/fetch_json.py "https://api.scryfall.com/cards/named?fuzzy=osgir" --output card.json

# Download files with retry
python3 http/download_file.py "https://example.com/image.jpg" --output image.jpg --retries 3

# Generate presentation from images
python3 presentation/generate_slide.py images/ --output slides.pptx --per-slide 9
```

## Tools Included

| Tool | Description | Use Cases |
|------|-------------|-----------|
| `document/convert_format.py` | Convert between MD/PPTX/PDF via Marp + LibreOffice | Slides, reports, handouts |
| `document/grid_layout.py` | Arrange images in configurable grids | Card proxies, photo sheets, catalogs |
| `http/fetch_json.py` | Fetch JSON from REST APIs with retry | Scryfall, EDHREC, any API |
| `http/download_file.py` | Download files with streaming + retry | Card images, assets, bulk data |
| `presentation/generate_slide.py` | Generate PPTX from image folders | Proxy sheets, albums, portfolios |
| `bin/marp-convert` | Shell wrapper for Marp CLI | Quick MD→PPTX/PDF |

## Dependencies

- Python 3.8+
- `python-pptx` — PPTX generation
- `Pillow` — Image processing
- `requests` — HTTP client
- Marp CLI (optional) — Markdown → presentation
- LibreOffice (optional) — PPTX → PDF fallback

## Decoupled Design

Every tool is a standalone script. No shared imports, no framework dependency. Copy any single file into your project and it works.
