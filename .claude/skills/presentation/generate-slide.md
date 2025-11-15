# generate-slide

Atomic skill: Generate PPTX slides from card images (9 cards per slide layout).

## A2A Interface

**REQUEST Message**:
```json
{
  "image_paths": [
    "images/black_lotus.jpg",
    "images/mox_sapphire.jpg"
  ],
  "output_file": "outputs/commander_proxies.pptx",
  "options": {
    "cards_per_slide": 9,
    "template": "template_2v6h_FIXED.pptx",
    "slide_width_inches": 10,
    "slide_height_inches": 7.5
  }
}
```

**RESPONSE Message**:
```json
{
  "pptx_path": "outputs/commander_proxies.pptx",
  "total_images": 100,
  "total_slides": 12,
  "cards_per_slide": 9,
  "status": "success"
}
```

## Contract

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "image_paths": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1
    },
    "output_file": {"type": "string"},
    "options": {
      "type": "object",
      "properties": {
        "cards_per_slide": {"type": "integer", "default": 9},
        "template": {"type": "string", "default": "template_2v6h_FIXED.pptx"},
        "slide_width_inches": {"type": "number", "default": 10},
        "slide_height_inches": {"type": "number", "default": 7.5}
      }
    }
  },
  "required": ["image_paths", "output_file"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "pptx_path": {"type": "string"},
    "total_images": {"type": "integer"},
    "total_slides": {"type": "integer"},
    "cards_per_slide": {"type": "integer"},
    "status": {"type": "string", "enum": ["success", "failed"]}
  },
  "required": ["pptx_path", "total_images", "total_slides", "status"]
}
```

## Single Responsibility

**Does**: Generate PPTX presentation from image file paths
**Does NOT**: Fetch card data, download images, convert to PDF, resize images

## Batch Processing Support

⚠️ **Not batch-compatible**: This skill generates a single PPTX file from all images. Batching happens upstream (fetch-card-image skill).

## Domain-Agnostic Uses

- **Photo Albums**: Generate presentation from photo directory
- **Product Catalogs**: Create visual catalogs from product images
- **Design Portfolios**: Generate portfolio presentations
- **Real Estate**: Create property listing presentations
- **Event Galleries**: Generate event photo slideshows

## Parameters

- `image_paths` (required): Array of image file paths to include
- `output_file` (required): Output PPTX file path
- `options.cards_per_slide` (optional, default: 9): Images per slide (3x3 grid)
- `options.template` (optional): Base template PPTX file
- `options.slide_width_inches` (optional, default: 10): Slide width
- `options.slide_height_inches` (optional, default: 7.5): Slide height

## Usage

**Generate proxies from images**:
```bash
/presentation/generate-slide \
  --images images/*.jpg \
  --output outputs/proxies.pptx
```

**Custom layout**:
```bash
/presentation/generate-slide \
  --images images/*.jpg \
  --output outputs/proxies.pptx \
  --cards-per-slide 6 \
  --template custom_template.pptx
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from pptx import Presentation
from pptx.util import Inches
from PIL import Image
import math

def create_slide_layout(
    prs: Presentation,
    image_paths: List[str],
    cards_per_slide: int,
    slide_width: float,
    slide_height: float
) -> None:
    """
    Add slide with card images in grid layout.

    Args:
        prs: Presentation object
        image_paths: Paths to images for this slide
        cards_per_slide: Number of cards per slide (9 = 3x3 grid)
        slide_width: Slide width in inches
        slide_height: Slide height in inches
    """
    # Calculate grid dimensions (assumes square grid)
    grid_size = int(math.sqrt(cards_per_slide))

    # Add blank slide
    blank_slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(blank_slide_layout)

    # Calculate image dimensions and positions
    margin = 0.25  # inches
    available_width = slide_width - (2 * margin)
    available_height = slide_height - (2 * margin)

    image_width = available_width / grid_size
    image_height = available_height / grid_size

    # Place images in grid
    for idx, image_path in enumerate(image_paths):
        if idx >= cards_per_slide:
            break

        row = idx // grid_size
        col = idx % grid_size

        left = Inches(margin + (col * image_width))
        top = Inches(margin + (row * image_height))
        width = Inches(image_width)
        height = Inches(image_height)

        try:
            slide.shapes.add_picture(
                image_path,
                left,
                top,
                width=width,
                height=height
            )
        except Exception as e:
            print(f"Warning: Failed to add image {image_path}: {e}", file=sys.stderr)

def generate_pptx(
    image_paths: List[str],
    output_file: str,
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate PPTX presentation from image paths.

    Args:
        image_paths: List of image file paths
        output_file: Output PPTX file path
        options: Generation options

    Returns:
        Result dict with pptx_path, counts, status
    """
    cards_per_slide = options.get("cards_per_slide", 9)
    template = options.get("template")
    slide_width = options.get("slide_width_inches", 10)
    slide_height = options.get("slide_height_inches", 7.5)

    try:
        # Create presentation (from template or blank)
        if template and Path(template).exists():
            prs = Presentation(template)
        else:
            prs = Presentation()
            prs.slide_width = Inches(slide_width)
            prs.slide_height = Inches(slide_height)

        # Calculate number of slides needed
        total_images = len(image_paths)
        total_slides = math.ceil(total_images / cards_per_slide)

        # Generate slides
        for slide_idx in range(total_slides):
            start_idx = slide_idx * cards_per_slide
            end_idx = min(start_idx + cards_per_slide, total_images)
            slide_images = image_paths[start_idx:end_idx]

            create_slide_layout(
                prs,
                slide_images,
                cards_per_slide,
                slide_width,
                slide_height
            )

        # Save presentation
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        prs.save(output_file)

        return {
            "pptx_path": output_file,
            "total_images": total_images,
            "total_slides": total_slides,
            "cards_per_slide": cards_per_slide,
            "status": "success"
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "error_type": "PPTX_GENERATION_ERROR"
        }

def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "image_paths and output_file required",
            "usage": "generate-slide.py <images_list.json> <output.pptx>"
        }), file=sys.stderr)
        sys.exit(1)

    # Load image paths from JSON file
    images_list_path = sys.argv[1]
    with open(images_list_path, 'r') as f:
        input_data = json.load(f)

    image_paths = input_data.get("images", [])
    if isinstance(image_paths, list) and len(image_paths) > 0:
        # Extract image_path from dicts if present
        if isinstance(image_paths[0], dict):
            image_paths = [img.get("image_path") for img in image_paths if img.get("status") == "success"]

    output_file = sys.argv[2]

    options = {
        "cards_per_slide": 9,
        "slide_width_inches": 10,
        "slide_height_inches": 7.5
    }

    # Generate PPTX
    result = generate_pptx(image_paths, output_file, options)

    # Output JSON result
    print(json.dumps(result, indent=2))

    # Exit with error if failed
    sys.exit(0 if result['status'] == 'success' else 1)

if __name__ == "__main__":
    main()
```

## Error Codes

- `0`: Success (PPTX generated)
- `1`: Failure (check error field)

## Error Types

- `PPTX_GENERATION_ERROR`: Failed to create presentation
- `MISSING_TEMPLATE`: Template file not found
- `INVALID_IMAGE`: Image file cannot be opened

## Performance

- **Memory Efficient**: Processes images one slide at a time
- **Template Support**: Can use existing PPTX as base template
- **Graceful Degradation**: Skips invalid images, continues processing
