# place-images-in-pptx

Generic PPTX generation: detect template slots, place images with aspect ratio fitting.

## A2A Interface

**REQUEST Message**:
```json
{
  "template_path": "template.pptx",
  "image_manifest": {
    "images": [
      {"path": "img1.jpg", "metadata": {"name": "Item 1"}},
      {"path": "img2.jpg", "metadata": {"name": "Item 2"}}
    ]
  },
  "output_path": "output.pptx",
  "layout_config": {
    "min_slot_size": 1.0,     // inches
    "aspect_fit": true,        // preserve aspect ratio
    "auto_rotate": true,       // rotate portrait → landscape
    "background_color": "white"
  }
}
```

**RESPONSE Message**:
```json
{
  "pptx_path": "output.pptx",
  "total_images": 75,
  "pages": 10,
  "slots_per_page": 8
}
```

## Domain-Agnostic Uses

- **MTG Cards**: Place card images in 2v+6h layout
- **Photo Albums**: Create photo presentation from folder
- **Code Screenshots**: Generate presentation from code screenshots
- **Charts/Graphs**: Layout charts in template slides
- **Product Catalog**: Generate catalog from product images

## Features

### Auto Slot Detection
Scans template for rectangles ≥ min_slot_size, determines orientation (vertical/horizontal).

### Aspect Ratio Fitting
Places images preserving aspect ratio (no stretching/clipping).

### Auto Rotation
Rotates portrait images for horizontal slots (optional).

### Background Control
Sets slide backgrounds (white, black, transparent, custom).

## Parameters

- `template_path` (required): Template PPTX file
- `image_manifest` (required): List of images with optional metadata
- `output_path` (required): Output PPTX path
- `layout_config` (optional): Layout configuration

## CLI Usage

**Standalone Invocation** (User Story 1):
```bash
python3 .claude/skills/presentation/place-images-in-pptx.py \
  --manifest .claude/state/my_deck_manifest.json \
  --template template_2v6h_FIXED.pptx \
  --output outputs/my_deck.pptx
```

**Parameters**:
- `--manifest` (required): Path to manifest JSON file (from fetch-from-api skill)
- `--template` (required): Path to PowerPoint template file (.pptx)
- `--output` (required): Path for output PowerPoint file

**Success Output** (JSON to stdout):
```json
{
  "status": "success",
  "pptx_path": "outputs/my_deck.pptx",
  "manifest": ".claude/state/my_deck_manifest.json",
  "template": "template_2v6h_FIXED.pptx"
}
```

**Error Output** (JSON to stderr):
```json
{
  "status": "error",
  "error": "Manifest file not found: .claude/state/missing.json",
  "exit_code": 1,
  "context": {"manifest": ".claude/state/missing.json"}
}
```

**Exit Codes**:
- `0`: Success
- `1`: Resource/file not found
- `5`: Conversion/generation error

## Template Format

Templates should have:
- Rectangles or auto-shapes ≥ min_slot_size (default 1.0")
- Consistent slot positions across slides
- Optional background styling

Example 2v+6h layout:
```
Slide 1:
┌─────────┬─────────┐
│ 2.5"x3.5" (V) │ 2.5"x3.5" (V) │  ← 2 vertical slots
├─────────┴─────────┤
│ 3.5"x2.5" (H)     │  ← 6 horizontal slots
│ 3.5"x2.5" (H)     │
│ 3.5"x2.5" (H)     │
└───────────────────┘
Total: 8 slots per page
```

## Implementation

Wraps `magic_cards.document_generator` module with domain-agnostic interface.
