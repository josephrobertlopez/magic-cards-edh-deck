#!/usr/bin/env python3
"""Debug: Visualize region rectangles to verify coordinates."""

from PIL import Image, ImageDraw
from pathlib import Path

# Load template
template_path = Path(".cache/templates_blanked/18bfdd1da886ce2c59fd2c1e8db2bfa4c94253ef5b36e1a8f6c5c729f7f6999b_sequential_adversarial.png")
template = Image.open(template_path)

# Test regions (same as MCTS test)
regions = [
    {"id": "name_box", "x": 50, "y": 35, "width": 300, "height": 40, "color": (255, 0, 0)},
    {"id": "mana_cost_box", "x": 680, "y": 35, "width": 60, "height": 60, "color": (0, 255, 0)},
    {"id": "art_box", "x": 100, "y": 100, "width": 300, "height": 300, "color": (0, 0, 255)},
    {"id": "type_box", "x": 50, "y": 510, "width": 400, "height": 35, "color": (255, 255, 0)},
    {"id": "text_box", "x": 50, "y": 550, "width": 690, "height": 200, "color": (255, 0, 255)},
    {"id": "pt_box", "x": 690, "y": 715, "width": 60, "height": 40, "color": (0, 255, 255)},
]

# Draw colored rectangles to show region positions
debug_img = template.copy()
draw = ImageDraw.Draw(debug_img, 'RGBA')

for region in regions:
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    color = region['color'] + (128,)  # Semi-transparent

    # Draw filled rectangle
    draw.rectangle(
        [(x, y), (x + w, y + h)],
        fill=color,
        outline=(255, 255, 255, 255),
        width=2
    )

# Save debug image
output = Path(".cache/templates_blanked/debug_regions.png")
debug_img.save(output)
print(f"Saved debug visualization to {output}")
print("\nRegion coverage:")
for r in regions:
    print(f"  {r['id']}: ({r['x']},{r['y']}) → ({r['x']+r['width']},{r['y']+r['height']})")
