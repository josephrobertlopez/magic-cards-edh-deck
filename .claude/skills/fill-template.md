# fill-template

Fill PowerPoint template with Magic card images using slot-based layout.

## Usage

```
/fill-template <template_file> <images_dir> <output_file>
```

**Parameters**:
- `template_file`: Path to PowerPoint template (e.g., decks.pptx)
- `images_dir`: Directory containing card images
- `output_file`: Path for output presentation

**Input**:
- Reads JSON manifest from `.claude/state/fetch_manifest.json`
- Uses successful cards from manifest

**Examples**:
```
/fill-template decks.pptx images output_deck.pptx
/fill-template my_template.pptx images/ my_deck.pptx
```

## Implementation

```python
#!/usr/bin/env python3
import os
import json
import math
from pptx import Presentation
from pptx.util import Inches
from pptx.dml.color import RGBColor
from PIL import Image
from pathlib import Path

def get_template_slot_positions(template_slide):
    """
    Extract card slot positions from template (FR-006)
    Returns list of slot dictionaries with left, top, width, height
    """
    card_slots = []

    for shape in template_slide.shapes:
        # Look for rectangular shapes that are card-sized
        if (shape.shape_type in [1, 13] and  # Rectangle or Picture
            shape.width.inches > 1.0 and
            shape.height.inches > 1.0):

            card_slots.append({
                'left': shape.left.inches,
                'top': shape.top.inches,
                'width': shape.width.inches,
                'height': shape.height.inches
            })

    # Sort slots by position (top to bottom, left to right)
    card_slots.sort(key=lambda x: (x['top'], x['left']))

    return card_slots

def place_card_in_slot(slide, card_path, slot_info):
    """
    Place card image in slot with aspect ratio preservation (FR-005, FR-007)
    Handles vertical/horizontal orientation based on slot dimensions
    """
    try:
        # Validate card image exists
        if not os.path.exists(card_path):
            print(f"    ⚠️  Image not found: {card_path}")
            return False

        with Image.open(card_path) as img:
            # Calculate aspect ratios
            slot_aspect = slot_info['width'] / slot_info['height']
            img_aspect = img.width / img.height

            # Determine if slot is horizontal (FR-007)
            is_horizontal_slot = slot_aspect > 1.0

            # Preserve aspect ratio while fitting to slot (FR-005)
            if img_aspect > slot_aspect:
                # Image is wider, fit to width
                new_width = slot_info['width']
                new_height = slot_info['width'] / img_aspect
            else:
                # Image is taller, fit to height
                new_height = slot_info['height']
                new_width = slot_info['height'] * img_aspect

            # Center the image in the slot
            left = slot_info['left'] + (slot_info['width'] - new_width) / 2
            top = slot_info['top'] + (slot_info['height'] - new_height) / 2

            # Resize for quality (150 DPI equivalent)
            target_width = int(new_width * 150)
            target_height = int(new_height * 150)

            resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Rotate if horizontal slot and card is vertical
            if is_horizontal_slot and img_aspect < 1.0:
                resized_img = resized_img.rotate(90, expand=True)

            # Save temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_path = temp_file.name
                resized_img.save(temp_path, "JPEG", quality=90)

        # Add picture to slide
        slide.shapes.add_picture(
            temp_path,
            Inches(left),
            Inches(top),
            Inches(new_width),
            Inches(new_height)
        )

        # Clean up temp file
        os.remove(temp_path)

        return True

    except Exception as e:
        print(f"    ❌ Failed to place card: {e}")
        return False

def create_presentation_from_template(template_file, images_dir, output_file, manifest_path=".claude/state/fetch_manifest.json"):
    """
    Create presentation using template pattern (FR-008, FR-015)
    """

    # Validate template exists
    if not os.path.exists(template_file):
        print(f"❌ Error: Template file not found: {template_file}")
        return False

    # Load manifest
    if not os.path.exists(manifest_path):
        print(f"❌ Error: Manifest not found: {manifest_path}")
        print(f"   Run /fetch-cards first to generate manifest")
        return False

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Get successful cards from manifest
    successful_cards = [
        card for card in manifest['cards']
        if card['status'] == 'success'
    ]

    total_cards = len(successful_cards)
    print(f"🎴 Found {total_cards} cards to place from manifest")

    if total_cards == 0:
        print("❌ No successful cards in manifest")
        return False

    # Load template
    print(f"📋 Loading template: {template_file}")
    template_prs = Presentation(template_file)

    if len(template_prs.slides) == 0:
        print("❌ Template has no slides")
        return False

    # Get slot positions from first slide
    template_slide = template_prs.slides[0]
    slot_positions = get_template_slot_positions(template_slide)

    print(f"📐 Found {len(slot_positions)} card slots in template")

    if len(slot_positions) == 0:
        print("❌ No card slots found in template")
        return False

    cards_per_slide = len(slot_positions)
    slides_needed = math.ceil(total_cards / cards_per_slide)

    print(f"📄 Creating {slides_needed} slides ({cards_per_slide} cards per slide)")

    # Create new presentation from template to preserve dimensions
    prs = Presentation(template_file)

    # Remove template slides, keep only the slide master/layouts
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[0]

    blank_layout = prs.slide_layouts[6]  # Blank layout from template

    # Process cards in groups (FR-008, FR-015)
    for slide_num in range(slides_needed):
        # Add new slide
        slide = prs.slides.add_slide(blank_layout)

        # Black background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0, 0, 0)

        # Calculate card indices for this slide
        start_idx = slide_num * cards_per_slide
        end_idx = min(start_idx + cards_per_slide, total_cards)

        print(f"\n📄 Slide {slide_num + 1}: Cards {start_idx + 1} to {end_idx}")

        # Place cards using template positions (FR-015: fill sequentially)
        for i, card_idx in enumerate(range(start_idx, end_idx)):
            if i >= len(slot_positions):
                break  # More cards than slots, will continue on next slide

            card_info = successful_cards[card_idx]
            card_path = card_info['path']
            card_name = card_info['name']
            slot = slot_positions[i]

            print(f"  [{i+1}] {card_name}")
            if place_card_in_slot(slide, card_path, slot):
                print(f"      ✅ Placed in slot")
            else:
                print(f"      ❌ Failed to place")

        # FR-015: Leave empty slots blank if cards exhausted
        remaining_slots = len(slot_positions) - (end_idx - start_idx)
        if remaining_slots > 0:
            print(f"  ℹ️  {remaining_slots} empty slots left blank")

    # Save presentation
    prs.save(output_file)
    print(f"\n💾 Saved presentation: {output_file}")
    print(f"📊 Stats: {total_cards} cards across {slides_needed} slides")

    return True

def main(template_file, images_dir, output_file):
    """Main skill execution"""

    print(f"🎴 Creating Presentation from Template")
    print("=" * 70)
    print(f"📋 Template: {template_file}")
    print(f"📁 Images: {images_dir}")
    print(f"💾 Output: {output_file}")
    print("=" * 70)

    # Validate images directory
    if not os.path.exists(images_dir):
        print(f"❌ Error: Images directory not found: {images_dir}")
        return 1

    success = create_presentation_from_template(
        template_file,
        images_dir,
        output_file
    )

    if success:
        print("\n" + "=" * 70)
        print(f"🎉 Presentation created successfully!")
        print(f"📁 File: {output_file}")
        print(f"🎴 Cards placed using template slot pattern!")
        return 0
    else:
        print("\n❌ Failed to create presentation")
        return 1

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: fill-template <template_file> <images_dir> <output_file>")
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
```

## Error Handling

**Common Errors**:
- `Template file not found`: Check template path is correct
- `Manifest not found`: Run `/fetch-cards` first
- `No successful cards in manifest`: All cards failed to download
- `No card slots found`: Template doesn't have valid card-sized shapes
- `Images directory not found`: Check images path

**Template Validation**:
- Template must have at least one slide
- Slide must contain rectangular shapes > 1" in size
- Shapes are detected automatically by size

## Slot Detection

Template slots are detected by:
1. Shape type: Rectangle (1) or Picture (13)
2. Size: Width and height both > 1.0 inches
3. Sorted: Top to bottom, left to right

**Orientation Handling** (FR-007):
- Horizontal slots (width > height): Cards may be rotated 90°
- Vertical slots (height > width): Cards placed normally
- Aspect ratio always preserved (FR-005)

## Requirements Satisfied

- **FR-005**: Preserves card aspect ratios when resizing
- **FR-006**: Supports template-based card positioning
- **FR-007**: Handles vertical/horizontal orientations
- **FR-008**: Distributes cards across multiple slides
- **FR-015**: Fills slots sequentially, creates slides as needed, leaves empties blank
