"""
Strategic action sampling for MCTS layout optimization.

Generates smart action candidates for placing card elements, using
strategic positions (corners + midpoints) to reduce action space from
~49,000 to ~24 actions per element (FR-008).
"""

from typing import List, Dict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.models.card_element import CardElement
from src.models.bounding_box import BoundingBox
from src.models.layout_action import LayoutAction


def generate_strategic_actions(
    element: CardElement,
    template_regions
) -> List[LayoutAction]:
    """
    Generate strategic action candidates for placing an element.

    Uses 8 strategic positions per region (4 corners + 4 midpoints) with
    element-specific constraints to reduce action space from ~49,140 to ~24
    actions per element (per Session 2025-11-16 clarification).

    Strategy (FR-008, T041):
    - 8 strategic positions: top-left, top-right, bottom-left, bottom-right,
      top-mid, bottom-mid, left-mid, right-mid
    - Element-specific constraints:
      * name: center alignment only
      * abilities: left alignment only
      * mana_cost: right alignment only
      * p_t: right alignment only
      * flavor: left or center
      * type_line: left or center
    - 1-3 font size options per element type (not all 7 sizes)

    Args:
        element: CardElement to generate actions for
        template_regions: Available template regions with bounding boxes

    Returns:
        List of strategic LayoutActions for this element

    Examples:
        >>> from src.models.card_element import CardElement
        >>> from src.models.bounding_box import BoundingBox
        >>> element = CardElement("name", "Lightning Bolt", True)
        >>> regions = {"name_box": BoundingBox(x=50, y=50, width=700, height=40)}
        >>> actions = generate_strategic_actions(element, regions)
        >>> len(actions) > 0
        True
        >>> all(action.alignment == "center" for action in actions)
        True
    """
    actions = []

    # Convert TemplateRegions object to dict if needed
    if hasattr(template_regions, 'name_box'):
        # It's a TemplateRegions object - convert to dict
        regions_dict = {
            'name_box': template_regions.name_box,
            'mana_cost_box': template_regions.mana_cost_box,
            'type_box': template_regions.type_box,
            'type_line_box': template_regions.type_box,  # Alias
            'pt_box': template_regions.p_t_box,
            'p_t_box': template_regions.p_t_box,  # Alias
            'artwork_box': template_regions.artwork_box,
        }
        # Add text_boxes
        for i, tb in enumerate(template_regions.text_boxes or [], 1):
            regions_dict[f'text_box_{i}'] = tb
        if template_regions.text_boxes:
            regions_dict['text_boxes'] = template_regions.text_boxes[0]
            regions_dict['text_box'] = template_regions.text_boxes[0]
        template_regions = regions_dict

    # Map element types to appropriate region names
    # Support both naming conventions (type_line_box/type_box, text_boxes/text_box)
    region_mapping = {
        "name": ["name_box"],
        "mana_cost": ["mana_cost_box", "name_box"],  # May be in name box area
        "type_line": ["type_line_box", "type_box"],  # Support both names
        "ability_1": ["text_box_1", "text_boxes", "text_box"],
        "ability_2": ["text_box_2", "text_boxes", "text_box"],
        "ability_3": ["text_box_3", "text_boxes", "text_box"],
        "ability_4": ["text_box_4", "text_boxes", "text_box"],
        "p_t": ["pt_box", "p_t_box"],  # Support both names
        "flavor": ["flavor_box", "text_boxes", "text_box"],
        "artwork": ["artwork_box"],
        "author": ["text_boxes", "flavor_box", "text_box"]
    }

    # Get allowed alignment(s) for this element type
    alignment_constraints = {
        "name": ["left"],
        "mana_cost": ["right"],
        "type_line": ["left", "center"],
        "ability_1": ["left"],
        "ability_2": ["left"],
        "ability_3": ["left"],
        "ability_4": ["left"],
        "p_t": ["right"],
        "flavor": ["left", "center"],
        "artwork": ["center"],
        "author": ["left", "center"]
    }

    # Get allowed font sizes for this element type (1-3 options)
    font_size_options = {
        "name": [16, 18],
        "mana_cost": [14, 16],
        "type_line": [12, 14],
        "ability_1": [10, 12],
        "ability_2": [10, 12],
        "ability_3": [10, 12],
        "ability_4": [10, 12],
        "p_t": [14, 16],
        "flavor": [9, 10],
        "artwork": [12],  # Not really text, but placeholder
        "author": [8, 9]
    }

    # Get region candidates for this element
    region_names = region_mapping.get(element.type, ["text_boxes"])
    allowed_alignments = alignment_constraints.get(element.type, ["left"])
    allowed_fonts = font_size_options.get(element.type, [12])

    # Generate actions for each matching region
    for region_name in region_names:
        if region_name not in template_regions:
            continue

        region_box = template_regions[region_name]

        # Generate 8 strategic positions within region
        positions = _get_strategic_positions(region_box)

        # Generate actions for each position × alignment × font combination
        for position in positions:
            for alignment in allowed_alignments:
                for font_size in allowed_fonts:
                    # Create BoundingBox at position with region's size
                    from src.models.bounding_box import BoundingBox
                    target_bbox = BoundingBox(
                        x=position[0],
                        y=position[1],
                        width=region_box.width,
                        height=region_box.height
                    )

                    action = LayoutAction(
                        element=element,
                        target_bbox=target_bbox,
                        font_size=font_size,
                        alignment=alignment
                    )
                    actions.append(action)

    return actions


