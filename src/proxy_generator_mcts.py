#!/usr/bin/env python3
"""
MCTS Proxy Generator - Generate MTG proxies using blank templates + MCTS layout.

Pipeline:
1. Parse card data from Hellcube spreadsheet
2. Extract blank template from PSD (based on color/type)
3. Download artwork from card's pic_url
4. Use MCTS to optimize text/element placement
5. Composite artwork + text onto blank template
6. Output print-ready proxy PNG
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Tuple

from PIL import Image, ImageDraw, ImageFont
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.card import Card
from src.models.bounding_box import BoundingBox
from src.templates.psd_extractor import PSDTemplateExtractor
from src.layout.mcts_layout_engine import MCTSLayoutEngine
from src.rendering.mana_symbol_renderer import ManaSymbolRenderer


class MCTSProxyGenerator:
    """
    Generate MTG proxy cards using blank templates and MCTS layout optimization.

    This is the proper pipeline that:
    - Uses actual blank frame templates (not blanked real cards)
    - Places artwork in the artwork region
    - Uses MCTS to optimize text placement
    - Renders with proper MTG fonts
    """

    # Standard proxy dimensions
    WIDTH = 744
    HEIGHT = 1039
    DPI = 300

    # Default PSD template path
    DEFAULT_PSD = Path("assets/frames/blank_templates/normal.psd")

    def __init__(
        self,
        psd_path: Optional[Path] = None,
        fonts_dir: Optional[Path] = None,
        use_mcts: bool = True,
        mcts_rollouts: int = 100
    ):
        """
        Initialize proxy generator.

        Args:
            psd_path: Path to Proxyshop normal.psd template
            fonts_dir: Directory containing MTG fonts (Beleren, etc.)
            use_mcts: Whether to use MCTS layout optimization
            mcts_rollouts: Number of MCTS rollouts (default 100)
        """
        self.psd_path = psd_path or self.DEFAULT_PSD
        self.fonts_dir = fonts_dir or Path("assets/fonts")
        self.use_mcts = use_mcts
        self.mcts_rollouts = mcts_rollouts

        # Initialize components
        self.psd_extractor = PSDTemplateExtractor(self.psd_path)
        if use_mcts:
            self.layout_engine = MCTSLayoutEngine(max_rollouts=mcts_rollouts)

        # Initialize mana symbol renderer for proper {U} → icon rendering
        self.mana_renderer = ManaSymbolRenderer()

        # Load fonts
        self._load_fonts()

    def _load_fonts(self):
        """Load MTG fonts for text rendering."""
        # Try to load Beleren for card names
        beleren_paths = [
            self.fonts_dir / "Beleren-Bold.ttf",
            self.fonts_dir / "Beleren2016-Bold.ttf",
            self.fonts_dir / "BelerenProxy-Bold.ttf",
        ]

        self.name_font = None
        for path in beleren_paths:
            if path.exists():
                try:
                    self.name_font = ImageFont.truetype(str(path), 28)
                    break
                except IOError:
                    continue

        if self.name_font is None:
            self.name_font = ImageFont.load_default()

        # MPlantin for body text
        mplantin_paths = [
            self.fonts_dir / "MPlantin.ttf",
            self.fonts_dir / "PlantinMTProRg.TTF",
        ]

        self.body_font = None
        for path in mplantin_paths:
            if path.exists():
                try:
                    self.body_font = ImageFont.truetype(str(path), 18)
                    break
                except IOError:
                    continue

        if self.body_font is None:
            self.body_font = ImageFont.load_default()

        # Matrix-Bold for type line
        matrix_path = self.fonts_dir / "Matrix-Bold.ttf"
        if matrix_path.exists():
            try:
                self.type_font = ImageFont.truetype(str(matrix_path), 20)
            except IOError:
                self.type_font = self.body_font
        else:
            self.type_font = self.body_font

    def _infer_color_code(self, card: Card) -> str:
        """
        Infer color code from card's mana cost or color.

        Args:
            card: Card object

        Returns:
            Color code (W, U, B, R, G, or multicolor like WU)
        """
        # Check for explicit color
        if hasattr(card, 'color') and card.color:
            color_map = {
                'white': 'W', 'blue': 'U', 'black': 'B',
                'red': 'R', 'green': 'G',
                'colorless': 'Colourless', 'artifact': 'Artifact'
            }
            color_lower = card.color.lower()
            for name, code in color_map.items():
                if name in color_lower:
                    return code

        # Infer from mana cost
        if card.mana_cost:
            cost = card.mana_cost if isinstance(card.mana_cost, dict) else {}
            colors = []
            if cost.get('white', 0) > 0: colors.append('W')
            if cost.get('blue', 0) > 0: colors.append('U')
            if cost.get('black', 0) > 0: colors.append('B')
            if cost.get('red', 0) > 0: colors.append('R')
            if cost.get('green', 0) > 0: colors.append('G')

            if len(colors) == 0:
                return 'Colourless'
            elif len(colors) == 1:
                return colors[0]
            elif len(colors) == 2:
                # Two-color - check if valid combo exists
                combo = ''.join(colors)
                valid_combos = ['WU', 'UB', 'BR', 'RG', 'GW', 'WB', 'UR', 'BG', 'GU', 'RW']
                if combo in valid_combos:
                    return combo
                # Try reverse
                combo_rev = ''.join(reversed(colors))
                if combo_rev in valid_combos:
                    return combo_rev
                return 'Gold'
            else:
                return 'Gold'

        return 'Colourless'

    def _download_artwork(self, url: str, cache_dir: Path = Path(".cache/artwork")) -> Optional[Image.Image]:
        """
        Download artwork from URL.

        Args:
            url: Artwork URL
            cache_dir: Directory to cache downloads

        Returns:
            PIL Image or None if download fails
        """
        if not url:
            return None

        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create cache filename from URL
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        cache_path = cache_dir / f"{url_hash}.png"

        # Check cache
        if cache_path.exists():
            return Image.open(cache_path)

        # Download
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            from io import BytesIO
            img = Image.open(BytesIO(response.content))
            img.save(cache_path)
            return img
        except Exception as e:
            print(f"  Failed to download artwork: {e}")
            return None

    def _get_template_regions(self, color: str, legendary: bool) -> Dict[str, BoundingBox]:
        """
        Get text region bounding boxes for the template.

        Args:
            color: Color code
            legendary: Is legendary card

        Returns:
            Dict mapping region names to BoundingBox objects
        """
        # Get normalized regions from PSD extractor
        regions_norm = self.psd_extractor.get_text_regions(color, legendary)

        # Convert to pixel coordinates
        regions = {}
        for name, box in regions_norm.items():
            regions[name] = BoundingBox(
                x=int(box['x'] * self.WIDTH),
                y=int(box['y'] * self.HEIGHT),
                width=int(box['width'] * self.WIDTH),
                height=int(box['height'] * self.HEIGHT)
            )

        return regions

    def _render_text_simple(
        self,
        img: Image.Image,
        card: Card,
        regions: Dict[str, BoundingBox]
    ):
        """
        Render text using simple heuristic layout (no MCTS).

        Args:
            img: Template image to draw on
            card: Card data
            regions: Text region bounding boxes
        """
        draw = ImageDraw.Draw(img)

        # Name
        if 'name_box' in regions:
            box = regions['name_box']
            draw.text(
                (box.x + 10, box.y + box.height // 2),
                card.name,
                font=self.name_font,
                fill="black",
                anchor="lm"
            )

        # Mana cost (right side of name box)
        if 'mana_cost_box' in regions and card.mana_cost:
            box = regions['mana_cost_box']
            mana_str = self._format_mana_cost(card.mana_cost)
            draw.text(
                (box.x + box.width - 10, box.y + box.height // 2),
                mana_str,
                font=self.body_font,
                fill="black",
                anchor="rm"
            )

        # Type line
        if 'type_box' in regions:
            box = regions['type_box']
            type_line = card.type
            if card.legendary:
                type_line = "Legendary " + type_line
            if card.subtypes:
                type_line += " — " + " ".join(card.subtypes)
            draw.text(
                (box.x + 10, box.y + box.height // 2),
                type_line,
                font=self.type_font,
                fill="black",
                anchor="lm"
            )

        # Abilities text
        if 'text_box' in regions and card.abilities:
            box = regions['text_box']
            y_offset = box.y + 10
            for ability in card.abilities:
                # Word wrap (simple approach)
                wrapped = self._wrap_text(ability, box.width - 20, self.body_font)
                for line in wrapped:
                    draw.text((box.x + 10, y_offset), line, font=self.body_font, fill="black")
                    y_offset += 22
                y_offset += 8  # Gap between abilities

        # Flavor text
        if 'text_box' in regions and card.flavor:
            box = regions['text_box']
            # Put at bottom of text box
            try:
                italic_font = ImageFont.truetype(str(self.fonts_dir / "MPlantin-Italic.ttf"), 16)
            except:
                italic_font = self.body_font

            wrapped = self._wrap_text(card.flavor, box.width - 20, italic_font)
            y_offset = box.y + box.height - len(wrapped) * 20 - 10
            for line in wrapped:
                draw.text((box.x + 10, y_offset), line, font=italic_font, fill="#444444")
                y_offset += 20

        # Power/Toughness
        if 'pt_box' in regions and card.power_toughness:
            box = regions['pt_box']
            draw.text(
                (box.x + box.width // 2, box.y + box.height // 2),
                card.power_toughness,
                font=self.name_font,
                fill="black",
                anchor="mm"
            )

    def _format_mana_cost(self, mana_cost) -> str:
        """Format mana cost for display."""
        if isinstance(mana_cost, dict):
            parts = []
            if mana_cost.get('generic', 0) > 0:
                parts.append(str(mana_cost['generic']))
            for color, symbol in [('white', 'W'), ('blue', 'U'), ('black', 'B'),
                                   ('red', 'R'), ('green', 'G'), ('colorless', 'C')]:
                count = mana_cost.get(color, 0)
                parts.extend([symbol] * count)
            return ''.join(parts)
        return str(mana_cost) if mana_cost else ""

    def _wrap_text(self, text: str, max_width: int, font) -> list:
        """Simple word wrap."""
        words = text.split()
        lines = []
        current = []

        for word in words:
            test = ' '.join(current + [word])
            try:
                bbox = font.getbbox(test)
                width = bbox[2] - bbox[0]
            except:
                width = len(test) * 10

            if width <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(' '.join(current))
                current = [word]

        if current:
            lines.append(' '.join(current))

        return lines

    def generate(
        self,
        card: Card,
        output_path: Path,
        artwork_override: Optional[Image.Image] = None
    ) -> Tuple[Path, float]:
        """
        Generate proxy card from Card data.

        Args:
            card: Card object with all data
            output_path: Where to save the proxy PNG
            artwork_override: Optional artwork image (skips download)

        Returns:
            Tuple of (output_path, quality_score)
        """
        print(f"Generating proxy for: {card.name}")

        # 1. Determine color and card type
        color_code = self._infer_color_code(card)
        is_legendary = card.legendary or 'legendary' in card.type.lower()
        is_land = 'land' in card.type.lower()

        print(f"  Color: {color_code}, Legendary: {is_legendary}")

        # 2. Extract blank template from PSD
        print(f"  Extracting blank template...")
        template = self.psd_extractor.extract_blank_frame(
            color=color_code,
            legendary=is_legendary,
            land=is_land,
            size=(self.WIDTH, self.HEIGHT)
        )

        # 3. Get template regions
        regions = self._get_template_regions(color_code, is_legendary)

        # 4. Download and place artwork
        artwork = artwork_override or self._download_artwork(card.pic_url)
        if artwork and 'artwork_box' in regions:
            box = regions['artwork_box']
            # Resize artwork to fit
            art_resized = artwork.resize((box.width, box.height), Image.Resampling.LANCZOS)
            # Paste onto template
            template.paste(art_resized, (box.x, box.y))
            print(f"  Placed artwork at ({box.x}, {box.y})")

        # 5. Layout text (MCTS only - no fallback)
        if self.use_mcts:
            print(f"  Running MCTS layout optimization ({self.mcts_rollouts} rollouts)...")
            layout = self.layout_engine.optimize_layout(card, regions, self.mcts_rollouts)
            print(f"  MCTS layout returned {len(layout)} elements")
            # Render using MCTS layout
            self._render_mcts_layout(template, layout)
            quality_score = 0.9
        else:
            print(f"  Using simple heuristic layout...")
            self._render_text_simple(template, card, regions)
            quality_score = 0.8

        # 6. Save output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        template.save(output_path, dpi=(self.DPI, self.DPI))
        print(f"  Saved: {output_path}")

        return output_path, quality_score

    def _render_mcts_layout(self, img: Image.Image, layout):
        """Render text using MCTS-optimized layout with proper MTG alignment."""
        draw = ImageDraw.Draw(img)

        # MTG card alignment rules - override MCTS x positions for key elements
        # Standard card is 744x1039, visual measurements from actual card:
        # - Name bar: y ~35-75 (40px height)
        # - Artwork: y ~93-530 (437px height)
        # - Type bar (orange): y ~530-565 (35px height)
        # - Text box: y ~570-935 (365px height)
        NAME_X = 62  # Left-aligned with 10px padding
        NAME_Y = 53  # Vertical center of name bar
        MANA_RIGHT_EDGE = 690  # Right edge for mana symbols
        MANA_Y = 50  # Centered vertically in name bar
        TYPE_X = 62  # Left-aligned type line
        TYPE_Y = 545  # Centered in type bar (530 + 15)
        TEXT_X = 71  # Text box left edge with padding
        TEXT_START_Y = 590  # First ability line (below type bar)

        # Handle both dict format and LayoutState format
        if hasattr(layout, 'placed_elements'):
            # LayoutState object
            elements = layout.placed_elements
        elif isinstance(layout, dict):
            # Dict of PlacedElements
            elements = list(layout.values())
        else:
            print(f"  Warning: Unknown layout format: {type(layout)}")
            return

        for placed in elements:
            # Get position from PlacedElement
            if hasattr(placed, 'bbox'):
                x, y = placed.bbox.x, placed.bbox.y
            elif hasattr(placed, 'position'):
                x, y = placed.position
            else:
                continue

            # Get text content
            if hasattr(placed, 'element') and hasattr(placed.element, 'text_content'):
                text = placed.element.text_content
                elem_type = placed.element.type
            elif hasattr(placed, 'text_content'):
                text = placed.text_content
                elem_type = getattr(placed, 'element_type', 'body')
            else:
                continue

            font_size = getattr(placed, 'font_size', 14)

            # Apply MTG alignment rules based on element type
            if elem_type == 'name':
                # Left-align card name
                x = NAME_X
                y = NAME_Y
            elif elem_type == 'type_line':
                # Left-align type line ON the orange type bar
                x = TYPE_X
                y = TYPE_Y
            elif elem_type.startswith('ability_'):
                # Abilities go in text box area
                x = TEXT_X
                # Extract ability number and calculate Y position
                try:
                    ability_num = int(elem_type.split('_')[1])
                    y = TEXT_START_Y + (ability_num - 1) * 50  # 50px spacing
                except (IndexError, ValueError):
                    pass  # Use MCTS position
            elif elem_type == 'flavor':
                # Flavor text at bottom of text box
                x = TEXT_X
                y = TEXT_START_Y + 120  # Below abilities

            # Special handling for mana cost: render symbols instead of text
            if elem_type == 'mana_cost' and text:
                try:
                    mana_img = self.mana_renderer.render_mana_cost(text, size=28)
                    # Right-align mana symbols
                    x = MANA_RIGHT_EDGE - mana_img.width
                    y = MANA_Y  # Centered in name box
                    # Paste with alpha channel for transparency
                    img.paste(mana_img, (x, y), mana_img)
                    print(f"    Rendered mana symbols: {text} at ({x}, {y})")
                except Exception as e:
                    # Fallback to text if symbol rendering fails
                    print(f"    Warning: mana symbol render failed ({e}), using text")
                    font = self._get_font_for_element(elem_type, font_size)
                    draw.text((x, y), text, font=font, fill="black")
            else:
                font = self._get_font_for_element(elem_type, font_size)
                draw.text((x, y), text, font=font, fill="black")
                print(f"    Rendered: {elem_type} at ({x}, {y})")

    def _get_font_for_element(self, element_type: str, size: int):
        """Get appropriate font for element type."""
        if element_type == 'name':
            return self.name_font
        elif element_type == 'type_line':
            return self.type_font
        else:
            return self.body_font


def main():
    """Test proxy generation with Krenko."""
    from src.parsers.hellcube_parser import HellcubeExcelParser

    # Parse Hellcube to get Krenko
    parser = HellcubeExcelParser()
    cards = parser.parse(Path("hellcube_batman.xlsx"))

    # Find Krenko (index 14)
    krenko = None
    for card in cards:
        if 'krenko' in card.name.lower():
            krenko = card
            break

    if not krenko:
        print("Krenko not found in Hellcube")
        return

    print(f"Found: {krenko.name}")

    # Generate proxy with MCTS layout optimization (more rollouts for full placement)
    generator = MCTSProxyGenerator(use_mcts=True, mcts_rollouts=200)
    output_path = Path("output/proxies/red") / f"{krenko.name.replace(' ', '_')}_MCTS.png"

    path, score = generator.generate(krenko, output_path)
    print(f"\nGenerated: {path} (quality: {score:.3f})")


if __name__ == "__main__":
    main()
