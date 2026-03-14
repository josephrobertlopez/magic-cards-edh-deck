# MCTS Implementation Specification
## Detailed Algorithm Design for MTG Card Layout Optimization

**Document**: 03-MCTS-Implementation-Spec.md
**Version**: 1.0.0
**Created**: 2025-11-15
**Related**: [02-Monorepo-Code-Structure.md](./02-Monorepo-Code-Structure.md)

---

## Table of Contents

1. [Algorithm Overview](#algorithm-overview)
2. [Data Structures](#data-structures)
3. [MCTS Core Operations](#mcts-core-operations)
4. [VLM Integration](#vlm-integration)
5. [Complete Implementation](#complete-implementation)
6. [Configuration & Tuning](#configuration--tuning)
7. [Examples](#examples)

---

## Algorithm Overview

**Name**: MCTSLayoutAlgorithm
**Inherits From**: `BaseAlgorithm` (from monorepo)
**Strategy**: Internal search (SUPPORTS_ITERATION = False)
**Backend**: Ollama VLM for layout quality scoring

### Algorithm Flow

```
Input: card_data + template_regions
  ↓
Initialize root node (empty layout)
  ↓
FOR rollout_num in range(max_rollouts):
  ├─ SELECT: Traverse tree using UCB1
  ├─ EXPAND: Add new child for unexplored action
  ├─ SIMULATE: Random completion + VLM evaluation
  └─ BACKPROPAGATE: Update ancestor statistics
  ↓
  Check convergence (10 consecutive stable scores)
  ↓
Extract best child (highest average reward)
  ↓
Reconstruct optimal layout path
  ↓
Output: layout + quality_score + rollouts_completed
```

### Convergence Criteria

**Early termination** when:
1. **Convergence threshold**: Best score stable within 0.01 for 10 consecutive rollouts
2. **Rollout budget exhausted**: `max_steps × 100` rollouts completed
3. **Perfect score**: Quality score reaches 1.0

**Typical behavior**:
- Simple cards (1 ability): Converge in 20-30 rollouts
- Complex cards (3 abilities): Converge in 60-80 rollouts
- Edge cases: Use full 100 rollout budget

---

## Data Structures

### LayoutState

**Represents a partial card layout during MCTS search.**

```python
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

@dataclass
class BoundingBox:
    """Rectangle region in pixels"""
    x: int              # Top-left X coordinate
    y: int              # Top-left Y coordinate
    width: int          # Box width in pixels
    height: int         # Box height in pixels

    def contains_point(self, px: int, py: int) -> bool:
        """Check if point (px, py) is inside box"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this box overlaps with another"""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)

@dataclass
class PlacedElement:
    """Represents a card element that has been positioned"""
    element_type: str          # 'name', 'mana_cost', 'type_line', 'ability_1', 'p_t', 'flavor'
    text_content: str          # Actual text to render
    position: Tuple[int, int]  # (x, y) top-left corner
    size: Tuple[int, int]      # (width, height) in pixels
    font_size: int             # Font size in points (8-20)
    alignment: str             # 'left', 'center', 'right'

    def get_bounding_box(self) -> BoundingBox:
        """Get bounding box for overlap checking"""
        x, y = self.position
        width, height = self.size
        return BoundingBox(x, y, width, height)

@dataclass
class CardElement:
    """Card element waiting to be placed"""
    element_type: str          # Type identifier
    text_content: str          # Text to render
    required: bool = True      # Must be placed (False for optional flavor)

@dataclass
class LayoutState:
    """Represents a partial card layout during MCTS search"""
    placed_elements: List[PlacedElement] = field(default_factory=list)
    remaining_elements: List[CardElement] = field(default_factory=list)
    template_regions: Dict[str, BoundingBox] = field(default_factory=dict)
    quality_score: Optional[float] = None  # Cached evaluation (None = not yet evaluated)

    def is_terminal(self) -> bool:
        """Check if all elements have been placed"""
        return len(self.remaining_elements) == 0

    def has_overlap(self) -> bool:
        """Check if any placed elements overlap"""
        for i, elem1 in enumerate(self.placed_elements):
            box1 = elem1.get_bounding_box()
            for elem2 in self.placed_elements[i+1:]:
                box2 = elem2.get_bounding_box()
                if box1.overlaps(box2):
                    return True
        return False

    def copy(self) -> 'LayoutState':
        """Create deep copy for simulation"""
        return LayoutState(
            placed_elements=list(self.placed_elements),
            remaining_elements=list(self.remaining_elements),
            template_regions=dict(self.template_regions),
            quality_score=self.quality_score
        )
```

### LayoutAction

**Represents a positioning decision for one element.**

```python
@dataclass
class LayoutAction:
    """Represents a positioning decision for one element"""
    element: CardElement          # Element to place
    region: str                   # Which template region to use
    position: Tuple[int, int]     # (x, y) within region
    font_size: int                # Font size (8-20pt)
    alignment: str                # 'left', 'center', 'right'

    def apply_to_state(self, state: LayoutState) -> LayoutState:
        """Apply this action to a state, returning new state"""
        new_state = state.copy()

        # Remove element from remaining
        new_state.remaining_elements = [
            e for e in state.remaining_elements
            if e.element_type != self.element.element_type
        ]

        # Calculate actual text size based on content and font
        text_width = estimate_text_width(self.element.text_content, self.font_size)
        text_height = estimate_text_height(self.element.text_content, self.font_size)

        # Create placed element
        placed = PlacedElement(
            element_type=self.element.element_type,
            text_content=self.element.text_content,
            position=self.position,
            size=(text_width, text_height),
            font_size=self.font_size,
            alignment=self.alignment
        )

        new_state.placed_elements.append(placed)
        return new_state
```

### MCTSNode

**Tree node storing partial layout state and visit statistics.**

```python
@dataclass
class MCTSNode:
    """MCTS tree node"""
    state: LayoutState                      # Partial layout
    parent: Optional['MCTSNode'] = None     # Parent node (None for root)
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0                         # Number of times visited
    total_reward: float = 0.0               # Sum of all rollout rewards through this node
    untried_actions: List[LayoutAction] = field(default_factory=list)

    def is_fully_expanded(self) -> bool:
        """Check if all actions have been tried"""
        return len(self.untried_actions) == 0

    def is_terminal(self) -> bool:
        """Check if this is a terminal state"""
        return self.state.is_terminal()

    def get_average_reward(self) -> float:
        """Get average reward (Q-value)"""
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def get_ucb1_score(self, exploration_constant: float = 1.414) -> float:
        """Calculate UCB1 score for selection

        UCB1 = Q(node) + C × sqrt(ln(N_parent) / N_node)
        """
        if self.visits == 0:
            return float('inf')  # Unvisited nodes have infinite priority

        exploitation = self.get_average_reward()
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration
```

---

## MCTS Core Operations

### 1. Selection Phase (UCB1 Tree Traversal)

**Goal**: Navigate from root to most promising unexpanded node.

**Algorithm**:
```
current_node = root
while current_node is not terminal AND current_node is fully expanded:
    current_node = child with highest UCB1 score
return current_node
```

**Implementation**:
```python
def _select(self, node: MCTSNode) -> MCTSNode:
    """Selection phase: UCB1 tree traversal

    Traverses tree from root, selecting children with highest UCB1 scores,
    until reaching a node that is either:
    - Terminal (all elements placed)
    - Not fully expanded (has untried actions)

    Returns:
        MCTSNode: Selected node for expansion/simulation
    """
    current = node

    while not current.is_terminal() and current.is_fully_expanded():
        # Select child with highest UCB1 score
        current = max(
            current.children,
            key=lambda child: child.get_ucb1_score(self.exploration_constant)
        )

    return current
```

**UCB1 Balancing**:
- **Early in search** (few visits): Exploration term dominates → tries diverse actions
- **Late in search** (many visits): Exploitation term dominates → refines best actions

**Example UCB1 calculation**:
```
Node A: 10 visits, 7.5 total reward, parent has 50 visits
Q(A) = 7.5 / 10 = 0.75
Exploration = 1.414 × sqrt(ln(50) / 10) = 1.414 × 0.622 = 0.880
UCB1(A) = 0.75 + 0.880 = 1.630

Node B: 30 visits, 24.0 total reward, parent has 50 visits
Q(B) = 24.0 / 30 = 0.800
Exploration = 1.414 × sqrt(ln(50) / 30) = 1.414 × 0.359 = 0.508
UCB1(B) = 0.800 + 0.508 = 1.308

Select Node A (higher UCB1, needs more exploration)
```

### 2. Expansion Phase (Add New Child)

**Goal**: Add one unexplored action as new child node.

**Algorithm**:
```
action = pop one untried action from node
new_state = apply action to node's state
create child node with new_state
add child to node's children
return child
```

**Implementation**:
```python
def _expand(self, node: MCTSNode) -> MCTSNode:
    """Expansion phase: Add new child for unexplored action

    Selects one untried action, applies it to create a new state,
    and adds the resulting node as a child.

    Args:
        node: Node to expand

    Returns:
        MCTSNode: Newly created child node
    """
    # Pop one untried action
    action = node.untried_actions.pop()

    # Apply action to create new state
    new_state = action.apply_to_state(node.state)

    # Create child node
    child = MCTSNode(
        state=new_state,
        parent=node,
        untried_actions=self._generate_actions(new_state)
    )

    # Add to parent's children
    node.children.append(child)

    return child
```

**Action Generation**:
```python
def _generate_actions(self, state: LayoutState) -> List[LayoutAction]:
    """Generate all possible actions for current state

    For next element to place, generates actions across:
    - All applicable template regions
    - Discrete position grid (10px steps)
    - Font size range (8-20pt)
    - Alignment options (left/center/right)

    Returns:
        List[LayoutAction]: All valid actions (typically 50-100 per element)
    """
    if state.is_terminal():
        return []

    next_element = state.remaining_elements[0]
    actions = []

    # Determine applicable regions for element type
    applicable_regions = self._get_applicable_regions(next_element.element_type)

    for region_name in applicable_regions:
        region = state.template_regions[region_name]

        # Discrete position grid (10px steps for speed)
        for x in range(region.x, region.x + region.width, 10):
            for y in range(region.y, region.y + region.height, 10):
                # Font sizes: 8, 10, 12, 14, 16, 18, 20
                for font_size in [8, 10, 12, 14, 16, 18, 20]:
                    # Alignment options
                    for alignment in ['left', 'center', 'right']:
                        action = LayoutAction(
                            element=next_element,
                            region=region_name,
                            position=(x, y),
                            font_size=font_size,
                            alignment=alignment
                        )
                        actions.append(action)

    return actions
```

**Pruning** (optional optimization):
- Filter out actions that would cause overlap with placed elements
- Filter out positions outside template region bounds
- Filter out font sizes too large for text content

### 3. Simulation Phase (Random Rollout + VLM Evaluation)

**Goal**: Complete partial layout randomly and evaluate quality with VLM.

**Algorithm**:
```
simulation_state = copy of node's state
while simulation_state has remaining elements:
    action = random choice from valid actions
    simulation_state = apply action to simulation_state
score = VLM evaluate simulation_state
return score
```

**Implementation**:
```python
def _simulate(self, node: MCTSNode, vlm_evaluator) -> float:
    """Simulation phase: Random rollout to terminal state + VLM scoring

    Completes the partial layout using random policy, then scores
    the completed layout with VLM for quality.

    Args:
        node: Node to simulate from
        vlm_evaluator: VLMLayoutEvaluator instance

    Returns:
        float: Quality score (0.0-1.0) from VLM
    """
    # Copy state for simulation
    simulation_state = node.state.copy()

    # Random rollout to completion
    while not simulation_state.is_terminal():
        actions = self._generate_actions(simulation_state)

        if not actions:
            # No valid actions (should not happen)
            return 0.0

        # Random policy
        action = random.choice(actions)
        simulation_state = action.apply_to_state(simulation_state)

    # VLM evaluation of completed layout
    quality_score = vlm_evaluator.score_layout(simulation_state)

    return quality_score
```

**Random Policy Trade-offs**:
- **Pros**: Fast (no evaluation per step), explores diverse completions
- **Cons**: May waste rollouts on poor random choices

**Heuristic-Guided Rollout** (optional enhancement):
```python
def _simulate_with_heuristic(self, node: MCTSNode, vlm_evaluator) -> float:
    """Simulation with heuristic bias toward good placements"""
    simulation_state = node.state.copy()

    while not simulation_state.is_terminal():
        actions = self._generate_actions(simulation_state)

        # Bias toward center alignment, larger fonts, standard positions
        weighted_actions = [
            (action, self._heuristic_weight(action))
            for action in actions
        ]

        action = random.choices(
            [a for a, _ in weighted_actions],
            weights=[w for _, w in weighted_actions]
        )[0]

        simulation_state = action.apply_to_state(simulation_state)

    return vlm_evaluator.score_layout(simulation_state)

def _heuristic_weight(self, action: LayoutAction) -> float:
    """Heuristic weight for biased rollout"""
    weight = 1.0

    # Prefer center alignment for name/type
    if action.element.element_type in ['name', 'type_line']:
        if action.alignment == 'center':
            weight *= 2.0

    # Prefer larger fonts (more readable)
    if action.font_size >= 12:
        weight *= 1.5

    # Prefer standard positions (top of region)
    region = self.template_regions[action.region]
    if action.position[1] <= region.y + 10:
        weight *= 1.3

    return weight
```

### 4. Backpropagation Phase (Update Statistics)

**Goal**: Propagate rollout reward up the tree to update node statistics.

**Algorithm**:
```
current_node = leaf_node
while current_node is not None:
    current_node.visits += 1
    current_node.total_reward += reward
    current_node = current_node.parent
```

**Implementation**:
```python
def _backpropagate(self, node: MCTSNode, reward: float):
    """Backpropagation phase: Update ancestor statistics

    Propagates the rollout reward from leaf node back to root,
    updating visit counts and total rewards.

    Args:
        node: Leaf node to backpropagate from
        reward: Quality score from VLM evaluation (0.0-1.0)
    """
    current = node

    while current is not None:
        current.visits += 1
        current.total_reward += reward
        current = current.parent
```

**Why this works**:
- Nodes on paths to high-quality layouts accumulate high total_reward
- Average reward (Q-value) increases for good partial placements
- UCB1 selection naturally gravitates toward these high-Q nodes
- Tree converges to optimal policy over multiple rollouts

---

## VLM Integration

### Template Region Detection

**VLMTemplateAnalyzer** - One-time template analysis

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class TemplateRegions(BaseModel):
    """VLM-detected template regions"""
    name_box: BoundingBox = Field(description="Card name region")
    mana_cost_box: BoundingBox = Field(description="Mana cost region (top-right)")
    type_line_box: BoundingBox = Field(description="Type line region")
    text_boxes: List[BoundingBox] = Field(description="1-3 ability text regions")
    pt_box: Optional[BoundingBox] = Field(None, description="Power/toughness box (creatures only)")
    flavor_box: Optional[BoundingBox] = Field(None, description="Flavor text region")

class VLMTemplateAnalyzer:
    """Uses Ollama VLM to detect template regions"""

    def __init__(self, percept_interface, instructor):
        self.percept_interface = percept_interface
        self.instructor = instructor

    def analyze_template(self, template_image_path: str) -> Dict[str, BoundingBox]:
        """Detect text box boundaries in MTG card template

        Args:
            template_image_path: Path to template PNG

        Returns:
            Dict mapping region names to BoundingBox objects
        """
        visual_data = {"image_path": template_image_path}

        # Process image with VLM
        self.percept_interface.process_with_vlm(visual_data)

        # Generate structured output
        prompt = f"""Analyze this MTG card template image and detect all text region bounding boxes.

Template dimensions: 750x1050 pixels (standard poker card at 300 DPI)

Identify these regions:
1. name_box: Card name at top (usually centered, ~30px tall)
2. mana_cost_box: Mana symbols top-right (~40px square)
3. type_line_box: Type line below name (~25px tall)
4. text_boxes: 1-3 ability text regions (variable height, largest regions)
5. pt_box: Power/toughness box (bottom-right corner, ~30px square) - only if creature template
6. flavor_box: Flavor text region (bottom of text area) - if present

For each region, provide bounding box as (x, y, width, height) in pixels.
x,y is top-left corner. Origin (0,0) is top-left of card.

Return ALL detected regions. Ensure text_boxes captures all ability regions."""

        regions_obj = self.instructor.generate_structured(
            prompt=prompt,
            response_model=TemplateRegions
        )

        # Convert to dict
        return {
            'name_box': regions_obj.name_box,
            'mana_cost_box': regions_obj.mana_cost_box,
            'type_line_box': regions_obj.type_line_box,
            'text_box_1': regions_obj.text_boxes[0] if len(regions_obj.text_boxes) > 0 else None,
            'text_box_2': regions_obj.text_boxes[1] if len(regions_obj.text_boxes) > 1 else None,
            'text_box_3': regions_obj.text_boxes[2] if len(regions_obj.text_boxes) > 2 else None,
            'pt_box': regions_obj.pt_box,
            'flavor_box': regions_obj.flavor_box
        }
```

### Layout Quality Evaluation

**VLMLayoutEvaluator** - Scores completed layouts

```python
class LayoutQuality(BaseModel):
    """VLM layout quality assessment"""
    readability_score: float = Field(ge=0.0, le=1.0, description="Text legibility and font sizing")
    convention_compliance: float = Field(ge=0.0, le=1.0, description="MTG layout conventions")
    aesthetic_balance: float = Field(ge=0.0, le=1.0, description="Visual harmony and spacing")
    overall_score: float = Field(ge=0.0, le=1.0, description="Weighted overall quality")
    issues: List[str] = Field(description="Specific problems identified")

class VLMLayoutEvaluator:
    """Uses Ollama VLM to score layout quality"""

    def __init__(self, instructor, percept_interface):
        self.instructor = instructor
        self.percept_interface = percept_interface

    def score_layout(self, state: LayoutState) -> float:
        """Evaluate layout quality (0.0-1.0)

        Renders layout preview and asks VLM to score on multiple criteria.

        Args:
            state: Completed LayoutState (all elements placed)

        Returns:
            float: Overall quality score (0.0-1.0)
        """
        # Render layout preview image
        preview_image_path = self._render_layout_preview(state)

        # Process with VLM
        visual_data = {"image_path": preview_image_path}
        self.percept_interface.process_with_vlm(visual_data)

        # Quality evaluation prompt
        prompt = f"""Evaluate this MTG card layout for quality.

Assess on three criteria:

1. **Readability** (0.0-1.0):
   - Text is legible at print size (2.5" × 3.5")
   - Font sizes appropriate for content
   - Adequate whitespace around text
   - No text overlap or cramming

2. **Convention Compliance** (0.0-1.0):
   - Card name centered at top
   - Mana cost in top-right
   - Type line below name
   - Abilities left-aligned in text boxes
   - Power/toughness in bottom-right (if creature)
   - Flavor text italicized at bottom (if present)

3. **Aesthetic Balance** (0.0-1.0):
   - Even spacing between elements
   - Visual hierarchy (name > abilities > flavor)
   - Elements aligned to template regions
   - No awkward gaps or crowding

Provide scores for each criterion and overall weighted score.
List any specific issues found.

Overall score formula: (readability × 0.5) + (convention × 0.3) + (aesthetic × 0.2)"""

        quality = self.instructor.generate_structured(
            prompt=prompt,
            response_model=LayoutQuality
        )

        return quality.overall_score

    def _render_layout_preview(self, state: LayoutState) -> str:
        """Render layout state to preview image

        Args:
            state: LayoutState with all elements placed

        Returns:
            str: Path to rendered preview PNG
        """
        from PIL import Image, ImageDraw, ImageFont

        # Create blank canvas (750x1050 white background)
        img = Image.new('RGB', (750, 1050), color='white')
        draw = ImageDraw.Draw(img)

        # Render each placed element
        for elem in state.placed_elements:
            x, y = elem.position
            font = ImageFont.truetype("Arial.ttf", elem.font_size)

            # Draw text
            draw.text(
                (x, y),
                elem.text_content,
                fill='black',
                font=font,
                align=elem.alignment
            )

            # Draw bounding box (for debugging)
            bbox = elem.get_bounding_box()
            draw.rectangle(
                [(bbox.x, bbox.y), (bbox.x + bbox.width, bbox.y + bbox.height)],
                outline='red',
                width=1
            )

        # Save preview
        preview_path = f"/tmp/layout_preview_{uuid.uuid4()}.png"
        img.save(preview_path)
        return preview_path
```

---

## Complete Implementation

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/algorithms/mcts/mcts_layout.py`

```python
#!/usr/bin/env python3.11
"""
MCTS Layout Optimization Algorithm - Following Reflexion Template
Optimizes MTG card element placement using Monte Carlo Tree Search

File: monorepo/agentic/algorithms/mcts/mcts_layout.py
"""

import json
import math
import random
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from ..base_algorithm import BaseAlgorithm

# Import data structures (defined above)
from .data_structures import (
    BoundingBox,
    PlacedElement,
    CardElement,
    LayoutState,
    LayoutAction,
    MCTSNode
)

# Import VLM integration
from .vlm_integration import (
    VLMTemplateAnalyzer,
    VLMLayoutEvaluator
)

class MCTSLayoutAlgorithm(BaseAlgorithm):
    """MCTS for card layout optimization - uniform interface

    Problem-solving strategy: Internal search (single episode)
    Each execution runs MCTS rollouts to convergence.

    Architecture:
    - Inherits from BaseAlgorithm (monorepo pattern)
    - Instructor-based VLM evaluation
    - Stateless execution (pure function)
    - Fallback heuristic for test mode

    Performance:
    - Target: <2s per card (100 rollouts)
    - Convergence: 10 consecutive stable scores
    - Quality: ≥0.8 score for 95%+ of cards
    """

    # Internal search strategy - completes in single episode
    SUPPORTS_ITERATION = False

    def __init__(self, name: str = "mcts_layout", **config):
        """Uniform constructor - uses unified parameter schema

        Args:
            name: Algorithm name
            **config: Configuration parameters
                - max_steps: Rollout multiplier (max_steps × 100 = total rollouts)
                - max_depth: Tree depth limit (7-8 for card layouts)
                - branching_factor: Action space size per state (~10-100)
                - domain: Problem domain ('mtg_layout')
                - instructor: Instructor instance (for VLM)
                - percept_interface: PerceptInterface instance (for VLM)
                - exploration_constant: UCB1 C parameter (default 1.414)
                - convergence_threshold: Score stability threshold (default 0.01)
        """
        super().__init__(name, **config)
        self.instructor = config.get('instructor')
        self.percept_interface = config.get('percept_interface')

        # MCTS-specific parameters (map from unified schema)
        self.max_rollouts = self.max_steps * 100  # max_steps × rollout multiplier
        self.exploration_constant = config.get('exploration_constant', 1.414)
        self.convergence_threshold = config.get('convergence_threshold', 0.01)

    def execute(self,
                problem: str,
                on_trial: Optional[Callable] = None,
                iteration_context: Optional[Dict] = None,
                **kwargs) -> Dict[str, Any]:
        """Execute MCTS layout optimization

        STATELESS PATTERN: Algorithm is pure function

        Args:
            problem: JSON-encoded card data and template info
            on_trial: Optional callback for rollout progress
                     Receives: {'rollout': int, 'best_score': float, 'timestamp': float}
                     Returns: True to continue, False to stop
            iteration_context: Optional provider state (ignored by MCTS - internal search)
            **kwargs: Algorithm-specific parameters
                - card_data: Parsed card object
                - template_regions: VLM-detected regions dict
                - vlm_evaluator: VLMLayoutEvaluator instance (optional)

        Returns:
            Dict with 'result' field containing:
                - success: bool
                - data: {'layout': LayoutState, 'quality_score': float, 'rollouts_completed': int}
                - metadata: {'algorithm': str, 'converged': bool, 'max_rollouts': int}
        """
        # Parse problem inputs
        problem_data = json.loads(problem)
        card_data = kwargs.get('card_data', problem_data.get('card_data'))
        template_regions = kwargs.get('template_regions', problem_data.get('template_regions'))

        # Fallback if no instructor/VLM
        if self.instructor is None or self.percept_interface is None:
            result = self._execute_fallback(card_data, template_regions)
        else:
            # Real MCTS with VLM evaluation
            try:
                vlm_evaluator = kwargs.get('vlm_evaluator')
                if vlm_evaluator is None:
                    vlm_evaluator = VLMLayoutEvaluator(self.instructor, self.percept_interface)

                # Initialize MCTS tree
                initial_state = LayoutState(
                    placed_elements=[],
                    remaining_elements=self._extract_card_elements(card_data),
                    template_regions=template_regions
                )
                root = MCTSNode(
                    state=initial_state,
                    untried_actions=self._generate_actions(initial_state)
                )

                # MCTS main loop
                best_score = 0.0
                convergence_count = 0

                for rollout_num in range(self.max_rollouts):
                    # Four phases: Selection → Expansion → Simulation → Backpropagation
                    node = self._select(root)

                    if not node.is_terminal():
                        node = self._expand(node)

                    reward = self._simulate(node, vlm_evaluator)
                    self._backpropagate(node, reward)

                    # Optional progress callback
                    if on_trial and root.children:
                        current_best = max(child.get_average_reward() for child in root.children)
                        trial_data = {
                            'rollout': rollout_num + 1,
                            'best_score': current_best,
                            'timestamp': time.time()
                        }
                        if not on_trial(trial_data):
                            break

                    # Convergence check
                    if root.children:
                        current_best = max(child.get_average_reward() for child in root.children)
                        if abs(current_best - best_score) < self.convergence_threshold:
                            convergence_count += 1
                            if convergence_count >= 10:  # 10 consecutive stable rollouts
                                break
                        else:
                            convergence_count = 0
                        best_score = current_best

                # Extract best layout
                if root.children:
                    best_child = max(root.children, key=lambda c: c.get_average_reward())
                    optimal_layout = self._reconstruct_path(best_child)
                else:
                    # Fallback if no children (should not happen)
                    optimal_layout = initial_state

                result = type('Result', (), {
                    'success': True,
                    'data': {
                        'layout': optimal_layout,
                        'quality_score': best_score,
                        'rollouts_completed': rollout_num + 1
                    },
                    'metadata': {
                        'algorithm': 'mcts_layout',
                        'converged': convergence_count >= 10,
                        'max_rollouts': self.max_rollouts
                    }
                })()

            except Exception as e:
                print(f"⚠️  MCTS failed: {e}, using fallback")
                result = self._execute_fallback(card_data, template_regions)

        # STATELESS PATTERN: Return structured response
        response = {'result': result}

        # iteration_context not used (internal search completes in single call)
        return response

    def _select(self, node: MCTSNode) -> MCTSNode:
        """Selection phase: UCB1 tree traversal"""
        current = node
        while not current.is_terminal() and current.is_fully_expanded():
            current = max(
                current.children,
                key=lambda child: child.get_ucb1_score(self.exploration_constant)
            )
        return current

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """Expansion phase: Add new child for unexplored action"""
        action = node.untried_actions.pop()
        new_state = action.apply_to_state(node.state)
        child = MCTSNode(
            state=new_state,
            parent=node,
            untried_actions=self._generate_actions(new_state)
        )
        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode, vlm_evaluator) -> float:
        """Simulation phase: Random rollout + VLM scoring"""
        simulation_state = node.state.copy()
        while not simulation_state.is_terminal():
            actions = self._generate_actions(simulation_state)
            if not actions:
                return 0.0  # No valid actions
            action = random.choice(actions)
            simulation_state = action.apply_to_state(simulation_state)

        return vlm_evaluator.score_layout(simulation_state)

    def _backpropagate(self, node: MCTSNode, reward: float):
        """Backpropagation phase: Update ancestor statistics"""
        current = node
        while current is not None:
            current.visits += 1
            current.total_reward += reward
            current = current.parent

    def _extract_card_elements(self, card_data: Dict) -> List[CardElement]:
        """Extract elements from card data"""
        elements = [
            CardElement('name', card_data['name']),
            CardElement('mana_cost', card_data['mana_cost']),
            CardElement('type_line', card_data['type'])
        ]

        # Abilities (1-3)
        for i, ability in enumerate(card_data.get('abilities', []), 1):
            elements.append(CardElement(f'ability_{i}', ability))

        # P/T (creatures only)
        if 'power_toughness' in card_data:
            elements.append(CardElement('p_t', card_data['power_toughness']))

        # Flavor (optional)
        if card_data.get('flavor_text'):
            elements.append(CardElement('flavor', card_data['flavor_text'], required=False))

        return elements

    def _generate_actions(self, state: LayoutState) -> List[LayoutAction]:
        """Generate all possible actions for current state"""
        if state.is_terminal():
            return []

        next_element = state.remaining_elements[0]
        actions = []

        # Determine applicable regions
        applicable_regions = self._get_applicable_regions(next_element.element_type, state.template_regions)

        for region_name, region in applicable_regions.items():
            # Discrete position grid (10px steps)
            for x in range(region.x, region.x + region.width, 10):
                for y in range(region.y, region.y + region.height, 10):
                    for font_size in [8, 10, 12, 14, 16, 18, 20]:
                        for alignment in ['left', 'center', 'right']:
                            actions.append(LayoutAction(
                                element=next_element,
                                region=region_name,
                                position=(x, y),
                                font_size=font_size,
                                alignment=alignment
                            ))

        return actions

    def _get_applicable_regions(self, element_type: str, template_regions: Dict) -> Dict:
        """Get template regions applicable for element type"""
        region_map = {
            'name': ['name_box'],
            'mana_cost': ['mana_cost_box'],
            'type_line': ['type_line_box'],
            'ability_1': ['text_box_1', 'text_box_2', 'text_box_3'],
            'ability_2': ['text_box_2', 'text_box_3'],
            'ability_3': ['text_box_3'],
            'p_t': ['pt_box'],
            'flavor': ['flavor_box', 'text_box_3']
        }

        applicable = region_map.get(element_type, [])
        return {k: v for k, v in template_regions.items() if k in applicable and v is not None}

    def _reconstruct_path(self, node: MCTSNode) -> LayoutState:
        """Reconstruct layout from leaf node to root"""
        return node.state

    def _execute_fallback(self, card_data, template_regions):
        """Fallback heuristic layout for test mode"""
        # Simple top-to-bottom placement without optimization
        state = LayoutState(
            placed_elements=[],
            remaining_elements=self._extract_card_elements(card_data),
            template_regions=template_regions
        )

        # Place elements top-to-bottom with heuristic positions
        y_offset = 50
        for elem in self._extract_card_elements(card_data):
            state.placed_elements.append(PlacedElement(
                element_type=elem.element_type,
                text_content=elem.text_content,
                position=(50, y_offset),
                size=(650, 30),
                font_size=12,
                alignment='left'
            ))
            y_offset += 40

        return type('Result', (), {
            'success': True,
            'data': {
                'layout': state,
                'quality_score': 0.6,  # Heuristic quality
                'rollouts_completed': 0
            },
            'metadata': {
                'algorithm': 'mcts_layout_fallback',
                'converged': False,
                'max_rollouts': 0
            }
        })()

__all__ = ['MCTSLayoutAlgorithm']
```

---

## Configuration & Tuning

### Recommended Parameters

**For development/testing**:
```python
mcts = MCTSLayoutAlgorithm(
    max_steps=1,              # 100 rollouts (fast iteration)
    max_depth=8,              # 7 elements + root
    branching_factor=50,      # ~50 actions per state
    exploration_constant=1.414,  # Standard √2
    convergence_threshold=0.05   # Looser convergence for speed
)
```

**For production**:
```python
mcts = MCTSLayoutAlgorithm(
    max_steps=3,              # 300 rollouts (higher quality)
    max_depth=8,
    branching_factor=100,     # More thorough exploration
    exploration_constant=1.414,
    convergence_threshold=0.01   # Strict convergence
)
```

### Tuning Guidelines

| Parameter | Effect | Tuning |
|-----------|--------|--------|
| `max_steps` | Rollout budget | ↑ = Better quality, slower |
| `exploration_constant` | Exploration vs exploitation | ↑ = More exploration, slower convergence |
| `convergence_threshold` | Early stopping sensitivity | ↓ = Stricter convergence, more rollouts |
| `branching_factor` | Action space size | ↑ = More thorough, exponentially slower |

---

## Examples

### Example 1: Simple Creature Card

```python
card_data = {
    'name': 'Grizzly Bears',
    'mana_cost': '(Gn)(Gn)',
    'type': 'Creature- Bear',
    'abilities': [''],  # Vanilla creature
    'power_toughness': '2/2'
}

template_regions = {
    'name_box': BoundingBox(50, 30, 650, 30),
    'mana_cost_box': BoundingBox(680, 30, 40, 40),
    'type_line_box': BoundingBox(50, 310, 650, 25),
    'text_box_1': BoundingBox(50, 350, 650, 400),
    'pt_box': BoundingBox(650, 980, 70, 50)
}

mcts = MCTSLayoutAlgorithm(max_steps=1)  # 100 rollouts
result = mcts.execute(
    problem=json.dumps({'card_data': card_data}),
    card_data=card_data,
    template_regions=template_regions
)

print(f"Quality: {result['result'].data['quality_score']}")
print(f"Rollouts: {result['result'].data['rollouts_completed']}")
# Expected: Quality ≥0.9, Rollouts ~20-30 (simple card, fast convergence)
```

### Example 2: Complex Planeswalker

```python
card_data = {
    'name': 'Jace, the Mind Sculptor',
    'mana_cost': '(Bu)(Bu)(Wt)(Wt)',
    'type': 'Legendary Planeswalker- Jace',
    'abilities': [
        '+2: Look at the top card of target player\'s library...',
        '0: Draw three cards, then put two cards from your hand...',
        '-1: Return target creature to its owner\'s hand.',
        '-12: Exile all cards from target player\'s library, then...'
    ],
    'flavor_text': '"The mind is just another puzzle to solve."'
}

mcts = MCTSLayoutAlgorithm(max_steps=2)  # 200 rollouts
result = mcts.execute(
    problem=json.dumps({'card_data': card_data}),
    card_data=card_data,
    template_regions=planeswalker_template_regions
)

print(f"Quality: {result['result'].data['quality_score']}")
print(f"Rollouts: {result['result'].data['rollouts_completed']}")
# Expected: Quality ≥0.8, Rollouts ~80-120 (complex card, needs exploration)
```

---

**Document Status**: ✅ Complete
**Last Updated**: 2025-11-15
**Next Document**: [04-Testing-Integration-Deployment.md](./04-Testing-Integration-Deployment.md)