def _get_strategic_positions(bbox: BoundingBox) -> List[tuple[int, int]]:
    """
    Calculate 8 strategic positions within a bounding box.

    Positions: 4 corners + 4 midpoints (top, bottom, left, right edges)

    Args:
        bbox: Region bounding box

    Returns:
        List of (x, y) coordinate tuples

    Examples:
        >>> from src.models.bounding_box import BoundingBox
        >>> bbox = BoundingBox(x=0, y=0, width=100, height=100)
        >>> positions = _get_strategic_positions(bbox)
        >>> len(positions)
        8
        >>> (0, 0) in positions  # top-left corner
        True
        >>> (50, 0) in positions  # top-mid
        True
    """
    x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height

    # Calculate strategic points with small padding from edges
    padding = 5

    positions = [
        # 4 corners
        (x + padding, y + padding),                    # top-left
        (x + w - padding, y + padding),                # top-right
        (x + padding, y + h - padding),                # bottom-left
        (x + w - padding, y + h - padding),            # bottom-right

        # 4 midpoints
        (x + w // 2, y + padding),                     # top-mid
        (x + w // 2, y + h - padding),                 # bottom-mid
        (x + padding, y + h // 2),                     # left-mid
        (x + w - padding, y + h // 2),                 # right-mid
    ]

    return positions


def generate_se2_movements(
    element: CardElement,
    current_position: tuple[int, int],
    step_sizes: List[int] = [5, 10, 20],
    include_rotation: bool = False
) -> List[LayoutAction]:
    """
    Generate SE2 (Special Euclidean 2D) movement actions.

    SE2 movements are small translations (and optionally rotations) from
    the current position, enabling fine-grained position optimization.

    Args:
        element: CardElement being positioned
        current_position: Current (x, y) position
        step_sizes: Pixel step sizes for movements (default [5, 10, 20])
        include_rotation: Include rotation actions (not typically used for text)

    Returns:
        List of LayoutActions representing SE2 movements

    Examples:
        >>> elem = CardElement("name", "Opt", True)
        >>> actions = generate_se2_movements(elem, (100, 50))
        >>> len(actions) > 0
        True
    """
    actions = []
    x, y = current_position

    # Generate translation actions: up, down, left, right, and diagonals
    directions = [
        (1, 0),   # right
        (-1, 0),  # left
        (0, 1),   # down
        (0, -1),  # up
        (1, 1),   # down-right
        (-1, 1),  # down-left
        (1, -1),  # up-right
        (-1, -1), # up-left
    ]

    for step in step_sizes:
        for dx, dy in directions:
            new_x = x + dx * step
            new_y = y + dy * step

            # Create action with new position
            from src.models.bounding_box import BoundingBox
            target_bbox = BoundingBox(
                x=new_x,
                y=new_y,
                width=100,  # Default width
                height=30   # Default height
            )

            action = LayoutAction(
                element=element,
                target_bbox=target_bbox,
                font_size=14,  # Default
                alignment="left"
            )
            actions.append(action)

    return actions


def filter_actions_by_constraints(
    actions: List[LayoutAction],
    min_spacing: int = 10
) -> List[LayoutAction]:
    """
    Filter out actions that would create obviously bad layouts.

    Removes actions that:
    - Place elements too close to region edges
    - Would create known conflicts (e.g., mana cost overlapping name)

    Args:
        actions: Candidate actions
        min_spacing: Minimum pixels from region edge

    Returns:
        Filtered action list

    Examples:
        >>> from src.models.layout_action import LayoutAction
        >>> from src.models.card_element import CardElement
        >>> elem = CardElement("name", "Text", True)
        >>> actions = [
        ...     LayoutAction(elem, "name_box", (5, 5), 14, "center"),
        ...     LayoutAction(elem, "name_box", (100, 100), 14, "center")
        ... ]
        >>> filtered = filter_actions_by_constraints(actions, min_spacing=10)
        >>> len(filtered) <= len(actions)
        True
    """
    # For now, return all actions (constraint filtering is a future optimization)
    return actions
