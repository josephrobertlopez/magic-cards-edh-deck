"""PSD Template Extractor - Extract blank MTG frames from Proxyshop PSD templates"""

from pathlib import Path
from typing import Optional, Literal
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import Layer, Group

ColorCode = Literal["W", "U", "B", "R", "G", "WU", "UB", "BR", "RG", "GW",
                    "WB", "UR", "BG", "GU", "RW", "Gold", "Artifact", "Colourless", "Land"]

class PSDTemplateExtractor:
    """Extract blank MTG card frames from Proxyshop PSD templates."""

    # Layers to always include in output
    ALWAYS_ON = ["Art Frame", "Border Crop", "Shadows"]

    # Layers to enable based on card properties
    COLOR_LAYERS = ["Background", "Pinlines & Textbox"]

    def __init__(self, psd_path: Path):
        """Load PSD template."""
        self.psd_path = Path(psd_path)
        self.psd: Optional[PSDImage] = None

    def _load_psd(self) -> PSDImage:
        """Lazy load PSD (they're large)."""
        if self.psd is None:
            self.psd = PSDImage.open(self.psd_path)
        return self.psd

    def _find_layer(self, name: str, parent: Optional[Layer] = None) -> Optional[Layer]:
        """Find layer by name in PSD tree."""
        psd = self._load_psd()
        search_in = parent if parent else psd

        for layer in search_in:
            if layer.name == name:
                return layer
            if hasattr(layer, '__iter__'):
                found = self._find_layer(name, layer)
                if found:
                    return found
        return None

    def _set_layer_visibility(self, layer: Layer, visible: bool):
        """Set layer visibility (modifies in-place)."""
        layer.visible = visible

    def extract_blank_frame(
        self,
        color: ColorCode,
        legendary: bool = False,
        land: bool = False,
        has_pt: bool = False,  # Only True for creatures with power/toughness
        output_path: Optional[Path] = None,
        size: tuple[int, int] = (744, 1039)  # Standard MTG proxy size
    ) -> Image.Image:
        """
        Extract a blank frame for the specified color/type.

        Args:
            color: Color code (W, U, B, R, G, or multicolor like WU, BR)
            legendary: Include legendary crown
            land: Use land pinlines instead of normal
            has_pt: Include power/toughness box (only for creatures)
            output_path: Optional path to save PNG
            size: Output size (default standard proxy)

        Returns:
            PIL Image of the blank frame
        """
        psd = self._load_psd()

        # Start by hiding all layers
        for layer in psd.descendants():
            layer.visible = False

        # Enable always-on layers
        for name in self.ALWAYS_ON:
            layer = self._find_layer(name)
            if layer:
                layer.visible = True

        # Enable Border group
        border = self._find_layer("Border")
        if border:
            border.visible = True
            # Enable the color-specific border if exists
            color_border = self._find_layer(color, border)
            if color_border:
                color_border.visible = True

        # Enable color-specific layers in Background and Pinlines
        for group_name in self.COLOR_LAYERS:
            if land and group_name == "Pinlines & Textbox":
                group_name = "Land Pinlines & Textbox"
            group = self._find_layer(group_name)
            if group:
                group.visible = True
                color_layer = self._find_layer(color, group)
                if color_layer:
                    color_layer.visible = True

        # Enable Name & Title Boxes - only the specific color
        name_box = self._find_layer("Name & Title Boxes")
        if name_box:
            name_box.visible = True
            color_name_box = self._find_layer(color, name_box)
            if color_name_box:
                color_name_box.visible = True

        # Enable PT Box ONLY for creatures with power/toughness
        if has_pt:
            pt_box = self._find_layer("PT Box")
            if pt_box:
                pt_box.visible = True
                color_pt = self._find_layer(color, pt_box)
                if color_pt:
                    color_pt.visible = True

        # Enable Legendary Crown if needed
        if legendary:
            # Note: Skip "Hollow Crown Shadow" - has stroke effects that require scikit-image

            crown = self._find_layer("Legendary Crown")
            if crown:
                crown.visible = True
                # Enable the specific color crown
                for child in crown:
                    if child.name == color:
                        child.visible = True
                    else:
                        child.visible = False

        # Composite and resize
        composite = psd.composite()
        if composite.size != size:
            composite = composite.resize(size, Image.Resampling.LANCZOS)

        # Save if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            composite.save(output_path, "PNG")

        return composite

    def get_text_regions(self, color: ColorCode, legendary: bool = False) -> dict:
        """
        Get bounding boxes for text regions on the template.

        Returns normalized coordinates (0-1) for:
        - name_box: Card name area
        - mana_cost_box: Mana cost area
        - type_box: Type line area
        - text_box: Rules text area
        - pt_box: Power/toughness area
        - artwork_box: Artwork area
        """
        psd = self._load_psd()
        width, height = psd.width, psd.height

        # Standard MTG card proportions (from template analysis)
        regions = {
            "name_box": {
                "x": 0.07, "y": 0.035,
                "width": 0.70, "height": 0.045
            },
            "mana_cost_box": {
                "x": 0.77, "y": 0.035,
                "width": 0.18, "height": 0.045
            },
            "artwork_box": {
                "x": 0.055, "y": 0.085,
                "width": 0.89, "height": 0.465
            },
            "type_box": {
                "x": 0.07, "y": 0.52,
                "width": 0.75, "height": 0.035
            },
            "text_box": {
                "x": 0.09, "y": 0.565,
                "width": 0.82, "height": 0.36
            },
            "pt_box": {
                "x": 0.80, "y": 0.90,
                "width": 0.12, "height": 0.045
            }
        }

        # Adjust for legendary crown (shifts things down slightly)
        if legendary:
            regions["name_box"]["y"] += 0.015
            regions["mana_cost_box"]["y"] += 0.015

        return regions


def extract_frame_for_card(
    psd_path: Path,
    color: str,
    card_type: str,
    legendary: bool = False,
    output_path: Optional[Path] = None
) -> Image.Image:
    """
    Convenience function to extract a frame based on card properties.

    Args:
        psd_path: Path to normal.psd template
        color: Color string (e.g., "R", "UB", "Gold")
        card_type: Card type (e.g., "Creature", "Instant", "Land")
        legendary: Is the card legendary
        output_path: Where to save the PNG

    Returns:
        PIL Image of blank frame
    """
    extractor = PSDTemplateExtractor(psd_path)

    is_land = "land" in card_type.lower()

    return extractor.extract_blank_frame(
        color=color,
        legendary=legendary,
        land=is_land,
        output_path=output_path
    )


if __name__ == "__main__":
    # Test extraction
    import sys

    psd_path = Path("assets/frames/blank_templates/normal.psd")
    if not psd_path.exists():
        print(f"PSD not found: {psd_path}")
        sys.exit(1)

    extractor = PSDTemplateExtractor(psd_path)

    # Extract red legendary creature frame (for Krenko)
    output = Path("assets/frames/blank_templates/R_legendary_creature.png")
    frame = extractor.extract_blank_frame(
        color="R",
        legendary=True,
        output_path=output
    )
    print(f"Extracted: {output} ({frame.size})")

    # Get text regions
    regions = extractor.get_text_regions("R", legendary=True)
    print("\nText regions:")
    for name, box in regions.items():
        print(f"  {name}: ({box['x']:.2f}, {box['y']:.2f}) {box['width']:.2f}x{box['height']:.2f}")
