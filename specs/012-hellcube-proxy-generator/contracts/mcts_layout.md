# MCTSLayoutAlgorithm Contract

**Module**: `../monorepo/agentic/algorithms/mcts/mcts_layout.py`
**Purpose**: MCTS-based layout optimization for card element placement

---

## Class: MCTSLayoutAlgorithm

**Inherits**: `BaseAlgorithm` (from `../monorepo/agentic/algorithms/base_algorithm.py`)

**Class Attributes**:
```python
SUPPORTS_ITERATION = False  # Internal search (not iterative refinement)
```

---

### __init__()

**Signature**:
```python
def __init__(self, name: str = "mcts_layout", **config):
    """
    Initialize MCTS layout algorithm.

    Args:
        name: Algorithm name (default: "mcts_layout")
        **config: Configuration parameters

    Config Parameters:
        max_steps (int): Rollout budget multiplier (default: 3)
            → max_rollouts = max_steps × 100
        max_depth (int): Max tree depth (default: 8 for 8 elements)
        branching_factor (int): Action space size (default: 24)
        exploration_constant (float): UCB1 C parameter (default: 1.414 = √2)
        convergence_threshold (float): Score stability threshold (default: 0.01)
        domain (str): Problem domain (default: "mtg_layout")
    """
```

**Example**:
```python
# Development (fast iteration)
mcts = MCTSLayoutAlgorithm(
    max_steps=1,  # 100 rollouts
    exploration_constant=1.414,
    convergence_threshold=0.05
)

# Production (high quality)
mcts = MCTSLayoutAlgorithm(
    max_steps=3,  # 300 rollouts
    exploration_constant=1.414,
    convergence_threshold=0.01
)
```

---

### execute()

**Signature**:
```python
def execute(
    self,
    problem: str,
    card_data: Dict[str, Any],
    template_regions: Dict[str, BoundingBox],
    **kwargs
) -> Dict[str, Any]:
    """
    Execute MCTS layout optimization.

    Args:
        problem: JSON string describing the problem (for BaseAlgorithm protocol)
        card_data: Card attributes (name, abilities, etc.)
        template_regions: VLM-detected template bounding boxes
        **kwargs: Optional overrides (max_rollouts, etc.)

    Returns:
        Dict with Result object:
        {
            'result': Result(
                success=True,
                data={
                    'layout': LayoutState,  # Best layout found
                    'quality_score': float,  # VLM score [0.0-1.0]
                    'rollouts_completed': int
                },
                metadata={
                    'algorithm': 'mcts_layout',
                    'converged': bool,
                    'max_rollouts': int,
                    'exploration_constant': float
                }
            )
        }

    Raises:
        ValueError: If card_data missing required fields or template_regions invalid
        MCTSError: If MCTS fails to converge or encounters internal error
    """
```

**Input Example**:
```python
card_data = {
    'name': 'Grizzly Bears',
    'mana_cost': ManaCost(symbols=[('G', 2)], cmc=2),
    'type': 'Creature',
    'subtypes': ['Bear'],
    'abilities': [],  # Vanilla creature
    'power_toughness': '2/2'
}

template_regions = {
    'name_box': BoundingBox(50, 30, 650, 30),
    'mana_cost_box': BoundingBox(680, 30, 40, 40),
    'type_line_box': BoundingBox(50, 310, 650, 25),
    'text_box_1': BoundingBox(50, 350, 650, 400),
    'pt_box': BoundingBox(650, 980, 70, 50)
}

result = mcts.execute(
    problem=json.dumps({'card_data': card_data}),
    card_data=card_data,
    template_regions=template_regions
)
```

**Output Example**:
```python
{
    'result': Result(
        success=True,
        data={
            'layout': LayoutState(
                placed_elements=[
                    PlacedElement(
                        element_type='name',
                        text_content='Grizzly Bears',
                        position=(350, 30),
                        size=(250, 30),
                        font_size=16,
                        alignment='center'
                    ),
                    # ... more elements
                ],
                remaining_elements=[],
                quality_score=0.92
            ),
            'quality_score': 0.92,
            'rollouts_completed': 45
        },
        metadata={
            'algorithm': 'mcts_layout',
            'converged': True,
            'max_rollouts': 100,
            'exploration_constant': 1.414
        }
    )
}
```

---

### _select()

**Signature** (internal):
```python
def _select(self, node: MCTSNode) -> MCTSNode:
    """
    Selection phase: UCB1 tree traversal.

    Args:
        node: Starting node (usually root)

    Returns:
        MCTSNode: Selected node for expansion (unexpanded or terminal)

    Algorithm:
        current = node
        while current is not terminal AND current is fully expanded:
            current = child with highest UCB1 score
        return current
    """
```

---

### _expand()

