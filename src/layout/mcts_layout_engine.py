"""
MCTS Layout Engine — optimize card element placement using Monte Carlo Tree Search.

Perfected pipeline:
- Text-aware bounding boxes (height computed from font size + content length)
- MTG-canonical default positions for intelligent rollouts
- 6-factor reward: overlap, region fit, spacing, reading order, margin, text overflow
- Best-reward tracking (returns highest-scoring terminal state, not most-visited path)
- Proper integration with MCTSProxyGenerator (LayoutState.placed_elements is Dict[str, PlacedElement])
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.models.bounding_box import BoundingBox
from src.models.card import Card
from src.models.card_element import CardElement
from src.models.layout_action import LayoutAction
from src.mcts.actions import generate_strategic_actions


# ==============================================================================
# Text measurement (approximate, no PIL dependency at search time)
# ==============================================================================

# Average character widths by font size (px), measured from DejaVu/Beleren metrics
_CHAR_WIDTH_RATIO = 0.55  # avg char width ≈ 0.55 × font_size for proportional fonts
_LINE_HEIGHT_RATIO = 1.35  # line height ≈ 1.35 × font_size


def estimate_text_bbox(text: str, font_size: int, max_width: int) -> tuple:
    """Estimate (width, height) in pixels for rendered text.

    Handles word wrapping: if text exceeds max_width, computes multi-line height.
    Returns (actual_width, total_height).
    """
    char_w = font_size * _CHAR_WIDTH_RATIO
    line_h = int(font_size * _LINE_HEIGHT_RATIO)
    text_width = int(len(text) * char_w)

    if text_width <= max_width:
        return (text_width, line_h)

    # Word-wrap: estimate number of lines
    words = text.split()
    lines = 1
    current_line_w = 0
    max_line_w = 0

    for word in words:
        word_w = int(len(word) * char_w)
        space_w = int(char_w)

        if current_line_w + space_w + word_w > max_width and current_line_w > 0:
            max_line_w = max(max_line_w, current_line_w)
            lines += 1
            current_line_w = word_w
        else:
            current_line_w += (space_w if current_line_w > 0 else 0) + word_w

    max_line_w = max(max_line_w, current_line_w)
    return (min(max_line_w, max_width), lines * line_h)


# ==============================================================================
# Layout State
# ==============================================================================

@dataclass
class PlacedElement:
    """An element that has been placed on the template."""
    element: CardElement
    bbox: BoundingBox
    font_size: int
    alignment: str


@dataclass
class LayoutState:
    """Current state of layout during MCTS search."""
    placed_elements: Dict[str, PlacedElement] = field(default_factory=dict)
    remaining_elements: List[CardElement] = field(default_factory=list)

    def is_terminal(self) -> bool:
        return len(self.remaining_elements) == 0

    def clone(self) -> 'LayoutState':
        return LayoutState(
            placed_elements=dict(self.placed_elements),
            remaining_elements=list(self.remaining_elements),
        )


# ==============================================================================
# MCTS Node
# ==============================================================================

@dataclass
class LayoutNode:
    """MCTS tree node for layout optimization."""
    state: LayoutState
    parent: Optional['LayoutNode'] = None
    action: Optional[LayoutAction] = None
    children: List['LayoutNode'] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_actions: List[LayoutAction] = field(default_factory=list)

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    def best_child(self, c: float = 1.414) -> 'LayoutNode':
        """UCB1 selection."""
        best = None
        best_score = -float('inf')
        for child in self.children:
            if child.visits == 0:
                return child
            exploit = child.total_reward / child.visits
            explore = c * math.sqrt(math.log(self.visits) / child.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best = child
        return best


# ==============================================================================
# MTG Canonical Positions (744×1039 standard proxy)
# ==============================================================================

# Default positions derived from real MTG card measurements.
# Used for intelligent rollouts (much better than random).
_MTG_DEFAULTS = {
    'name':      {'x': 62,  'y': 43,  'font': 18, 'align': 'left',   'height': 30},
    'mana_cost': {'x': 580, 'y': 43,  'font': 16, 'align': 'right',  'height': 30},
    'type_line': {'x': 62,  'y': 548, 'font': 14, 'align': 'left',   'height': 28},
    'ability_1': {'x': 75,  'y': 590, 'font': 12, 'align': 'left',   'height': 60},
    'ability_2': {'x': 75,  'y': 660, 'font': 12, 'align': 'left',   'height': 60},
    'ability_3': {'x': 75,  'y': 730, 'font': 12, 'align': 'left',   'height': 60},
    'ability_4': {'x': 75,  'y': 800, 'font': 12, 'align': 'left',   'height': 60},
    'flavor':    {'x': 75,  'y': 870, 'font': 10, 'align': 'left',   'height': 50},
    'p_t':       {'x': 620, 'y': 950, 'font': 16, 'align': 'right',  'height': 30},
    'author':    {'x': 75,  'y': 960, 'font': 8,  'align': 'left',   'height': 16},
    'artwork':   {'x': 41,  'y': 88,  'font': 12, 'align': 'center', 'height': 483},
}

# Map element type → region name
_REGION_MAP = {
    'name': 'name_box',
    'mana_cost': 'mana_cost_box',
    'type_line': 'type_box',
    'ability_1': 'text_box',
    'ability_2': 'text_box',
    'ability_3': 'text_box',
    'ability_4': 'text_box',
    'flavor': 'text_box',
    'p_t': 'pt_box',
    'artwork': 'artwork_box',
    'author': 'text_box',
}


# ==============================================================================
# Reward Function (6-factor)
# ==============================================================================

class LayoutRewardFunction:
    """Score a layout on overlap, fit, spacing, reading order, margins, and text overflow."""

    def __init__(self, regions: Dict[str, BoundingBox], card_width: int = 744, card_height: int = 1039):
        self.regions = regions
        self.card_width = card_width
        self.card_height = card_height

    def evaluate(self, state: LayoutState) -> float:
        """Compute reward in [0, 1]. Higher is better."""
        if not state.placed_elements:
            return 0.0

        scores = {
            'overlap':  self._overlap_score(state),
            'fit':      self._region_fit_score(state),
            'spacing':  self._spacing_score(state),
            'order':    self._reading_order_score(state),
            'margin':   self._margin_score(state),
            'overflow': self._text_overflow_score(state),
        }

        weights = {
            'overlap':  0.25,
            'fit':      0.25,
            'spacing':  0.15,
            'order':    0.15,
            'margin':   0.10,
            'overflow': 0.10,
        }
        return sum(weights[k] * scores[k] for k in scores)

    def _overlap_score(self, state: LayoutState) -> float:
        """1.0 = no overlaps. Hard penalty for any overlap."""
        placed = list(state.placed_elements.values())
        if len(placed) < 2:
            return 1.0

        total_overlap = 0
        total_area = sum(p.bbox.area for p in placed) or 1
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                total_overlap += placed[i].bbox.overlap_area(placed[j].bbox)

        return max(0.0, 1.0 - (total_overlap / total_area) * 10)

    def _region_fit_score(self, state: LayoutState) -> float:
        """Score how well elements fit within their designated regions."""
        fits = 0
        total = len(state.placed_elements)
        if total == 0:
            return 1.0

        for elem_type, placed in state.placed_elements.items():
            region_name = _REGION_MAP.get(elem_type)
            if region_name and region_name in self.regions:
                region = self.regions[region_name]
                if (placed.bbox.x >= region.x and
                    placed.bbox.y >= region.y and
                    placed.bbox.right <= region.right and
                    placed.bbox.bottom <= region.bottom):
                    fits += 1
                else:
                    overlap = placed.bbox.overlap_area(region)
                    fits += overlap / max(placed.bbox.area, 1)

        return fits / total

    def _spacing_score(self, state: LayoutState) -> float:
        """Score vertical spacing consistency within same-region groups."""
        # Group elements by their target region
        text_elements = [(t, p) for t, p in state.placed_elements.items()
                         if _REGION_MAP.get(t) == 'text_box']
        if len(text_elements) < 2:
            return 1.0

        sorted_elems = sorted(text_elements, key=lambda tp: tp[1].bbox.y)
        gaps = []
        for i in range(1, len(sorted_elems)):
            gap = sorted_elems[i][1].bbox.y - sorted_elems[i-1][1].bbox.bottom
            gaps.append(gap)

        if not gaps:
            return 1.0

        mean_gap = sum(gaps) / len(gaps)
        # Penalize negative gaps (overlaps within text box)
        if any(g < 0 for g in gaps):
            return 0.2

        if mean_gap == 0:
            return 0.5

        variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
        cv = math.sqrt(variance) / abs(mean_gap) if mean_gap != 0 else 1.0
        return max(0.0, 1.0 - cv)

    def _reading_order_score(self, state: LayoutState) -> float:
        """Score whether elements follow top-to-bottom priority order."""
        placed = list(state.placed_elements.values())
        if len(placed) < 2:
            return 1.0

        sorted_by_priority = sorted(placed, key=lambda p: p.element.priority)
        in_order = 0
        total = len(sorted_by_priority) - 1

        for i in range(total):
            if sorted_by_priority[i].bbox.y <= sorted_by_priority[i+1].bbox.y:
                in_order += 1

        return in_order / total if total > 0 else 1.0

    def _margin_score(self, state: LayoutState) -> float:
        """Penalize elements too close to card edges. Min 20px margin."""
        min_margin = 20
        penalties = 0
        total = len(state.placed_elements)
        if total == 0:
            return 1.0

        for placed in state.placed_elements.values():
            if (placed.bbox.x < min_margin or
                placed.bbox.y < min_margin or
                placed.bbox.right > self.card_width - min_margin or
                placed.bbox.bottom > self.card_height - min_margin):
                penalties += 1

        return 1.0 - (penalties / total)

    def _text_overflow_score(self, state: LayoutState) -> float:
        """Penalize text that overflows its bounding box (estimated)."""
        overflows = 0
        total = 0

        for elem_type, placed in state.placed_elements.items():
            if elem_type in ('artwork',):
                continue
            total += 1
            text = placed.element.text_content
            est_w, est_h = estimate_text_bbox(text, placed.font_size, placed.bbox.width)
            if est_h > placed.bbox.height * 1.1:  # 10% tolerance
                overflows += 1

        if total == 0:
            return 1.0
        return 1.0 - (overflows / total)


# ==============================================================================
# MCTS Layout Engine
# ==============================================================================

class MCTSLayoutEngine:
    """MCTS-based layout optimizer for MTG proxy cards.

    Perfected features:
    - Text-aware bounding boxes (content-sized, not region-sized)
    - MTG-canonical defaults for intelligent rollouts
    - Best-reward tracking (returns highest-scored state)
    - 6-factor reward function
    """

    def __init__(self, max_rollouts: int = 100, exploration_constant: float = 1.414,
                 quality_threshold: float = 0.85):
        self.max_rollouts = max_rollouts
        self.exploration_constant = exploration_constant
        self.quality_threshold = quality_threshold

    def optimize_layout(self, card: Card, regions: Dict[str, BoundingBox],
                        rollouts: Optional[int] = None) -> LayoutState:
        """Run MCTS to find optimal element placement.

        Returns LayoutState with placed_elements: Dict[str, PlacedElement].
        The proxy generator iterates this dict to render each element.
        """
        rollouts = rollouts or self.max_rollouts
        reward_fn = LayoutRewardFunction(regions)

        elements = self._card_to_elements(card)
        initial_state = LayoutState(remaining_elements=elements)
        root = LayoutNode(state=initial_state)
        root.untried_actions = self._get_actions(initial_state, regions)

        # Track best terminal state by reward (not just most-visited path)
        best_reward = -1.0
        best_state = None

        for sim in range(rollouts):
            node = root

            # Selection
            while not node.state.is_terminal() and node.is_fully_expanded():
                child = node.best_child(self.exploration_constant)
                if child is None:
                    break
                node = child

            # Expansion
            if not node.state.is_terminal() and not node.is_fully_expanded():
                action = node.untried_actions.pop()
                new_state = self._apply_action(node.state, action, regions)
                child = LayoutNode(state=new_state, parent=node, action=action)
                child.untried_actions = self._get_actions(new_state, regions)
                node.children.append(child)
                node = child

            # Simulation (intelligent rollout using MTG defaults)
            final_state = self._rollout(node.state, regions)

            # Evaluation
            reward = reward_fn.evaluate(final_state)

            # Track best
            if reward > best_reward:
                best_reward = reward
                best_state = final_state

            # Backpropagation
            while node:
                node.visits += 1
                node.total_reward += reward
                node = node.parent

            # Early stopping (require minimum 10 simulations for diversity)
            avg = root.total_reward / root.visits if root.visits else 0
            if sim >= 10 and avg >= self.quality_threshold:
                print(f"  MCTS early stop at sim {sim+1}: avg={avg:.3f} best={best_reward:.3f}")
                break

            if (sim + 1) % 50 == 0:
                avg = root.total_reward / root.visits if root.visits else 0
                print(f"  MCTS sim {sim+1}/{rollouts}: avg={avg:.3f} best={best_reward:.3f}")

        # Return best state found across all simulations
        if best_state and best_state.is_terminal():
            print(f"  MCTS final: best_reward={best_reward:.3f}, "
                  f"{len(best_state.placed_elements)} elements placed")
            return best_state

        # Fallback: walk most-visited path + greedy complete
        fallback = self._best_terminal(root)
        if not fallback.is_terminal():
            fallback = self._rollout(fallback, regions)
        return fallback

    def _card_to_elements(self, card: Card) -> List[CardElement]:
        """Convert Card data to list of CardElements for MCTS."""
        elements = [
            CardElement("name", card.name, required=True),
        ]

        if card.mana_cost:
            elements.append(CardElement("mana_cost", str(card.mana_cost), required=True))

        type_line = card.type
        if card.legendary:
            type_line = "Legendary " + type_line
        if card.subtypes:
            type_line += " \u2014 " + " ".join(card.subtypes)
        elements.append(CardElement("type_line", type_line, required=True))

        for i, ability in enumerate(card.abilities[:4], 1):
            elements.append(CardElement(f"ability_{i}", ability, required=True))

        if card.flavor:
            elements.append(CardElement("flavor", card.flavor, required=False))

        if card.power_toughness:
            elements.append(CardElement("p_t", card.power_toughness, required=True))

        if card.author:
            elements.append(CardElement("author", card.author, required=False))

        elements.sort(key=lambda e: e.priority)
        return elements

    def _get_actions(self, state: LayoutState, regions: Dict[str, BoundingBox]) -> List[LayoutAction]:
        """Generate candidate actions for the next element to place."""
        if state.is_terminal():
            return []

        next_element = state.remaining_elements[0]
        actions = generate_strategic_actions(next_element, regions)

        # Fix target_bbox dimensions: size to text content, not full region
        for action in actions:
            region_name = _REGION_MAP.get(next_element.type, 'text_box')
            region = regions.get(region_name)
            if region:
                est_w, est_h = estimate_text_bbox(
                    next_element.text_content, action.font_size, region.width
                )
                # Keep action's x,y position but resize to content
                action.target_bbox = BoundingBox(
                    x=action.target_bbox.x,
                    y=action.target_bbox.y,
                    width=min(est_w, region.width),
                    height=max(est_h, int(action.font_size * _LINE_HEIGHT_RATIO)),
                )

        return actions

    def _apply_action(self, state: LayoutState, action: LayoutAction,
                      regions: Dict[str, BoundingBox]) -> LayoutState:
        """Apply a placement action, returning new state."""
        new_state = state.clone()
        placed = PlacedElement(
            element=action.element,
            bbox=action.target_bbox,
            font_size=action.font_size,
            alignment=action.alignment,
        )
        new_state.placed_elements[action.element.type] = placed
        new_state.remaining_elements = [e for e in new_state.remaining_elements
                                         if e.type != action.element.type]
        return new_state

    def _rollout(self, state: LayoutState, regions: Dict[str, BoundingBox]) -> LayoutState:
        """Intelligent rollout using MTG-canonical default positions.

        Instead of random placement, uses real card anatomy positions
        with small jitter for exploration diversity.
        """
        current = state.clone()

        # Track cumulative Y offset for abilities stacking in text_box
        ability_y_cursor = None

        for element in list(current.remaining_elements):
            defaults = _MTG_DEFAULTS.get(element.type, _MTG_DEFAULTS.get('ability_1'))
            region_name = _REGION_MAP.get(element.type, 'text_box')
            region = regions.get(region_name)

            # Base position from MTG defaults
            x = defaults['x']
            y = defaults['y']
            font_size = defaults['font']
            alignment = defaults['align']

            # Compute content-aware height
            max_w = region.width if region else 600
            est_w, est_h = estimate_text_bbox(element.text_content, font_size, max_w)

            # For abilities: stack sequentially in text_box using cursor
            if element.type.startswith('ability_') and region:
                if ability_y_cursor is None:
                    ability_y_cursor = region.y + 10  # Start near top of text_box
                y = ability_y_cursor
                ability_y_cursor = y + est_h + 8  # 8px gap between abilities
            elif element.type == 'flavor' and ability_y_cursor is not None:
                y = ability_y_cursor + 4
                ability_y_cursor = y + est_h + 4

            # Add small jitter for exploration (±5px)
            jitter_x = random.randint(-5, 5)
            jitter_y = random.randint(-5, 5)
            x = max(20, x + jitter_x)
            y = max(20, y + jitter_y)

            # Clamp to card bounds
            bbox = BoundingBox(
                x=x,
                y=y,
                width=min(est_w, max_w),
                height=max(est_h, int(font_size * _LINE_HEIGHT_RATIO)),
            )

            placed = PlacedElement(
                element=element, bbox=bbox,
                font_size=font_size, alignment=alignment,
            )
            current.placed_elements[element.type] = placed

        current.remaining_elements = []
        return current

    def _best_terminal(self, root: LayoutNode) -> LayoutState:
        """Walk down the most-visited path to find best terminal state."""
        node = root
        while node.children:
            node = max(node.children, key=lambda n: n.visits)
        return node.state
