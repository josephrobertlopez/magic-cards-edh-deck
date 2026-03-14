# Proxy Grid Generator

Generate print-ready proxy sheets from any images using a configurable grid layout.

Works with custom card art, tokens, alters, Scryfall images, or any image files.

## Arguments
- $ARGUMENTS: Images to lay out, plus optional grid/paper options. Examples:
  - `images/*.jpg` — all cached card images, default 2x4 MTG layout
  - `3x3 images/my_custom_*.png` — custom art in a 3x3 grid
  - `full-art images/alter1.jpg images/alter2.jpg` — 2x2 large layout
  - `token images/tokens/*.png` — 3x3 token sheet

## Instructions

1. **Parse the request** to determine:
   - Which images to include (file paths, glob patterns, or a directory)
   - Grid preset or custom rows/cols
   - Paper size if specified
   - Whether to rotate (landscape) or keep portrait

2. **If images aren't specified**, check common locations:
   - `images/` — cached Scryfall card images
   - Look for `.jpg`, `.png`, `.jpeg` files
   - Ask the user if ambiguous

3. **Run `grid_layout.py`** with the appropriate flags:
   ```bash
   python3 grid_layout.py [OPTIONS] <image_files>
   ```

   Available presets (use `--preset`):
   | Preset | Grid | Rotation | Cards/Page |
   |--------|------|----------|------------|
   | `mtg` (default) | 2x4 | landscape | 8 |
   | `mtg-3x3` | 3x3 | portrait | 9 |
   | `token` | 3x3 | portrait | 9 |
   | `full-art` | 2x2 | portrait | 4 |
   | `playtest` | 3x5 | portrait | 15 |

   Key flags:
   - `--preset <name>` — use a preset grid config
   - `--rows N --cols N` — custom grid dimensions
   - `--paper letter|a4|legal|tabloid` — paper size
   - `--no-rotate` — keep portrait orientation
   - `--bg white|black` — background color
   - `--margin 0.3` — page margin in inches
   - `--spacing 0.15` — gap between cards in inches
   - `-o outputs/my_grid.pptx` — output file path
   - `--pdf` — also convert to PDF

4. **Report results**: output file path, grid dimensions, cell size, cards placed, pages generated.

5. **Remind the user** to print at 100% scale (no fit-to-page) for correct card sizing.

## Examples

```bash
# Default MTG proxies from cached images
python3 grid_layout.py images/*.jpg

# Custom art tokens in 3x3 grid
python3 grid_layout.py --preset token -o outputs/tokens.pptx images/tokens/*.png

# Large full-art alters, 4 per page, with PDF
python3 grid_layout.py --preset full-art --pdf -o outputs/alters.pptx images/alter_*.jpg

# Custom 3x5 playtest cards on A4 paper
python3 grid_layout.py --rows 5 --cols 3 --no-rotate --paper a4 images/*.png
```