**Signature** (internal):
```python
def _expand(self, node: MCTSNode) -> MCTSNode:
    """
    Expansion phase: Add new child for unexplored action.

    Args:
        node: Node to expand

    Returns:
        MCTSNode: Newly created child node

    Algorithm:
        action = pop one untried action from node
        new_state = apply action to node's state
        create child node with new_state
        add child to node's children
        return child
    """
```

---

### _simulate()

**Signature** (internal):
```python
def _simulate(self, node: MCTSNode, vlm_evaluator: VLMLayoutEvaluator) -> float:
    """
    Simulation phase: Random rollout + VLM evaluation.

    Args:
        node: Node to simulate from
        vlm_evaluator: VLM evaluator instance

    Returns:
        float: VLM quality score [0.0-1.0]

    Algorithm:
        simulation_state = copy of node's state
        while simulation_state has remaining elements:
            action = random choice from valid actions
            simulation_state = apply action
        score = VLM evaluate simulation_state
        return score
    """
```

---

### _backpropagate()

**Signature** (internal):
```python
def _backpropagate(self, node: MCTSNode, reward: float):
    """
    Backpropagation phase: Update ancestor statistics.

    Args:
        node: Leaf node to backpropagate from
        reward: VLM quality score [0.0-1.0]

    Side Effects:
        Updates visits and total_reward for all ancestors up to root

    Algorithm:
        current = node
        while current is not None:
            current.visits += 1
            current.total_reward += reward
            current = current.parent
    """
```

---

### _generate_actions()

**Signature** (internal):
```python
def _generate_actions(self, state: LayoutState) -> List[LayoutAction]:
    """
    Generate strategic actions for next element.

    Args:
        state: Current layout state

    Returns:
        List[LayoutAction]: ~24 actions per element

    Strategy (Strategic Sampling):
        8 positions per region:
            - 4 corners: (x, y), (x+w, y), (x, y+h), (x+w, y+h)
            - 4 midpoints: top-center, bottom-center, left-center, right-center

        Element-specific constraints:
            - name: center alignment only, fonts [14, 16]
            - mana_cost: right alignment only, font [14]
            - type_line: center alignment only, font [12]
            - abilities: left alignment only, fonts [10, 11, 12]
            - p_t: right alignment only, font [14]
            - flavor: left alignment only, font [10]

        Result: 8 × 3 × 1 = 24 actions (vs 49,140 full enumeration)
    """
```

---

## Error Classes

```python
class MCTSError(Exception):
    """Raised when MCTS encounters internal error"""
    pass

class ConvergenceError(MCTSError):
    """Raised when MCTS fails to converge within rollout budget"""
    def __init__(self, rollouts_completed: int, best_score: float):
        self.rollouts_completed = rollouts_completed
        self.best_score = best_score
        super().__init__(
            f"MCTS failed to converge after {rollouts_completed} rollouts "
            f"(best score: {best_score:.3f})"
        )
```

---

## Performance Contract

**Guarantees**:
- **Convergence Detection**: Stops when score stable within `convergence_threshold` for 10 consecutive rollouts
- **Rollout Budget**: Never exceeds `max_rollouts` (= `max_steps` × 100)
- **Quality Lower Bound**: Returns layout with score ≥ 0.0 (may be poor if no good layout exists)

**Typical Performance** (with VLM every rollout):
- Simple card (1 ability): 20-30 rollouts, 4-6 seconds
- Medium card (2 abilities): 40-60 rollouts, 8-12 seconds
- Complex card (3+ abilities): 60-80 rollouts, 12-16 seconds

**Memory**: <50MB per card (MCTS tree + LayoutState copies)

---

## Integration with VLM

**Dependencies**:
- `VLMLayoutEvaluator` (from `vlm_evaluators.py`)
- `instructor` framework (from `../monorepo/agentic/core/utils/instructor.py`)
- `PerceptInterface` (from `../monorepo/agentic/core/interfaces/percept_interface.py`)

**VLM Call Pattern**:
```python
# In _simulate():
vlm_evaluator = VLMLayoutEvaluator(self.instructor, self.percept_interface)
quality_score = vlm_evaluator.score_layout(simulation_state)
# Returns float [0.0-1.0]
```

---

## Testing Contract

**Unit Tests** (pytest):
```python
def test_mcts_initialization():
    """Verify algorithm initializes with correct defaults"""

def test_ucb1_score_calculation():
    """Verify UCB1 formula: Q + C×sqrt(ln(N_parent)/N)"""

def test_action_generation_strategic_sampling():
    """Verify ~24 actions per element (not 49,140)"""

def test_convergence_detection():
    """Verify early termination when score stable"""
```

**BDD Tests** (behave):
```gherkin
Scenario: MCTS converges on simple card layout
    Given a card with 1 ability text box
    And a template with detected regions
    And an MCTS algorithm with max_steps=1
    When I execute the algorithm
    Then the quality score should be >= 0.8
    And the rollouts completed should be <= 100
    And the algorithm should have converged
```
