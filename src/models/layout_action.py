"""Layout action model — a candidate placement for MCTS search."""

from dataclasses import dataclass
from src.models.card_element import CardElement
from src.models.bounding_box import BoundingBox


@dataclass
class LayoutAction:
    """A candidate action: place an element at a position with font/alignment.

    Args:
        element: The CardElement being placed
        target_bbox: Where to place it
        font_size: Font size in points
        alignment: Text alignment (left, center, right)
    """
    element: CardElement
    target_bbox: BoundingBox
    font_size: int = 14
    alignment: str = "left"

    def __hash__(self):
        return hash((self.element.type, self.target_bbox.x, self.target_bbox.y,
                      self.font_size, self.alignment))

    def __repr__(self):
        return (f"LayoutAction({self.element.type} -> "
                f"({self.target_bbox.x},{self.target_bbox.y}) "
                f"font={self.font_size} align={self.alignment})")
