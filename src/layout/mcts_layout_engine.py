"""
MCTS Layout Engine — optimize card element placement using Monte Carlo Tree Search.

Uses strategic action sampling (corners + midpoints) to reduce action space
from ~49K to ~24 actions per element, then searches for optimal placement
via UCB1 selection + random rollouts.

Reward function scores:
- Overlap penalty (elements shouldn't overlap)
- Region fit (elements should stay within their designated regions)
- Spacing quality (consistent spacing between elements)
- Reading order (top-to-bottom, left-to-right for MTG cards)
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from src.models.bounding_box import BoundingBox
from src.models.card import Card
from src.models.card_element import CardElement
from src.models.layout_action import LayoutAction
from src.mcts.actions import generate_strategic_actions


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
# Reward Function
# ==============================================================================

class LayoutRewardFunction:
    """Score a layout based on overlap, fit, spacing, and reading order."""

    def __init__(self, regions: Dict[str, BoundingBox]):
        self.regions = regions

    def evaluate(self, state: LayoutState) -> float:
        """Compute reward in [0, 1]."""
        if not state.placed_elements:
            return 0.0

        scores = {
            'overlap': self._overlap_score(state),
            'fit': self._region_fit_score(state),
            'spacing': self._spacing_score(state),
            'order': self._reading_order_score(state),
        }

        weights = {'overlap': 0.35, 'fit': 0.30, 'spacing': 0.20, 'order': 0.15}
        return sum(weights[k] * scores[k] for k in scores)

    def _overlap_score(self, state: LayoutState) -> float:
        """Penalize overlapping elements. 1.0 = no overlaps."""
        placed = list(state.placed_elements.values())
        if len(placed) < 2:
            return 1.0

        total_overlap = 0
        total_area = sum(p.bbox.area for p in placed)
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                total_overlap += placed[i].bbox.overlap_area(placed[j].bbox)

        if total_area == 0:
            return 1.0
        return max(0.0, 1.0 - (total_overlap / total_area) * 5)

    def _region_fit_score(self, state: LayoutState) -> float:
        """Score how well elements fit within their designated regions."""
        region_map = {
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
        }

        fits = 0
        total = len(state.placed_elements)
        if total == 0:
            return 1.0

        for elem_type, placed in state.placed_elements.items():
            region_name = region_map.get(elem_type)
            if region_name and region_name in self.regions:
                region = self.regions[region_name]
                # Check if placed bbox is within region
                if (placed.bbox.x >= region.x and
                    placed.bbox.y >= region.y and
                    placed.bbox.right <= region.right and
                    placed.bbox.bottom <= region.bottom):
                    fits += 1
                else:
                    # Partial credit for partial containment
                    overlap = placed.bbox.overlap_area(region)
                    fits += overlap / max(placed.bbox.area, 1)

        return fits / total

    def _spacing_score(self, state: LayoutState) -> float:
        """Score vertical spacing consistency. 1.0 = even spacing."""
        placed = sorted(state.placed_elements.values(), key=lambda p: p.bbox.y)
        if len(placed) < 2:
            return 1.0

        gaps = []
        for i in range(1, len(placed)):
            gap = placed[i].bbox.y - placed[i-1].bbox.bottom
            gaps.append(gap)

        if not gaps:
            return 1.0

        mean_gap = sum(gaps) / len(gaps)
        if mean_gap == 0:
            return 0.5

        variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
        cv = math.sqrt(variance) / abs(mean_gap) if mean_gap != 0 else 1.0
        return max(0.0, 1.0 - cv)

    def _reading_order_score(self, state: LayoutState) -> float:
        """Score whether elements follow top-to-bottom reading order."""
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


# ==============================================================================
# MCTS Layout Engine
# ==============================================================================

class MCTSLayoutEngine:
    """MCTS-based layout optimizer for MTG proxy cards.

    Args:
        max_rollouts: Number of MCTS simulations per element
        exploration_constant: UCB1 exploration parameter
        quality_threshold: Early stopping threshold
    """

    def __init__(self, max_rollouts: int = 100, exploration_constant: float = 1.414,
                 quality_threshold: float = 0.75):
        self.max_rollouts = max_rollouts
        self.exploration_constant = exploration_constant
        self.quality_threshold = quality_threshold

    def optimize_layout(self, card: Card, regions: Dict[str, BoundingBox],
                        rollouts: Optional[int] = None) -> LayoutState:
        """Run MCTS to find optimal element placement.

        Args:
            card: Card data
            regions: Template region bounding boxes
            rollouts: Override max_rollouts

        Returns:
            LayoutState with optimized placements
        """
        rollouts = rollouts or self.max_rollouts
        reward_fn = LayoutRewardFunction(regions)

        # Build elements from card data
        elements = self._card_to_elements(card)

        # Initialize state
        initial_state = LayoutState(remaining_elements=elements)
        root = LayoutNode(state=initial_state)
        root.untried_actions = self._get_actions(initial_state, regions)

        # MCTS search
        for sim in range(rollouts):
            node = root

            # Selection — walk down tree via UCB1
            while not node.state.is_terminal() and node.is_fully_expanded():
                node = node.best_child(self.exploration_constant)

            # Expansion — try an untried action
            if not node.state.is_terminal() and not node.is_fully_expanded():
                action = node.untried_actions.pop()
                new_state = self._apply_action(node.state, action)
                child = LayoutNode(state=new_state, parent=node, action=action)
                child.untried_actions = self._get_actions(new_state, regions)
                node.children.append(child)
                node = child

            # Simulation — random rollout to terminal state
            final_state = self._rollout(node.state, regions)

            # Evaluation
            reward = reward_fn.evaluate(final_state)

            # Backpropagation
            while node:
                node.visits += 1
                node.total_reward += reward
                node = node.parent

            # Early stopping
            avg = root.total_reward / root.visits if root.visits else 0
            if avg > self.quality_threshold:
                print(f"  MCTS early stop at sim {sim+1}: avg_reward={avg:.3f}")
                break

            if (sim + 1) % 50 == 0:
                print(f"  MCTS sim {sim+1}/{rollouts}: avg_reward={avg:.3f}")

        # Extract best path
        return self._best_terminal(root)

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
            type_line += " — " + " ".join(card.subtypes)
        elements.append(CardElement("type_line", type_line, required=True))

        for i, ability in enumerate(card.abilities[:4], 1):
            elements.append(CardElement(f"ability_{i}", ability, required=True))

        if card.flavor:
            elements.append(CardElement("flavor", card.flavor, required=False))

        if card.power_toughness:
            elements.append(CardElement("p_t", card.power_toughness, required=True))

        if card.author:
            elements.append(CardElement("author", card.author, required=False))

        # Sort by priority
        elements.sort(key=lambda e: e.priority)
        return elements

    def _get_actions(self, state: LayoutState, regions: Dict[str, BoundingBox]) -> List[LayoutAction]:
        """Generate candidate actions for the next element to place."""
        if state.is_terminal():
            return []

        next_element = state.remaining_elements[0]

        # Build TemplateRegions-compatible dict from regions
        # generate_strategic_actions expects objects with .x, .y, .width, .height
        return generate_strategic_actions(next_element, regions)

    def _apply_action(self, state: LayoutState, action: LayoutAction) -> LayoutState:
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
        """Random rollout: place remaining elements in default positions."""
        current = state.clone()

        for element in list(current.remaining_elements):
            # Pick a default position within the appropriate region
            region_map = {
                'name': 'name_box', 'mana_cost': 'mana_cost_box',
                'type_line': 'type_box', 'p_t': 'pt_box',
                'artwork': 'artwork_box',
            }
            # Abilities and flavor go in text_box
            region_name = region_map.get(element.type, 'text_box')
            region = regions.get(region_name)

            if region:
                # Random position within region
                x = region.x + random.randint(0, max(0, region.width // 4))
                y = region.y + random.randint(0, max(0, region.height // 4))
                bbox = BoundingBox(x=x, y=y, width=region.width, height=30)
            else:
                # Fallback
                bbox = BoundingBox(x=50, y=50, width=200, height=30)

            placed = PlacedElement(element=element, bbox=bbox, font_size=12, alignment="left")
            current.placed_elements[element.type] = placed

        current.remaining_elements = []
        return current

    def _best_terminal(self, root: LayoutNode) -> LayoutState:
        """Walk down the most-visited path to find best terminal state."""
        node = root
        while node.children:
            node = max(node.children, key=lambda n: n.visits)

        # If not terminal, do a greedy rollout
        if not node.state.is_terminal():
            return node.state  # Return partial — caller handles remaining

        return node.state
