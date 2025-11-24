#!/usr/bin/env python3
"""PIL Baseline Template Blanker - Simple, Fast, Effective."""

import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path


def sample_edge_color(image, region):
    """Sample average color from region edges."""
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    img_np = np.array(image)

    edge_colors = []

    # Sample top & bottom edges
    for i in range(min(10, w)):
        px = x + i * (w // min(10, w))
        if 0 <= px < img_np.shape[1]:
            if 0 <= y < img_np.shape[0]:
                edge_colors.append(img_np[y, px])
            if 0 <= y+h-1 < img_np.shape[0]:
                edge_colors.append(img_np[y+h-1, px])

    # Average
    if edge_colors:
        return tuple(np.mean(edge_colors, axis=0).astype(int).tolist())
    else:
        return (128, 128, 128)


def blank_template(template_path, regions, output_path):
    """Blank template using simple PIL rectangles."""

    # Load template
    template = Image.open(template_path)
    draw = ImageDraw.Draw(template)

    print(f"Blanking template: {template_path.name}")
    print(f"Regions to blank: {len(regions)}")

    # Blank each region
    for region in regions:
        x, y, w, h = region['x'], region['y'], region['width'], region['height']

        # Sample edge color
        color = sample_edge_color(template, region)

        # Draw filled rectangle (DESTRUCTIVE - overwrites text)
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            fill=color
        )

        print(f"  Blanked {region['id']}: color={color}")

    # Save result
    template.save(output_path)
    print(f"\nSaved blanked template to: {output_path}")
    return template


if __name__ == "__main__":
    # Krang template
    template_path = Path(".cache/templates_blanked/18bfdd1da886ce2c59fd2c1e8db2bfa4c94253ef5b36e1a8f6c5c729f7f6999b_sequential_adversarial.png")

    # Regions (VLM-detected approximate coordinates)
    regions = [
        {"id": "name_box", "x": 50, "y": 35, "width": 300, "height": 40},
        {"id": "mana_cost_box", "x": 680, "y": 35, "width": 60, "height": 60},
        {"id": "type_box", "x": 50, "y": 510, "width": 400, "height": 35},
        {"id": "text_box", "x": 50, "y": 550, "width": 690, "height": 200},
        {"id": "pt_box", "x": 690, "y": 715, "width": 60, "height": 40},
    ]

    # Output path
    output_path = Path(".cache/templates_blanked/pil_baseline_blanked.png")

    # Blank it
    result = blank_template(template_path, regions, output_path)

    print("\nDone! ᕕ( ᐛ )ᕗ")
    print(f"PIL baseline: Simple, fast, effective")
