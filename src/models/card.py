"""
Card data model for Hellcube proxy generator.

Represents a single MTG custom card with all attributes extracted from
the Hellcube spreadsheet.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Card:
    """
    Represents a Magic: The Gathering custom card.

    Attributes extracted from Hellcube AJ.xlsx spreadsheet using semantic
    parsing with dynamic adjacency detection.
    """

    # Required fields (FR-013: must be present for validation)
    name: str
    type: str  # Primary card type (Creature, Planeswalker, Artifact, etc.)

    # Inferred fields
    mana_cost: Optional[str] = None  # Parenthetical notation from name
    color: Optional[str] = None  # Inferred from mana symbols (Bu→blue, etc.)
    legendary: bool = False  # Detected from "Legendary" keyword in Types field

    # Parsed fields
    subtypes: List[str] = field(default_factory=list)  # From Types field after dash
    abilities: List[str] = field(default_factory=list)  # Combined from multiple "text" rows
    flavor: Optional[str] = None
    power_toughness: Optional[str] = None  # From Stats field (e.g., "2/4")
    author: Optional[str] = None

    # Custom artwork
    artwork_url: Optional[str] = None  # From "pic" field (FR-009: fail card if invalid)

    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.name:
            raise ValueError("Card name is required (FR-013)")
        if not self.type:
            raise ValueError("Card type is required (FR-013)")

    def __repr__(self) -> str:
        """Human-readable representation for debugging."""
        return f"Card(name={self.name!r}, type={self.type}, color={self.color})"
