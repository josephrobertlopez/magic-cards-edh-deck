#!/usr/bin/env python3
"""
End-to-End Test: Generate ONE MTG Proxy Card
==============================================

Golden Path Execution:
1. Parse ONE card from Hellcube spreadsheet
2. Load blanked template (requires T060 preprocessing)
3. Skip artwork (MVP - optional)
4. Run MCTS text placement (10 rollouts for speed)
5. Render final proxy PNG

Usage:
    python test_one_proxy.py

Prerequisites:
    - Template preprocessing completed (python src/cli/preprocess_templates.py)
    - Hellcube AJ.xlsx in current directory
    - Ollama running with llava:7b model
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image, ImageDraw, ImageFont

# Import existing components
from src.parsers.hellcube_parser import HellcubeExcelParser
from src.parsers.color_inference import infer_color_from_mana_cost
from src.cache.blanked_template_cache import BlankedTemplateCacheRepository
from src.cache.template_cache import TemplateCacheManager
from src.models.card_element import CardElement
from src.models.layout_state import LayoutState
from src.mcts.mcts_algorithm import MCTSLayoutAlgorithm


def timestamp():
    """Generate timestamped log prefix."""
    return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"


def create_placeholder_artwork(width=400, height=300, color=(100, 149, 237)):
    """Create placeholder artwork image (cornflower blue rectangle)."""
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)

    # Add "ARTWORK" text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()

    text = "ARTWORK"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    position = ((width - text_width) // 2, (height - text_height) // 2)
    draw.text(position, text, fill=(255, 255, 255), font=font)

    return img


def main():
    print(f"\n{'='*70}")
    print(f"END-TO-END TEST: Generate ONE MTG Proxy Card")
    print(f"{'='*70}\n")

    # Step 1: Parse ONE card from Excel
    print(f"{timestamp()} Step 1: Parsing ONE card from Hellcube spreadsheet...")

    excel_path = Path("Hellcube AJ.xlsx")
    if not excel_path.exists():
        print(f"[ERROR] Hellcube AJ.xlsx not found!")
        print(f"[INFO] Please place Hellcube AJ.xlsx in current directory")
        return 1

    try:
        parser = HellcubeExcelParser()
        cards = parser.parse_excel(str(excel_path))

        if not cards:
            print(f"[ERROR] No cards parsed from spreadsheet!")
            return 1

        # Get first card
        card = cards[0]
        print(f"{timestamp()} ✅ Parsed card: {card.name}")
        print(f"  - Type: {card.type}")
        print(f"  - Mana Cost: {card.mana_cost}")
        print(f"  - Color: {card.color}")
        print(f"  - Abilities: {len(card.abilities)} ability(ies)")

    except Exception as e:
        print(f"[ERROR] Card parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 2: Load blanked template
    print(f"\n{timestamp()} Step 2: Loading blanked template...")

    blanked_cache = BlankedTemplateCacheRepository()
    template_cache = TemplateCacheManager()

    # Find matching template hash
    # For MVP, just use first available blanked template
    cache_stats = blanked_cache.get_cache_stats()

    if cache_stats['total_templates'] == 0:
        print(f"[ERROR] No blanked templates found in cache!")
        print(f"[INFO] Run preprocessing first:")
        print(f"       python src/cli/preprocess_templates.py --max-rollouts 10 --max-concurrent 1 --subset HASH")
        return 1

    # List available blanked templates
    cache_dir = Path(".cache/templates_blanked")
    blanked_files = list(cache_dir.glob("*_blank.png"))

    if not blanked_files:
        print(f"[ERROR] No blanked templates found!")
        return 1

    # Use first blanked template
    template_hash = blanked_files[0].stem.replace("_blank", "")
    print(f"{timestamp()} Using template hash: {template_hash[:16]}...")

    blanked_template = blanked_cache.get_blanked_template(template_hash)

    if blanked_template is None:
        print(f"[ERROR] Failed to load blanked template!")
        return 1

    print(f"{timestamp()} ✅ Loaded blanked template: {blanked_template.size}")

    # Step 3: Skip artwork (MVP)
    print(f"\n{timestamp()} Step 3: Creating placeholder artwork (MVP - skipping download)...")

    artwork = create_placeholder_artwork()
    print(f"{timestamp()} ✅ Created placeholder artwork: {artwork.size}")

    # Step 4: Composite artwork onto template center
    print(f"\n{timestamp()} Step 4: Compositing artwork onto template...")

    # Simple center composite (no VLM region detection for MVP)
    template_with_artwork = blanked_template.copy()

    # Calculate center position (rough approximation)
    template_width, template_height = template_with_artwork.size
    artwork_width, artwork_height = artwork.size

    # Center position with slight offset for MTG card layout
    x_offset = (template_width - artwork_width) // 2
    y_offset = int(template_height * 0.25)  # Upper-middle region

    template_with_artwork.paste(artwork, (x_offset, y_offset))
    print(f"{timestamp()} ✅ Artwork composited at ({x_offset}, {y_offset})")

    # Step 5: Create card elements for MCTS
    print(f"\n{timestamp()} Step 5: Preparing card elements for MCTS text placement...")

    elements = [
        CardElement(
            element_type="name",
            text_content=card.name,
            required=True
        ),
        CardElement(
            element_type="type_line",
            text_content=card.type,
            required=True
        ),
    ]

    # Add abilities
    for i, ability in enumerate(card.abilities):
        elements.append(CardElement(
            element_type=f"ability_{i+1}",
            text_content=ability,
            required=True
        ))

    print(f"{timestamp()} Created {len(elements)} card elements")

    # Step 6: Run MCTS text placement (simplified - skip for MVP, use heuristic)
    print(f"\n{timestamp()} Step 6: Applying heuristic text layout (MVP - skipping MCTS)...")

    # Heuristic layout positions (rough MTG card coordinates)
    heuristic_layout = {
        "name": {"x": 50, "y": 30, "font_size": 18, "width": 400},
        "type_line": {"x": 50, "y": 500, "font_size": 14, "width": 400},
        "ability_1": {"x": 50, "y": 540, "font_size": 12, "width": 400},
    }

    print(f"{timestamp()} ✅ Heuristic layout applied")

    # Step 7: Render text onto template
    print(f"\n{timestamp()} Step 7: Rendering text onto template...")

    final_image = template_with_artwork.copy()
    draw = ImageDraw.Draw(final_image)

    # Load font
    try:
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_type = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        font_name = font_type = font_text = ImageFont.load_default()

    # Render name
    if "name" in heuristic_layout:
        pos = heuristic_layout["name"]
        draw.text((pos["x"], pos["y"]), card.name, fill=(0, 0, 0), font=font_name)

    # Render type
    if "type_line" in heuristic_layout:
        pos = heuristic_layout["type_line"]
        draw.text((pos["x"], pos["y"]), card.type, fill=(0, 0, 0), font=font_type)

    # Render abilities
    for i, ability in enumerate(card.abilities):
        key = f"ability_{i+1}"
        if key in heuristic_layout:
            pos = heuristic_layout[key]
            # Wrap text if too long
            words = ability.split()
            lines = []
            current_line = []

            for word in words:
                current_line.append(word)
                test_line = " ".join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=font_text)
                if bbox[2] - bbox[0] > pos["width"]:
                    if len(current_line) > 1:
                        current_line.pop()
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        lines.append(test_line)
                        current_line = []

            if current_line:
                lines.append(" ".join(current_line))

            # Draw wrapped text
            y_offset = 0
            for line in lines:
                draw.text((pos["x"], pos["y"] + y_offset), line, fill=(0, 0, 0), font=font_text)
                y_offset += 16

    print(f"{timestamp()} ✅ Text rendered")

    # Step 8: Save final proxy
    print(f"\n{timestamp()} Step 8: Saving final proxy...")

    output_dir = Path("output/proxies") / card.color.lower()
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in card.name)
    safe_name = safe_name.replace(' ', '_')

    output_path = output_dir / f"{safe_name}.png"
    final_image.save(output_path, format="PNG", dpi=(300, 300))

    print(f"{timestamp()} ✅ Proxy saved to: {output_path}")

    # Final summary
    print(f"\n{'='*70}")
    print(f"SUCCESS! Proxy card generated:")
    print(f"  - Card: {card.name}")
    print(f"  - Type: {card.type}")
    print(f"  - Color: {card.color}")
    print(f"  - Output: {output_path}")
    print(f"  - Size: {final_image.size} @ 300 DPI")
    print(f"{'='*70}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
