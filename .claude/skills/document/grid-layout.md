---
name: "document/grid-layout"
description: "Arrange images into grid layouts on presentation slides"
version: "1.0.0"
supports_batch: false

inputs:
  - name: image_paths
    type: list
    required: true
    description: "List of image file paths to arrange in grid"

  - name: rows
    type: integer
    required: true
    description: "Number of rows per slide"

  - name: columns
    type: integer
    required: true
    description: "Number of columns per slide"

  - name: output_path
    type: string
    required: true
    description: "Path to save generated PPTX file"

  - name: slide_width
    type: number
    required: false
    default: 10
    description: "Slide width in inches"

  - name: slide_height
    type: number
    required: false
    default: 7.5
    description: "Slide height in inches"

  - name: margin
    type: number
    required: false
    default: 0.5
    description: "Margin around grid in inches"

  - name: spacing
    type: number
    required: false
    default: 0.1
    description: "Spacing between cells in inches"

  - name: placeholder_text
    type: string
    required: false
    default: "Image Not Available"
    description: "Text to show when image file is missing"

outputs:
  - name: path
    type: string
    description: "Full path to generated PPTX file"

  - name: slide_count
    type: integer
    description: "Number of slides created"

  - name: images_per_slide
    type: integer
    description: "Maximum images per slide (rows × columns)"

  - name: missing_images_count
    type: integer
    description: "Count of missing image files (placeholders used)"
---

# document/grid-layout

Arrange images into customizable grid layouts on presentation slides.

## Purpose

This skill provides domain-agnostic grid layout generation for any set of images. It works with any image collection including card proxies, product catalogs, employee directories, photo albums, event galleries, and any other visual content that benefits from grid organization.

## Implementation

### Prerequisites

- Python 3.9+
- python-pptx library
- Pillow (PIL) for image handling
- pathlib (stdlib)

### Algorithm

1. **Calculate Layout**: images_per_slide = rows × columns
2. **Calculate Slide Count**: slide_count = ceil(len(image_paths) / images_per_slide)
3. **Calculate Cell Dimensions**:
   - available_width = slide_width - (2 × margin) - ((columns - 1) × spacing)
   - available_height = slide_height - (2 × margin) - ((rows - 1) × spacing)
   - cell_width = available_width / columns
   - cell_height = available_height / rows
4. **Create Presentation**: Initialize PPTX with specified dimensions
5. **For Each Slide**:
   - Create blank slide
   - Get batch of images (up to images_per_slide)
   - For each image in batch:
     - Calculate cell position (row, col)
     - If image exists: Add to slide at position with aspect ratio preserved
     - If image missing: Add text box with placeholder_text
6. **Save Presentation**: Write to output_path
7. **Return Result**: {path, slide_count, images_per_slide, missing_images_count}

### Error Handling

- **Missing image files**: Show placeholder text (no error)
- **Invalid image format**: Show placeholder text (log warning)
- **Output directory missing**: Create parent directories automatically
- **Invalid grid dimensions**: Raise INVALID_GRID error (rows/columns must be > 0)
- **Empty image list**: Raise EMPTY_INPUT error

### Pseudo-code

```python
from pptx import Presentation
from pptx.util import Inches
from PIL import Image
from pathlib import Path
import math

def execute_document_grid_layout(args):
    image_paths = args["image_paths"]
    rows = args["rows"]
    columns = args["columns"]
    output_path = Path(args["output_path"])
    slide_width = args.get("slide_width", 10)
    slide_height = args.get("slide_height", 7.5)
    margin = args.get("margin", 0.5)
    spacing = args.get("spacing", 0.1)
    placeholder_text = args.get("placeholder_text", "Image Not Available")

    # Validate inputs
    if rows <= 0 or columns <= 0:
        raise Exception("INVALID_GRID: rows and columns must be > 0")
    if not image_paths:
        raise Exception("EMPTY_INPUT: image_paths cannot be empty")

    # Calculate layout
    images_per_slide = rows * columns
    slide_count = math.ceil(len(image_paths) / images_per_slide)

    # Calculate cell dimensions
    available_width = slide_width - (2 * margin) - ((columns - 1) * spacing)
    available_height = slide_height - (2 * margin) - ((rows - 1) * spacing)
    cell_width = available_width / columns
    cell_height = available_height / rows

    # Create presentation
    prs = Presentation()
    prs.slide_width = Inches(slide_width)
    prs.slide_height = Inches(slide_height)

    missing_count = 0

    # Process images in batches (one batch per slide)
    for slide_num in range(slide_count):
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

        # Get batch of images for this slide
        start_idx = slide_num * images_per_slide
        end_idx = min(start_idx + images_per_slide, len(image_paths))
        batch = image_paths[start_idx:end_idx]

        # Place images in grid
        for idx, img_path in enumerate(batch):
            row = idx // columns
            col = idx % columns

            # Calculate position
            left = margin + (col * (cell_width + spacing))
            top = margin + (row * (cell_height + spacing))

            # Add image or placeholder
            if Path(img_path).exists():
                try:
                    slide.shapes.add_picture(
                        img_path,
                        Inches(left),
                        Inches(top),
                        width=Inches(cell_width),
                        height=Inches(cell_height)
                    )
                except Exception:
                    # Invalid image format
                    add_text_placeholder(slide, left, top, cell_width, cell_height, placeholder_text)
                    missing_count += 1
            else:
                # Missing file
                add_text_placeholder(slide, left, top, cell_width, cell_height, placeholder_text)
                missing_count += 1

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save presentation
    prs.save(str(output_path))

    return {
        "path": str(output_path),
        "slide_count": slide_count,
        "images_per_slide": images_per_slide,
        "missing_images_count": missing_count
    }

def add_text_placeholder(slide, left, top, width, height, text):
    """Add centered text box as placeholder."""
    textbox = slide.shapes.add_textbox(
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height)
    )
    textbox.text = text
    # Center align, set font, etc.
```

## Usage Examples

### Example 1: Card Proxy Grid (3×3)

```yaml
- name: generate_card_proxies
  skill: document/grid-layout
  args:
    image_paths: "{{card_images}}"
    rows: 3
    columns: 3
    output_path: "/tmp/proxies/commander_deck.pptx"
  outputs:
    pptx_path: "{{result.path}}"
```

### Example 2: Product Catalog (4×2)

```yaml
- name: generate_catalog
  skill: document/grid-layout
  args:
    image_paths: "{{product_images}}"
    rows: 4
    columns: 2
    output_path: "/tmp/catalogs/winter_2024.pptx"
    slide_width: 11
    slide_height: 8.5
  outputs:
    catalog_path: "{{result.path}}"
```

### Example 3: Photo Album with Custom Spacing

```yaml
- name: generate_album
  skill: document/grid-layout
  args:
    image_paths: "{{vacation_photos}}"
    rows: 2
    columns: 2
    output_path: "/tmp/albums/hawaii_trip.pptx"
    margin: 1.0
    spacing: 0.5
  outputs:
    album_path: "{{result.path}}"
```

## Domain-Agnostic Design

This skill contains **zero domain-specific logic**. It works equally well for:

- Gaming: Card proxies, character sheets, game boards
- E-commerce: Product catalogs, lookbooks, price sheets
- Corporate: Employee directories, team photos, org charts
- Personal: Photo albums, scrapbooks, collages
- Real Estate: Property listings, floor plan galleries
- Education: Student rosters, flashcards, visual aids

The skill accepts any list of image paths and arranges them in a grid without assumptions about content type or purpose.
