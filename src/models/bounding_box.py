"""Bounding box model for card element positioning."""

from dataclasses import dataclass


@dataclass
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates.

    Attributes:
        x: Left edge x coordinate
        y: Top edge y coordinate
        width: Box width in pixels
        height: Box height in pixels
    """
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> tuple:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this box overlaps with another."""
        return not (self.right <= other.x or other.right <= self.x or
                    self.bottom <= other.y or other.bottom <= self.y)

    def overlap_area(self, other: 'BoundingBox') -> int:
        """Compute overlap area with another box."""
        if not self.overlaps(other):
            return 0
        x_overlap = max(0, min(self.right, other.right) - max(self.x, other.x))
        y_overlap = max(0, min(self.bottom, other.bottom) - max(self.y, other.y))
        return x_overlap * y_overlap

    def contains(self, x: int, y: int) -> bool:
        """Check if point (x, y) is inside this box."""
        return self.x <= x <= self.right and self.y <= y <= self.bottom
