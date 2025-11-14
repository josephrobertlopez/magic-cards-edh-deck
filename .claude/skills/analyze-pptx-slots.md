# analyze-pptx-slots

Analyze PowerPoint template structure and extract card slot positions.

## Usage

```
/analyze-pptx-slots <template.pptx>
```

**Parameters**:
- `template.pptx`: PowerPoint template file to analyze (required)

**Output**:
- JSON report of detected slots with positions, dimensions, orientations
- Slot count and layout summary
- Validation warnings for template issues

**Examples**:
```
/analyze-pptx-slots template_2v6h_FIXED.pptx
/analyze-pptx-slots custom_template.pptx
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from pptx import Presentation

def analyze_template_slots(template_path):
    """
    Extract card slot positions from PowerPoint template.

    Args:
        template_path: Path to PPTX template file

    Returns:
        Dictionary with slot analysis results

    Raises:
        FileNotFoundError: Template not found
        ValueError: Template has no valid slides or slots
    """
    template_path = Path(template_path).resolve()

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    if not template_path.suffix.lower() in ['.pptx', '.ppt']:
        raise ValueError(f"Template must be PowerPoint file (.pptx or .ppt), got: {template_path.suffix}")

    # Load template
    prs = Presentation(str(template_path))

    if len(prs.slides) == 0:
        raise ValueError("Template has no slides")

    # Analyze first slide (template pattern)
    template_slide = prs.slides[0]

    # Extract slot positions
    card_slots = []

    for shape in template_slide.shapes:
        # Look for rectangles or auto-shapes ≥1.0" in size
        if (shape.shape_type in [1, 13] and  # Rectangle (1) or Auto Shape (13)
            shape.width.inches > 1.0 and
            shape.height.inches > 1.0):

            # Calculate aspect ratio and orientation
            aspect_ratio = shape.width.inches / shape.height.inches
            orientation = "horizontal" if aspect_ratio > 1.0 else "vertical"

            card_slots.append({
                'index': len(card_slots),
                'left': round(shape.left.inches, 2),
                'top': round(shape.top.inches, 2),
                'width': round(shape.width.inches, 2),
                'height': round(shape.height.inches, 2),
                'aspect_ratio': round(aspect_ratio, 2),
                'orientation': orientation
            })

    if len(card_slots) == 0:
        raise ValueError("No valid card slots found (need rectangles ≥1.0\" × 1.0\")")

    # Sort slots by position (top to bottom, left to right)
    card_slots.sort(key=lambda x: (x['top'], x['left']))

    # Update indices after sorting
    for i, slot in enumerate(card_slots):
        slot['index'] = i

    # Count orientations
    vertical_count = sum(1 for s in card_slots if s['orientation'] == 'vertical')
    horizontal_count = sum(1 for s in card_slots if s['orientation'] == 'horizontal')

    # Get presentation dimensions
    slide_width = prs.slide_width.inches
    slide_height = prs.slide_height.inches

    # Build analysis result
    analysis = {
        'template_path': str(template_path),
        'slide_dimensions': {
            'width_inches': round(slide_width, 1),
            'height_inches': round(slide_height, 1),
            'orientation': 'landscape' if slide_width > slide_height else 'portrait'
        },
        'slot_summary': {
            'total_slots': len(card_slots),
            'vertical_slots': vertical_count,
            'horizontal_slots': horizontal_count,
            'layout_description': f"{vertical_count}v+{horizontal_count}h"
        },
        'slots': card_slots
    }

    return analysis

def main(template_path):
    """Main skill execution"""
    try:
        print(f"🎴 Analyzing PowerPoint Template")
        print("=" * 70)
        print(f"📄 Template: {template_path}")
        print()

        analysis = analyze_template_slots(template_path)

        # Print summary
        print(f"📐 Slide Dimensions: {analysis['slide_dimensions']['width_inches']}\" × {analysis['slide_dimensions']['height_inches']}\"")
        print(f"📊 Layout: {analysis['slot_summary']['layout_description']} ({analysis['slot_summary']['total_slots']} total slots)")
        print()

        # Print slot details
        print("🎯 Detected Slots:")
        print()
        for slot in analysis['slots']:
            print(f"  Slot {slot['index']}:")
            print(f"    Position: ({slot['left']}\", {slot['top']}\")")
            print(f"    Size: {slot['width']}\" × {slot['height']}\"")
            print(f"    Orientation: {slot['orientation'].upper()}")
            print(f"    Aspect: {slot['aspect_ratio']}")
            print()

        # Save JSON report
        json_path = Path(template_path).with_suffix('.slots.json')
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"💾 Detailed report saved: {json_path}")
        print()
        print("✅ Analysis complete!")

        return 0

    except FileNotFoundError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except ValueError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze-pptx-slots <template.pptx>")
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
```

## Output Example

```
🎴 Analyzing PowerPoint Template
======================================================================
📄 Template: template_2v6h_FIXED.pptx

📐 Slide Dimensions: 11.0" × 8.5"
📊 Layout: 2v+6h (8 total slots)

🎯 Detected Slots:

  Slot 0:
    Position: (0.5", 0.75")
    Size: 2.5" × 3.5"
    Orientation: VERTICAL
    Aspect: 0.71

  Slot 1:
    Position: (0.5", 4.5")
    Size: 2.5" × 3.5"
    Orientation: VERTICAL
    Aspect: 0.71

  Slot 2:
    Position: (3.5", 0.5")
    Size: 3.5" × 2.5"
    Orientation: HORIZONTAL
    Aspect: 1.40

  [... 5 more horizontal slots ...]

💾 Detailed report saved: template_2v6h_FIXED.slots.json
✅ Analysis complete!
```

## JSON Output Schema

```json
{
  "template_path": "/path/to/template.pptx",
  "slide_dimensions": {
    "width_inches": 11.0,
    "height_inches": 8.5,
    "orientation": "landscape"
  },
  "slot_summary": {
    "total_slots": 8,
    "vertical_slots": 2,
    "horizontal_slots": 6,
    "layout_description": "2v+6h"
  },
  "slots": [
    {
      "index": 0,
      "left": 0.5,
      "top": 0.75,
      "width": 2.5,
      "height": 3.5,
      "aspect_ratio": 0.71,
      "orientation": "vertical"
    }
  ]
}
```

## Error Handling

**`Template not found`**:
```
❌ Error: Template not found: /path/to/template.pptx
```
**Solution**: Check file path is correct

**`Template has no slides`**:
```
❌ Error: Template has no slides
```
**Solution**: Ensure template PPTX has at least one slide

**`No valid card slots found`**:
```
❌ Error: No valid card slots found (need rectangles ≥1.0" × 1.0")
```
**Solution**: Add rectangular shapes to template, minimum 1" × 1" size

## Use Cases

**Template Validation**:
- Verify template has expected slot count before generation
- Check slot positions match design specifications
- Validate aspect ratios for portrait/landscape cards

**Debugging Failed Generation**:
- Identify why cards aren't placing correctly
- See actual detected slot positions vs expected
- Find overlapping or malformed slots

**Template Migration**:
- Document old template structure before creating new one
- Compare slot layouts between template versions
- Generate conversion mapping for layout changes

## Exit Codes

- `0`: Success
- `1`: Template not found, invalid, or has no slots
