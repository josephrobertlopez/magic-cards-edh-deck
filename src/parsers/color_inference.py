"""
Color inference from mana symbols.

Implements FR-002: Infer card color from mana cost symbols
(Bu→blue, Rd→red, mixed symbols→multicolor).
"""

from typing import Dict, Optional


def infer_color_from_mana(mana_counts: Dict[str, int]) -> str:
    """
    Infer card color from mana cost breakdown.

    Args:
        mana_counts: Dictionary of mana type to count
                    (e.g., {"blue": 2, "generic": 1})

    Returns:
        Color string: "blue", "red", "green", "white", "black",
                     "colorless", or "multicolor"

    Examples:
        >>> infer_color_from_mana({"blue": 2, "generic": 1})
        'blue'

        >>> infer_color_from_mana({"blue": 1, "red": 1})
        'multicolor'

        >>> infer_color_from_mana({"colorless": 2})
        'colorless'

        >>> infer_color_from_mana({"generic": 3})
        'colorless'

    Spec: FR-002 - Bu→blue, Rd→red, Gn→green, Wt→white, Bk→black,
                    Cl→colorless, mixed→multicolor
    """
    # Extract colored mana symbols (exclude generic and colorless)
    colored_symbols = {
        color: count
        for color, count in mana_counts.items()
        if color not in ("generic", "colorless")
    }

    # No colored mana = colorless
    if not colored_symbols:
        return "colorless"

    # Single color
    if len(colored_symbols) == 1:
        return list(colored_symbols.keys())[0]

    # Multiple colors = multicolor
    return "multicolor"


def get_color_abbreviation(color: str) -> Optional[str]:
    """
    Get two-letter abbreviation for color (for mana symbol rendering).

    Args:
        color: Full color name ("blue", "red", etc.)

    Returns:
        Two-letter abbreviation ("Bu", "Rd", etc.) or None if invalid

    Examples:
        >>> get_color_abbreviation("blue")
        'Bu'

        >>> get_color_abbreviation("red")
        'Rd'

        >>> get_color_abbreviation("multicolor")
        None
    """
    abbreviations = {
        "blue": "Bu",
        "red": "Rd",
        "green": "Gn",
        "white": "Wt",
        "black": "Bk",
        "colorless": "Cl",
    }
    return abbreviations.get(color)
