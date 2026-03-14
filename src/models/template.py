"""
Template metadata model for MTG card templates.

Represents metadata about a card template file, used for fuzzy matching
templates to cards based on color, type, and legendary status.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TemplateMetadata:
    """
    Metadata about an MTG card template.

    Attributes:
        color: Card color (blue, red, green, white, black, colorless, multicolor)
        card_type: Primary card type (Creature, Planeswalker, Artifact, Enchantment, etc.)
        legendary: Whether template is for legendary cards
        file_path: Absolute path to template image file
        sha256_hash: SHA-256 hash of template file (for VLM region caching)
    """
    color: str
    card_type: str
    legendary: bool
    file_path: str
    sha256_hash: str

    # Optional attributes for specialty templates
    multicolor_combination: Optional[str] = None  # e.g., "WU" for white-blue
    frame_style: Optional[str] = None  # e.g., "modern", "classic", "m15"

    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.color:
            raise ValueError("Template color is required")
        if not self.card_type:
            raise ValueError("Template card_type is required")
        if not self.file_path:
            raise ValueError("Template file_path is required")
        if not self.sha256_hash:
            raise ValueError("Template sha256_hash is required")

    def matches_card(self, card_color: str, card_type: str, card_legendary: bool) -> bool:
        """
        Check if this template matches the given card attributes.

        Args:
            card_color: Card's color
            card_type: Card's primary type
            card_legendary: Card's legendary status

        Returns:
            True if template matches card attributes (exact match or compatible)

        Examples:
            >>> template = TemplateMetadata("blue", "Creature", True, "/path", "hash123")
            >>> template.matches_card("blue", "Creature", True)
            True
            >>> template.matches_card("blue", "Creature", False)
            False  # legendary mismatch
            >>> template.matches_card("red", "Creature", True)
            False  # color mismatch
        """
        # Exact match required for all attributes
        return (
            self.color == card_color and
            self.card_type == card_type and
            self.legendary == card_legendary
        )

    def __repr__(self) -> str:
        """Human-readable representation for debugging."""
        legendary_str = "Legendary " if self.legendary else ""
        return f"TemplateMetadata({legendary_str}{self.color} {self.card_type})"
