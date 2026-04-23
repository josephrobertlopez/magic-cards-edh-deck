"""
Mana cost parser for parenthetical notation.

Parses MTG mana costs from card names like "Batman Blue (Bu,Bu)(1)" into
structured format: {blue: 2, generic: 1}.

Implements FR-002: Extract mana costs from parenthetical notation.
"""

import re
from typing import Dict


# Mana symbol mapping (FR-002: Bu→blue, Rd→red, etc.)
MANA_SYMBOLS = {
    "Bu": "blue",
    "Rd": "red",
    "Gn": "green",
    "Wt": "white",
    "Bk": "black",
    "Cl": "colorless",
}


def parse_mana_cost(card_name: str) -> Dict[str, int]:
    """
    Parse mana cost from parenthetical notation in card name.

    Args:
        card_name: Card name with mana cost like "Batman Blue (Bu,Bu)(1)"

    Returns:
        Dictionary mapping mana type to count:
        {"blue": 2, "generic": 1}

    Examples:
        >>> parse_mana_cost("Batman Blue (Bu,Bu)(1)")
        {'blue': 2, 'generic': 1}

        >>> parse_mana_cost("Fire Spell (Rd,Rd,Rd)")
        {'red': 3}

        >>> parse_mana_cost("Colorless Artifact (Cl)(2)")
        {'colorless': 1, 'generic': 2}
    """
    mana_counts: Dict[str, int] = {}

    # Find all parenthetical groups
    parenthetical_pattern = r"\(([^)]+)\)"
    matches = re.findall(parenthetical_pattern, card_name)

    for group in matches:
        # Check if it's a numeric generic cost
        if group.isdigit():
            mana_counts["generic"] = mana_counts.get("generic", 0) + int(group)
            continue

        # Parse colored mana symbols (comma-separated)
        symbols = [s.strip() for s in group.split(",")]
        for symbol in symbols:
            if symbol in MANA_SYMBOLS:
                color = MANA_SYMBOLS[symbol]
                mana_counts[color] = mana_counts.get(color, 0) + 1

    return mana_counts


def extract_mana_cost_from_name(card_name: str) -> tuple[str, str]:
    """
    Extract card name and mana cost separately.

    Args:
        card_name: Full card name with mana cost like "Batman Blue (Bu,Bu)(1)"

    Returns:
        Tuple of (clean_name, mana_cost_string):
        ("Batman Blue", "(Bu,Bu)(1)")

    Examples:
        >>> extract_mana_cost_from_name("Batman Blue (Bu,Bu)(1)")
        ('Batman Blue', '(Bu,Bu)(1)')

        >>> extract_mana_cost_from_name("Nala (Gn,Wt)")
        ('Nala', '(Gn,Wt)')
    """
    # Find all parenthetical groups
    parenthetical_pattern = r"\(([^)]+)\)"
    matches = list(re.finditer(parenthetical_pattern, card_name))

    if not matches:
        return card_name.strip(), ""

    # Everything before first parenthesis is the name
    first_match = matches[0]
    clean_name = card_name[: first_match.start()].strip()

    # Everything from first parenthesis onward is the mana cost
    mana_cost = card_name[first_match.start() :].strip()

    return clean_name, mana_cost
