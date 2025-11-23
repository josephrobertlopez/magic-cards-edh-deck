"""
Fuzzy template matcher for MTG cards.

Matches cards to templates using fuzzy filename matching with tolerance
for naming variations (FR-008a).

Examples of matched patterns:
- "blue*creature*legend*.png"
- "legendary_blue_creature.png"
- "creature-blue-legendary.png"
- "Blue Creature (Legendary).png"
"""

import re
from typing import List, Optional
from src.models.card import Card
from src.models.template import TemplateMetadata


class TemplateMatcher:
    """
    Fuzzy matcher for finding templates that match card attributes.

    Uses flexible pattern matching to handle naming variations in template files.
    """

    def __init__(self, templates: List[TemplateMetadata]):
        """
        Initialize matcher with available templates.

        Args:
            templates: List of available template metadata
        """
        self.templates = templates

    def find_best_match(self, card: Card) -> Optional[TemplateMetadata]:
        """
        Find best matching template for a card.

        Args:
            card: Card object with color, type, legendary attributes

        Returns:
            Best matching TemplateMetadata, or None if no match found

        Matching priority:
        1. Exact match (color + type + legendary status)
        2. Fallback to non-legendary variant if legendary not available
        3. Fallback to generic type template (ignoring color)
        4. None if no matches at all

        Examples:
            >>> templates = [TemplateMetadata("blue", "Creature", True, "/path1", "hash1")]
            >>> matcher = TemplateMatcher(templates)
            >>> card = Card(name="Test", type="Creature", color="blue", legendary=True)
            >>> match = matcher.find_best_match(card)
            >>> match.color
            'blue'
        """
        # Priority 1: Exact match
        exact_matches = [
            t for t in self.templates
            if t.matches_card(card.color, card.type, card.legendary)
        ]
        if exact_matches:
            return exact_matches[0]

        # Priority 2: Fallback to non-legendary if legendary not available
        if card.legendary:
            non_legendary_matches = [
                t for t in self.templates
                if t.color == card.color and t.card_type == card.type and not t.legendary
            ]
            if non_legendary_matches:
                print(f"⚠️  No legendary template for {card.color} {card.type}, using non-legendary")
                return non_legendary_matches[0]

        # Priority 3: Fallback to generic type template (ignore color)
        type_matches = [
            t for t in self.templates
            if t.card_type == card.type and t.legendary == card.legendary
        ]
        if type_matches:
            print(f"⚠️  No {card.color} template for {card.type}, using generic {type_matches[0].color}")
            return type_matches[0]

        # Priority 4: No matches
        print(f"❌ No template found for {card.color} {card.type} (legendary={card.legendary})")
        return None

    def find_all_matches(self, card: Card) -> List[TemplateMetadata]:
        """
        Find all templates that could work for a card.

        Args:
            card: Card object

        Returns:
            List of all matching templates (exact + fallbacks)
        """
        matches = []

        # Exact matches
        exact = [
            t for t in self.templates
            if t.matches_card(card.color, card.type, card.legendary)
        ]
        matches.extend(exact)

        # Non-legendary fallbacks
        if card.legendary:
            non_legendary = [
                t for t in self.templates
                if t.color == card.color and t.card_type == card.type and not t.legendary
                and t not in matches
            ]
            matches.extend(non_legendary)

        # Type-only matches
        type_only = [
            t for t in self.templates
            if t.card_type == card.type and t not in matches
        ]
        matches.extend(type_only)

        return matches

    @staticmethod
    def normalize_filename(filename: str) -> str:
        """
        Normalize template filename for fuzzy matching.

        Args:
            filename: Template filename (with or without path)

        Returns:
            Normalized lowercase string with only alphanumeric characters

        Examples:
            >>> TemplateMatcher.normalize_filename("Blue Creature (Legendary).png")
            'bluecreaturelegendary'
            >>> TemplateMatcher.normalize_filename("legendary_blue_creature.png")
            'legendarybluecreature'
        """
        # Extract filename from path
        if "/" in filename:
            filename = filename.split("/")[-1]

        # Remove extension
        if "." in filename:
            filename = filename.rsplit(".", 1)[0]

        # Lowercase and remove non-alphanumeric
        normalized = re.sub(r'[^a-z0-9]', '', filename.lower())
        return normalized

    @staticmethod
    def extract_attributes_from_filename(filename: str) -> dict:
        """
        Extract card attributes from template filename using pattern matching.

        Args:
            filename: Template filename

        Returns:
            Dictionary with inferred attributes: {color, card_type, legendary}

        Examples:
            >>> TemplateMatcher.extract_attributes_from_filename("blue_creature_legendary.png")
            {'color': 'blue', 'card_type': 'Creature', 'legendary': True}
            >>> TemplateMatcher.extract_attributes_from_filename("red_planeswalker.png")
            {'color': 'red', 'card_type': 'Planeswalker', 'legendary': False}
        """
        normalized = filename.lower()
        attributes = {}

        # Detect color
        colors = ["blue", "red", "green", "white", "black", "colorless", "multicolor"]
        for color in colors:
            if color in normalized:
                attributes["color"] = color
                break

        # Detect card type
        types = ["creature", "planeswalker", "artifact", "enchantment", "instant", "sorcery", "land"]
        for card_type in types:
            if card_type in normalized:
                attributes["card_type"] = card_type.capitalize()
                break

        # Detect legendary status
        attributes["legendary"] = "legend" in normalized

        return attributes
