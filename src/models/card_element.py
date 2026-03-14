"""Card element model — a single text/visual element on an MTG card."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CardElement:
    """A single element to be placed on a card template.

    Args:
        type: Element type (name, mana_cost, type_line, ability_1..4, p_t, flavor, artwork, author)
        text_content: The text to render
        required: Whether this element must be placed (validation fails without it)
        priority: Layout priority (lower = placed first). Default by type.
    """
    type: str
    text_content: str
    required: bool = True
    priority: Optional[int] = None

    def __post_init__(self):
        if self.priority is None:
            # Default priority order matching MTG card top-to-bottom
            priority_map = {
                "name": 0,
                "mana_cost": 1,
                "artwork": 2,
                "type_line": 3,
                "ability_1": 4,
                "ability_2": 5,
                "ability_3": 6,
                "ability_4": 7,
                "flavor": 8,
                "p_t": 9,
                "author": 10,
            }
            self.priority = priority_map.get(self.type, 99)

    def __hash__(self):
        return hash((self.type, self.text_content))
