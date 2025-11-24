#!/usr/bin/env python3
"""Test MCTS Template Extractor on Krang template."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PIL import Image
from inpainting.mcts_template_extractor import MCTSTemplateExtractor


def test_mcts_extractor():
    """Test MCTS Template Extractor POC."""

    # Load Krang template (original with text)
    template_path = Path(".cache/templates_blanked/18bfdd1da886ce2c59fd2c1e8db2bfa4c94253ef5b36e1a8f6c5c729f7f6999b_sequential_adversarial.png")

    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}")
        return

    template = Image.open(template_path)
    print(f"Loaded template: {template.size}")

    # Define 6 regions (VLM-detected, using approximate coordinates)
    regions = [
        {"id": "name_box", "x": 50, "y": 35, "width": 300, "height": 40},
        {"id": "mana_cost_box", "x": 680, "y": 35, "width": 60, "height": 60},
        {"id": "art_box", "x": 100, "y": 100, "width": 300, "height": 300},
        {"id": "type_box", "x": 50, "y": 510, "width": 400, "height": 35},
        {"id": "text_box", "x": 50, "y": 550, "width": 690, "height": 200},
        {"id": "pt_box", "x": 690, "y": 715, "width": 60, "height": 40},
    ]

    print(f"Regions: {len(regions)}")

    # Initialize MCTS Template Extractor
    print("\n" + "="*60)
    print("Hybrid MCTS Template Extractor POC")
    print("="*60)
    print(f"Configuration:")
    print(f"  Approach: MCTS color search + PIL destructive draw")
    print(f"  Colors: edge, neighbor, perturbed (3 per region)")
    print(f"  Simulations: 10 (or >0.6 score)")
    print(f"  Reward weights: 0.35 edges + 0.35 VLM + 0.15 frame + 0.15 gradient")
    print("="*60 + "\n")

    extractor = MCTSTemplateExtractor(
        num_simulations=10,
        exploration_constant=1.414,
        quality_threshold=0.6
    )

    # Run extraction
    result = extractor.extract(template, regions)

    # Save result
    output_path = Path(".cache/templates_blanked/mcts_extractor_result.png")
    result.save(output_path)
    print(f"\nSaved result to {output_path}")

    # Compare with original
    print("\nComparison:")
    print(f"  Original: {template_path.name}")
    print(f"  Result:   {output_path.name}")
    print("\nDone! ᕕ( ᐛ )ᕗ")
    print("\nNext: Compare visually and vs PIL baseline")


if __name__ == "__main__":
    test_mcts_extractor()
