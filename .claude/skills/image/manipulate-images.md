# manipulate-images

Generic image manipulation: resize, rotate, crop, adjust aspect ratios.

## A2A Interface

**REQUEST Message**:
```json
{
  "operation": "resize",  // resize | rotate | crop | fit
  "images": ["img1.jpg", "img2.png"],
  "params": {
    "target_width": 150,   // DPI or pixels
    "target_height": 150,
    "preserve_aspect": true,
    "rotation": 90,        // degrees (for rotate)
    "quality": 90          // JPEG quality
  },
  "output_dir": "processed"
}
```

**RESPONSE Message**:
```json
{
  "processed_images": ["processed/img1.jpg", "processed/img2.png"],
  "total": 2,
  "successful": 2,
  "failed": 0
}
```

## Domain-Agnostic Uses

- **MTG Cards**: Resize/rotate cards for presentation slots
- **Screenshots**: Resize screenshots for documentation
- **Photos**: Batch resize photos for web galleries
- **Charts**: Fit charts into specific dimensions
- **Thumbnails**: Generate thumbnails from images

## Operations

### resize
Resize images to target dimensions with aspect ratio preservation.

### rotate
Rotate images (useful for portrait → landscape conversion).

### fit
Fit images into bounding box (letterbox/pillarbox if needed).

### crop
Crop images to specific dimensions.

## Parameters

- `operation` (required): Operation type
- `images` (required): List of image paths
- `params` (required): Operation-specific parameters
- `output_dir` (optional): Output directory (default: "processed")

## Usage

**Resize for PPTX slots**:
```bash
/image/manipulate-images \
  --operation resize \
  --images images/*.jpg \
  --width 150 \
  --height 150 \
  --preserve-aspect \
  --output processed
```

**Rotate portrait to landscape**:
```bash
/image/manipulate-images \
  --operation rotate \
  --images images/portrait.jpg \
  --rotation 90 \
  --output rotated
```

**Fit into bounding box**:
```bash
/image/manipulate-images \
  --operation fit \
  --images screenshots/*.png \
  --width 800 \
  --height 600 \
  --output fitted
```

## Implementation

Uses PIL/Pillow for image operations. Can extend `magic_cards.document_generator` image manipulation logic.
