# Testing, Integration & Deployment
## Complete Validation Strategy for MCTS Layout Optimization

**Document**: 04-Testing-Integration-Deployment.md
**Version**: 1.0.0
**Created**: 2025-11-15
**Related**: [03-MCTS-Implementation-Spec.md](./03-MCTS-Implementation-Spec.md)

---

## Table of Contents

1. [Testing Strategy Overview](#testing-strategy-overview)
2. [Phase 1: VLM + Reflexion Integration](#phase-1-vlm--reflexion-integration)
3. [Phase 2: MCTS Algorithm Implementation](#phase-2-mcts-algorithm-implementation)
4. [Phase 3: MCTS Behave Tests](#phase-3-mcts-behave-tests)
5. [Phase 4: Grid World Domain Test](#phase-4-grid-world-domain-test)
6. [Phase 5: Hellcube Excel Integration](#phase-5-hellcube-excel-integration)
7. [Integration Architecture](#integration-architecture)
8. [Performance Optimization](#performance-optimization)
9. [Deployment & Success Criteria](#deployment--success-criteria)
10. [Risk Mitigation](#risk-mitigation)

---

## Testing Strategy Overview

**Goal**: Validate MCTS + VLM integration through **incremental complexity** - from infrastructure to production use case.

### 5-Phase Incremental Validation

```
Phase 1: VLM + Reflexion (infrastructure test)
  ↓ Validates: Ollama backend, instructor integration, VLM structured output
  ↓ Risk: High - if this fails, MCTS won't work
  ↓
Phase 2: MCTS Implementation (algorithm correctness)
  ↓ Validates: MCTS core operations, BaseAlgorithm compliance
  ↓ Risk: Medium - algorithmic bugs
  ↓
Phase 3: MCTS Behave Tests (BDD audit)
  ↓ Validates: Convergence, quality thresholds, behave pattern compliance
  ↓ Risk: Low - structured testing catches edge cases
  ↓
Phase 4: Grid World Test (known-good problem)
  ↓ Validates: MCTS on simple domain before layout complexity
  ↓ Risk: Low - tractability check with ground truth
  ↓
Phase 5: Hellcube Excel Integration (production)
  ↓ Validates: End-to-end workflow with real card data
  ↓ Risk: Very Low - all components validated independently
```

**Rationale**:
- **Fast feedback**: Phase 1 fails quickly if Ollama not working
- **Risk mitigation**: Each phase derisks next phase
- **Debuggability**: Failures isolated to specific components
- **Confidence building**: Success at each phase increases certainty

---

## Phase 1: VLM + Reflexion Integration

**Goal**: Validate VLM + Instructor infrastructure works before implementing MCTS.

**Why Reflexion?** Already exists in monorepo - reuse for infrastructure validation.

### Test Setup

**Prerequisites**:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Download llava-1.5 model (~4GB)
ollama pull llava:13b

# Verify backend
export BACKEND=ollama
ollama list | grep llava
```

### Behave Feature Test

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/components/algorithms/vlm_reflexion_integration.feature`

```gherkin
Feature: VLM Integration with Reflexion Algorithm

  Background:
    Given the backend is set to "ollama"
    And Ollama is running with llava model

  Scenario: Reflexion with VLM backend generates structured output
    Given a Reflexion algorithm with instructor
    When I execute the algorithm with problem "Analyze this visual data"
    Then the result should use Ollama backend
    And the output should conform to ReflexionChain Pydantic schema
    And trials should contain structured reflections

  Scenario: VLM processes image and returns structured regions
    Given a PerceptInterface with instructor
    And a test MTG card template image
    When I call process_with_vlm with the image
    Then the result should contain detected regions
    And regions should have valid bounding boxes
    And bounding boxes should fit within 750x1050 dimensions

  Scenario: Instructor generates structured VLM output
    Given an instructor configured for Ollama backend
    And a Pydantic model for TemplateRegions
    When I call generate_structured with VLM prompt
    Then the result should be a TemplateRegions instance
    And all required fields should be populated
    And bounding box coordinates should be valid integers
```

### Step Definitions

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/components/algorithms/steps/vlm_integration_steps.py`

```python
from behave import given, when, then
import os
from agentic.algorithms.reflexion import ReflexionAlgorithm
from agentic.core.interfaces.percept_interface import PerceptInterface
from agentic.core.utils.instructor import get_instructor
from pydantic import BaseModel, Field

@given('the backend is set to "ollama"')
def step_set_backend_ollama(context):
    os.environ['BACKEND'] = 'ollama'
    context.backend = 'ollama'

@given('Ollama is running with llava model')
def step_verify_ollama(context):
    import subprocess
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    assert 'llava' in result.stdout, "llava model not found in Ollama"

@given('a Reflexion algorithm with instructor')
def step_create_reflexion_with_instructor(context):
    instructor = get_instructor('ollama')
    context.algorithm = ReflexionAlgorithm(
        max_steps=2,
        instructor=instructor
    )

@when('I execute the algorithm with problem {problem}')
def step_execute_algorithm(context, problem):
    context.result = context.algorithm.execute(problem)

@then('the result should use Ollama backend')
def step_verify_ollama_backend(context):
    assert context.result['result'].metadata.get('backend') == 'ollama'

@then('the output should conform to ReflexionChain Pydantic schema')
def step_verify_pydantic_schema(context):
    result_data = context.result['result'].data
    assert 'trials' in result_data
    assert isinstance(result_data['trials'], list)
    for trial in result_data['trials']:
        assert 'trial' in trial
        assert 'attempt' in trial
        assert 'reflection' in trial
        assert 'score' in trial
        assert 0.0 <= trial['score'] <= 1.0
```

### Success Criteria

- ✅ Ollama backend connects and responds
- ✅ llava model processes image inputs
- ✅ Instructor generates Pydantic-validated output
- ✅ PerceptInterface process_with_vlm() succeeds
- ✅ Reflexion algorithm works with VLM backend

**Exit Criteria**: All scenarios pass → MCTS infrastructure validated

---

## Phase 2: MCTS Algorithm Implementation

**Goal**: Implement MCTSLayoutAlgorithm following Reflexion template pattern.

### Implementation Checklist

**File Creation**:
```bash
mkdir -p /home/joey/Documents/GitHub/monorepo/agentic/algorithms/mcts
touch /home/joey/Documents/GitHub/monorepo/agentic/algorithms/mcts/__init__.py
touch /home/joey/Documents/GitHub/monorepo/agentic/algorithms/mcts/mcts_layout.py
touch /home/joey/Documents/GitHub/monorepo/agentic/algorithms/mcts/data_structures.py
touch /home/joey/Documents/GitHub/monorepo/agentic/algorithms/mcts/vlm_integration.py
```

**Code Structure**:
- `mcts_layout.py` - MCTSLayoutAlgorithm class (see doc 03)
- `data_structures.py` - LayoutState, MCTSNode, BoundingBox, etc.
- `vlm_integration.py` - VLMTemplateAnalyzer, VLMLayoutEvaluator

**Pattern Compliance**:
```python
# __init__.py
from .mcts_layout import MCTSLayoutAlgorithm

__all__ = ['MCTSLayoutAlgorithm']
```

### Unit Tests

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/unit/algorithms/mcts/test_mcts_layout.py`

```python
import pytest
import json
from agentic.algorithms.mcts import MCTSLayoutAlgorithm
from agentic.algorithms.mcts.data_structures import (
    BoundingBox, LayoutState, CardElement
)

def test_mcts_init():
    """Test MCTS algorithm initialization"""
    mcts = MCTSLayoutAlgorithm(name="test_mcts", max_steps=1)

    assert mcts.name == "test_mcts"
    assert mcts.max_steps == 1
    assert mcts.max_rollouts == 100  # 1 × 100
    assert mcts.SUPPORTS_ITERATION == False  # Internal search

def test_mcts_unified_parameters():
    """Test unified parameter schema"""
    mcts = MCTSLayoutAlgorithm(
        max_steps=2,
        max_depth=8,
        branching_factor=50,
        domain="mtg_layout"
    )

    assert mcts.max_rollouts == 200
    assert mcts.max_depth == 8
    assert mcts.branching_factor == 50
    assert mcts.domain == "mtg_layout"

def test_mcts_extract_card_elements():
    """Test card element extraction"""
    card_data = {
        'name': 'Test Card',
        'mana_cost': '(Bu)(Bu)',
        'type': 'Creature- Test',
        'abilities': ['Ability 1', 'Ability 2'],
        'power_toughness': '2/2',
        'flavor_text': 'Flavor text'
    }

    mcts = MCTSLayoutAlgorithm()
    elements = mcts._extract_card_elements(card_data)

    assert len(elements) == 7  # name, cost, type, 2 abilities, P/T, flavor
    assert elements[0].element_type == 'name'
    assert elements[3].element_type == 'ability_1'
    assert elements[6].element_type == 'flavor'

def test_mcts_generate_actions():
    """Test action generation for state"""
    state = LayoutState(
        remaining_elements=[CardElement('name', 'Test Card')],
        template_regions={
            'name_box': BoundingBox(50, 30, 650, 30)
        }
    )

    mcts = MCTSLayoutAlgorithm()
    actions = mcts._generate_actions(state)

    assert len(actions) > 0
    # 650/10 × 30/10 × 7 fonts × 3 alignments = 65 × 3 × 7 × 3 = ~4,095 actions
    # (Actually fewer due to grid boundaries)
    assert all(action.element.element_type == 'name' for action in actions)

def test_mcts_fallback_execution():
    """Test fallback execution without VLM"""
    card_data = {
        'name': 'Test Card',
        'mana_cost': '(Rd)',
        'type': 'Sorcery',
        'abilities': ['Deal 3 damage to target creature.']
    }

    template_regions = {
        'name_box': BoundingBox(50, 30, 650, 30),
        'mana_cost_box': BoundingBox(680, 30, 40, 40),
        'type_line_box': BoundingBox(50, 310, 650, 25),
        'text_box_1': BoundingBox(50, 350, 650, 400)
    }

    mcts = MCTSLayoutAlgorithm(max_steps=1)  # No instructor/VLM
    result = mcts.execute(
        problem=json.dumps({'card_data': card_data}),
        card_data=card_data,
        template_regions=template_regions
    )

    assert 'result' in result
    assert result['result'].success == True
    assert result['result'].data['quality_score'] == 0.6  # Fallback quality
    assert result['result'].metadata['algorithm'] == 'mcts_layout_fallback'

def test_mcts_ucb1_calculation():
    """Test UCB1 score calculation"""
    from agentic.algorithms.mcts.data_structures import MCTSNode

    parent = MCTSNode(
        state=LayoutState(),
        visits=100
    )

    child = MCTSNode(
        state=LayoutState(),
        parent=parent,
        visits=10,
        total_reward=7.5
    )

    ucb1 = child.get_ucb1_score(exploration_constant=1.414)

    # Expected: 0.75 + 1.414 × sqrt(ln(100) / 10)
    #         = 0.75 + 1.414 × sqrt(4.605 / 10)
    #         = 0.75 + 1.414 × 0.679
    #         = 0.75 + 0.960
    #         = 1.710
    assert abs(ucb1 - 1.710) < 0.01

def test_bounding_box_overlap():
    """Test bounding box overlap detection"""
    box1 = BoundingBox(100, 100, 200, 50)
    box2 = BoundingBox(250, 120, 200, 50)  # Overlaps
    box3 = BoundingBox(350, 100, 200, 50)  # No overlap

    assert box1.overlaps(box2) == True
    assert box1.overlaps(box3) == False

def test_layout_state_terminal():
    """Test terminal state detection"""
    state = LayoutState(
        remaining_elements=[CardElement('name', 'Test')]
    )
    assert state.is_terminal() == False

    state.remaining_elements = []
    assert state.is_terminal() == True
```

**Run Tests**:
```bash
cd /home/joey/Documents/GitHub/monorepo
BACKEND=test pytest tests/unit/algorithms/mcts/test_mcts_layout.py -v
```

### Success Criteria

- ✅ All unit tests pass
- ✅ MCTS follows BaseAlgorithm protocol
- ✅ Fallback execution works without VLM
- ✅ UCB1, selection, expansion, simulation, backpropagation implemented correctly

---

## Phase 3: MCTS Behave Tests

**Goal**: Audit MCTS correctness with BDD tests following monorepo patterns.

### Behave Feature

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/components/algorithms/mcts_layout.feature`

```gherkin
Feature: MCTS Layout Optimization Algorithm

  Background:
    Given the backend is set to "ollama"

  Scenario: MCTS initializes with unified parameters
    Given an MCTS algorithm with max_steps=2
    Then the algorithm should have 200 max rollouts
    And SUPPORTS_ITERATION should be False
    And the domain should be configurable

  Scenario: MCTS converges to optimal layout within rollout budget
    Given a card with 1 ability text box
    And a template with detected regions
    And an MCTS algorithm with max_steps=1
    When I execute the algorithm
    Then the result should contain an optimal layout
    And the quality score should be >= 0.8
    And the rollouts completed should be <= 100
    And the algorithm should have converged

  Scenario: MCTS handles complex cards with 3 abilities
    Given a card with 3 ability text boxes
    And a template with 3 text regions
    And an MCTS algorithm with max_steps=2
    When I execute the algorithm
    Then the result should contain an optimal layout
    And all 3 abilities should be positioned
    And the quality score should be >= 0.75
    And no elements should overlap

  Scenario: MCTS with VLM backend evaluates layout quality
    Given the backend is set to "ollama"
    And an MCTS algorithm with instructor and percept interface
    And a simple test card
    When I execute with a card layout problem
    Then VLM should be called for quality evaluation
    And the output should conform to LayoutState schema
    And quality score should be between 0.0 and 1.0

  Scenario: MCTS fallback works without VLM
    Given an MCTS algorithm without instructor
    And a simple test card
    When I execute the algorithm
    Then the fallback heuristic should be used
    And the result should succeed with quality 0.6
    And no VLM calls should be made

  Scenario: MCTS respects template region boundaries
    Given a card with 2 abilities
    And a template with strict region boundaries
    And an MCTS algorithm with max_steps=1
    When I execute the algorithm
    Then all placed elements should be within region boundaries
    And no elements should exceed template dimensions

  Scenario: MCTS early termination on convergence
    Given a simple card with 1 ability
    And an MCTS algorithm with max_steps=3
    When I execute the algorithm
    Then the algorithm should terminate early
    And rollouts completed should be less than 300
    And convergence count should be >= 10
```

### Step Definitions

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/components/algorithms/steps/mcts_layout_steps.py`

```python
from behave import given, when, then
import json
from agentic.algorithms.mcts import MCTSLayoutAlgorithm
from agentic.algorithms.mcts.data_structures import BoundingBox, CardElement
from agentic.core.utils.instructor import get_instructor
from agentic.core.interfaces.percept_interface import PerceptInterface

@given('an MCTS algorithm with max_steps={steps:d}')
def step_create_mcts(context, steps):
    context.algorithm = MCTSLayoutAlgorithm(max_steps=steps)

@given('a card with {num:d} ability text box')
@given('a card with {num:d} ability text boxes')
def step_create_card(context, num):
    abilities = [f'Ability {i+1} text' for i in range(num)]
    context.card = {
        'name': 'Test Card',
        'mana_cost': '(Bu)(Bu)',
        'type': 'Creature- Test',
        'abilities': abilities,
        'power_toughness': '2/2'
    }

@given('a template with detected regions')
@given('a template with {num:d} text regions')
def step_create_template(context, num=1):
    context.template_regions = {
        'name_box': BoundingBox(50, 30, 650, 30),
        'mana_cost_box': BoundingBox(680, 30, 40, 40),
        'type_line_box': BoundingBox(50, 310, 650, 25),
        'text_box_1': BoundingBox(50, 350, 650, 150),
        'pt_box': BoundingBox(650, 980, 70, 50)
    }
    if num >= 2:
        context.template_regions['text_box_2'] = BoundingBox(50, 510, 650, 150)
    if num >= 3:
        context.template_regions['text_box_3'] = BoundingBox(50, 670, 650, 150)

@given('an MCTS algorithm with instructor and percept interface')
def step_create_mcts_with_vlm(context):
    instructor = get_instructor('ollama')
    percept = PerceptInterface(instructor=instructor)
    context.algorithm = MCTSLayoutAlgorithm(
        max_steps=1,
        instructor=instructor,
        percept_interface=percept
    )

@when('I execute the algorithm')
def step_execute_mcts(context):
    context.result = context.algorithm.execute(
        problem=json.dumps({'card_data': context.card}),
        card_data=context.card,
        template_regions=context.template_regions
    )

@then('the result should contain an optimal layout')
def step_verify_layout(context):
    assert 'result' in context.result
    assert 'layout' in context.result['result'].data

@then('the quality score should be >= {score:f}')
def step_verify_quality(context, score):
    actual_score = context.result['result'].data['quality_score']
    assert actual_score >= score, f"Quality {actual_score} < {score}"

@then('the rollouts completed should be <= {max_rollouts:d}')
def step_verify_rollouts(context, max_rollouts):
    rollouts = context.result['result'].data['rollouts_completed']
    assert rollouts <= max_rollouts, f"Rollouts {rollouts} > {max_rollouts}"

@then('the algorithm should have converged')
def step_verify_convergence(context):
    converged = context.result['result'].metadata['converged']
    assert converged == True, "Algorithm did not converge"

@then('no elements should overlap')
def step_verify_no_overlap(context):
    layout = context.result['result'].data['layout']
    assert layout.has_overlap() == False, "Elements overlap detected"
```

**Run Tests**:
```bash
cd /home/joey/Documents/GitHub/monorepo
BACKEND=ollama behave tests/components/algorithms/mcts_layout.feature
```

### Success Criteria

- ✅ All behave scenarios pass
- ✅ MCTS converges within rollout budget
- ✅ Quality scores meet thresholds (≥0.8 for simple, ≥0.75 for complex)
- ✅ VLM integration works correctly
- ✅ Fallback mode works without VLM

---

## Phase 4: Grid World Domain Test

**Goal**: Validate MCTS on simple known-good problem before complex layout optimization.

### Grid World Problem

**Problem**: Find optimal path in 3×3 grid with obstacles.

```
Grid:
S . .
. X .
. . G

S = Start (0,0)
G = Goal (2,2)
X = Obstacle (1,1)

Optimal path: (0,0) → (0,1) → (0,2) → (1,2) → (2,2)
Length: 4 moves
```

### Grid World State

```python
@dataclass
class GridWorldState:
    """Grid world state for MCTS testing"""
    position: Tuple[int, int]  # (row, col)
    goal: Tuple[int, int]
    obstacles: List[Tuple[int, int]]
    grid_size: int = 3

    def is_terminal(self) -> bool:
        return self.position == self.goal

    def get_actions(self) -> List[str]:
        """Get valid moves from current position"""
        row, col = self.position
        actions = []

        # Up, Down, Left, Right
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in moves:
            new_row, new_col = row + dr, col + dc
            if (0 <= new_row < self.grid_size and
                0 <= new_col < self.grid_size and
                (new_row, new_col) not in self.obstacles):
                actions.append((new_row, new_col))

        return actions
```

### Test Implementation

**File**: `/home/joey/Documents/GitHub/monorepo/tests/integration/test_mcts_grid_world.py`

```python
import pytest
from agentic.algorithms.mcts import MCTSLayoutAlgorithm

def test_mcts_grid_world_simple():
    """MCTS should find optimal path in 3×3 grid"""

    # Adapt MCTS for grid world (state = GridWorldState, actions = moves)
    # Reward function: -1 per step, 0 at goal
    # This tests MCTS core operations on simple problem

    grid = GridWorld(size=3, obstacles=[(1,1)], start=(0,0), goal=(2,2))

    # Use MCTSLayoutAlgorithm with grid world state adapter
    mcts = MCTSLayoutAlgorithm(max_steps=1)  # 100 rollouts

    result = mcts.execute(problem=json.dumps({'grid': grid.to_dict()}))
    path = result['result'].data['path']

    # Validate path
    assert path[0] == (0, 0), "Path should start at (0,0)"
    assert path[-1] == (2, 2), "Path should end at (2,2)"
    assert (1, 1) not in path, "Path should avoid obstacle at (1,1)"
    assert len(path) <= 6, "Path should be reasonably short"

    # Optimal path is 5 steps: (0,0)→(0,1)→(0,2)→(1,2)→(2,2)
    # MCTS should find optimal or near-optimal
    print(f"Found path length: {len(path)}, Optimal: 5")
```

**Success Criteria**:
- ✅ MCTS finds valid path (no obstacles, reaches goal)
- ✅ Path length ≤ optimal + 2 (near-optimal)
- ✅ Converges in <100 rollouts for simple grid
- ✅ Demonstrates MCTS correctness on known problem

**Rationale**: If MCTS fails on grid world (simple, discrete, well-studied), it will fail on layout optimization (complex, continuous, novel). Grid world success builds confidence.

---

## Phase 5: Hellcube Excel Integration

**Goal**: End-to-end validation with real Hellcube proxy generation.

### Integration Components

**1. Spreadsheet Parser → Card Data**

```python
# parser/excel_parser.py
import pandas as pd

def parse_hellcube_spreadsheet(filepath: str) -> List[Dict]:
    """Parse Hellcube AJ.xlsx into structured card data

    Returns:
        List[Dict]: Card objects with name, mana_cost, type, abilities, etc.
    """
    df = pd.read_excel(filepath)

    cards = []
    # Semantic parsing with adjacency detection (FR-001)
    # ...
    return cards
```

**2. Template Downloader + VLM Analyzer**

```python
# skills/template_downloader.py
def download_mtg_templates(required_types: List[str]) -> Dict[str, str]:
    """Download MTG templates for required card types

    Returns:
        Dict[str, str]: Mapping of template_type → local_path
    """
    templates = {}
    for template_type in required_types:
        url = research_template_url(template_type)
        local_path = download_file(url, dest=f"templates/{template_type}.png")
        templates[template_type] = local_path

    return templates

# VLM analysis (one-time per template)
vlm_analyzer = VLMTemplateAnalyzer(percept_interface, instructor)
template_regions_cache = {}

for template_type, template_path in templates.items():
    regions = vlm_analyzer.analyze_template(template_path)
    template_regions_cache[template_type] = regions
    print(f"Analyzed {template_type}: {len(regions)} regions detected")
```

**3. MCTS Layout Optimizer**

```python
# proxy_generator/layout_optimizer.py
from a2a_orchestrator.batch_processor import BatchProcessor

mcts = MCTSLayoutAlgorithm(
    instructor=instructor,
    percept_interface=percept_interface,
    max_steps=3,  # 300 rollouts per card
    exploration_constant=1.414
)

def generate_proxy_with_mcts(card: Dict) -> str:
    """Generate proxy for one card using MCTS layout optimization"""

    # Select template via fuzzy matching
    template = select_template_fuzzy_match(card, templates)
    template_regions = template_regions_cache[template.type]

    # MCTS optimization
    problem = json.dumps({
        'card_data': card,
        'template_regions': template_regions
    })

    result = mcts.execute(
        problem=problem,
        card_data=card,
        template_regions=template_regions
    )

    optimal_layout = result['result'].data['layout']
    quality_score = result['result'].data['quality_score']

    # Render final proxy
    proxy_image = render_proxy(card, template, optimal_layout)
    output_path = f"output/{card['name']}.png"
    save_proxy(proxy_image, output_path)

    print(f"Generated {card['name']}: quality={quality_score:.2f}")
    return output_path

# Batch processing with Feature 010
batch_processor = BatchProcessor(
    batch_size=10,
    max_concurrent=4,
    retry_policy=ExponentialBackoff()
)

cards = parse_hellcube_spreadsheet("Hellcube AJ.xlsx")
results = batch_processor.process_parallel(
    items=cards,
    processor_fn=generate_proxy_with_mcts
)

print(f"Generated {len(results)} proxies")
```

### End-to-End Behave Test

**File**: `/home/joey/Documents/GitHub/magic-cards-edh-deck/tests/features/hellcube_proxy_generation.feature`

```gherkin
Feature: Hellcube Proxy Generation with MCTS Layout

  Background:
    Given the Hellcube AJ.xlsx spreadsheet exists
    And the backend is set to "ollama"
    And Ollama is running with llava model

  Scenario: Parse Hellcube spreadsheet
    When I parse the Hellcube spreadsheet
    Then I should extract 200+ cards
    And each card should have name, type, and mana cost
    And abilities should be parsed as list of strings

  Scenario: Download MTG templates with VLM analysis
    Given a list of required template types from parsed cards
    When I download MTG templates
    Then I should have 50+ template files
    When I analyze templates with VLM
    Then each template should have detected regions
    And regions should include name_box, type_line_box, text_boxes

  Scenario: Generate proxy for simple creature card
    Given a parsed creature card with 1 ability
    And a creature template with VLM-analyzed regions
    When I generate proxy with MCTS layout optimizer
    Then the proxy PNG should be created
    And the quality score should be >= 0.8
    And the proxy should be print-ready (750x1050 @ 300 DPI)

  Scenario: Generate proxy for complex planeswalker
    Given a parsed planeswalker card with 3 abilities
    And a planeswalker template
    When I generate proxy with MCTS layout optimizer
    Then the proxy PNG should be created
    And the quality score should be >= 0.75
    And all 3 abilities should be legible

  Scenario: Batch generate 200+ Hellcube proxies
    Given parsed Hellcube cards (200+)
    And downloaded templates with VLM analysis
    When I run batch proxy generation with MCTS
    Then all 200+ proxies should be generated
    And 95%+ should have quality score >= 0.8
    And the batch should complete within 10 minutes
    And proxies should be organized by Markov tree voting

  Scenario: Handle card with invalid artwork URL
    Given a card with unreachable artwork URL
    When I generate proxy with MCTS
    Then proxy generation should fail for that card
    And an error should be logged with card name and URL
    And remaining cards should continue processing
```

### Performance Validation

**Metrics to Collect**:
```python
import time

start_time = time.time()
results = []

for card in cards:
    card_start = time.time()
    result = generate_proxy_with_mcts(card)
    card_time = time.time() - card_start

    results.append({
        'card': card['name'],
        'quality_score': result['quality_score'],
        'rollouts': result['rollouts_completed'],
        'time': card_time
    })

total_time = time.time() - start_time

# Analyze
import pandas as pd
df = pd.DataFrame(results)

print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
print(f"Avg time per card: {df['time'].mean():.2f}s")
print(f"Avg quality: {df['quality_score'].mean():.3f}")
print(f"Quality >= 0.8: {(df['quality_score'] >= 0.8).sum() / len(df) * 100:.1f}%")
print(f"Avg rollouts: {df['rollouts'].mean():.1f}")
```

**Target Metrics**:
- Total time: ≤600s (10 min) for 200 cards
- Avg time per card: ≤2s
- Avg quality: ≥0.85
- Quality ≥0.8: ≥95% of cards
- Avg rollouts: ≤80 (early convergence)

### Success Criteria

- ✅ Spreadsheet parser extracts 200+ cards with ≥95% accuracy
- ✅ Template downloader fetches 50+ templates
- ✅ VLM analyzes all templates successfully
- ✅ MCTS generates proxies for all cards
- ✅ 95%+ cards have quality ≥0.8
- ✅ Batch processing completes in <10 minutes
- ✅ Markov tree voting organizes proxies optimally
- ✅ Artwork URL failures handled gracefully

---

## Integration Architecture

### Data Flow Diagram

```
Hellcube AJ.xlsx
  ↓
[Semantic Spreadsheet Parser] (FR-001)
  ↓
List[Card] (200+ cards)
  ├─→ [Infer Attributes] (FR-002, FR-004a, FR-004b)
  │     - Color from mana symbols
  │     - Legendary status from Types field
  │     - Primary type extraction
  ↓
[Template Research & Download] (FR-005, FR-006, FR-007)
  ↓
Dict[template_type → template_path]
  ↓
[VLM Template Analyzer] (One-time per template)
  ↓
Dict[template_type → TemplateRegions]
  ↓
[Template Matcher] (FR-008a - Fuzzy matching)
  ↓
FOR EACH Card:
  ├─ [Select Template] (color + type + legendary matching)
  ├─ [MCTS Layout Optimizer] (FR-008)
  │    ├─ Initialize: LayoutState(remaining=card_elements, regions=template_regions)
  │    ├─ MCTS Loop (100-300 rollouts):
  │    │    └─ Selection → Expansion → Simulation → Backpropagation
  │    ├─ VLM Evaluation (layout quality scoring)
  │    └─ Extract: optimal_layout + quality_score
  ├─ [Download Artwork] (FR-009)
  │    └─ If fail: Log error, continue (don't block batch)
  ├─ [Render Proxy] (Pillow composition)
  │    └─ Composite: template + card elements @ optimal positions
  └─ [Save PNG] (FR-011 - 300 DPI, 750x1050px)
       ↓
       output/{card_name}.png
  ↓
[Markov Tree Voting] (FR-012 - Folder organization)
  ↓
Organized folders:
  color/type/*.png  OR  type/color/*.png
  (depending on card distribution)
```

### Component Dependencies

```
a2a_orchestrator/
├── orchestrator.py           # Workflow coordination
├── batch_processor.py        # Parallel proxy generation (Feature 010)
└── skills/
    ├── excel_parser_skill.py          # NEW: Spreadsheet parsing
    ├── template_downloader_skill.py   # NEW: Template research
    ├── mcts_layout_skill.py           # NEW: MCTS optimization wrapper
    └── proxy_renderer_skill.py        # NEW: Final proxy composition

monorepo/agentic/algorithms/
└── mcts/
    ├── mcts_layout.py        # MCTSLayoutAlgorithm
    ├── data_structures.py    # LayoutState, MCTSNode, etc.
    └── vlm_integration.py    # VLMTemplateAnalyzer, VLMLayoutEvaluator

monorepo/agentic/core/
├── interfaces/
│   └── percept_interface.py  # VLM vision processing
└── utils/
    └── instructor.py          # Structured output generation
```

---

## Performance Optimization

### 1. VLM Caching

**Problem**: VLM template analysis is slow (~2s per template)

**Solution**: One-time analysis + persistent cache

```python
import json
import hashlib

def get_template_regions_cached(template_path: str, vlm_analyzer) -> Dict:
    """Get template regions with disk caching"""

    # Cache key from template file hash
    with open(template_path, 'rb') as f:
        template_hash = hashlib.md5(f.read()).hexdigest()

    cache_path = f".cache/template_regions_{template_hash}.json"

    # Check cache
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            regions_dict = json.load(f)
        return {k: BoundingBox(**v) for k, v in regions_dict.items()}

    # Analyze with VLM
    regions = vlm_analyzer.analyze_template(template_path)

    # Save to cache
    os.makedirs(".cache", exist_ok=True)
    regions_dict = {k: v.__dict__ for k, v in regions.items()}
    with open(cache_path, 'w') as f:
        json.dump(regions_dict, f)

    return regions
```

**Impact**: 50 templates × 2s = 100s → 0s (after first run)

### 2. Parallel Batch Processing

**Problem**: Sequential processing of 200 cards too slow

**Solution**: Leverage Feature 010 batch processor

```python
batch_processor = BatchProcessor(
    batch_size=10,          # Process 10 cards per batch
    max_concurrent=4,       # 4 parallel workers
    retry_policy=ExponentialBackoff(max_retries=3)
)

results = batch_processor.process_parallel(
    items=cards,
    processor_fn=generate_proxy_with_mcts
)
```

**Impact**: 200 cards × 2s = 400s → 100s (4× speedup)

### 3. MCTS Rollout Budget Tuning

**Problem**: 300 rollouts per card may be overkill for simple cards

**Solution**: Adaptive rollout budget based on card complexity

```python
def adaptive_max_steps(card: Dict) -> int:
    """Determine rollout budget based on card complexity"""

    complexity = len(card.get('abilities', []))

    if complexity == 0:  # Vanilla creature
        return 1  # 100 rollouts
    elif complexity <= 2:  # Simple card
        return 2  # 200 rollouts
    else:  # Complex card (3+ abilities)
        return 3  # 300 rollouts

mcts = MCTSLayoutAlgorithm(max_steps=adaptive_max_steps(card))
```

**Impact**: Avg rollouts 300 → ~150 (50% speedup)

### 4. Early Convergence

**Already implemented**: 10 consecutive stable scores → early termination

**Impact**: Complex cards may use full budget, simple cards terminate at ~30-50 rollouts

### 5. Action Space Pruning

**Problem**: 10px grid generates ~5,000 actions per element

**Solution**: Prune invalid actions before MCTS expansion

```python
def _generate_actions(self, state: LayoutState) -> List[LayoutAction]:
    """Generate actions with pruning"""

    actions = []
    # ... (generate all candidate actions)

    # Prune actions that would cause overlap
    valid_actions = [
        action for action in actions
        if not self._would_cause_overlap(action, state)
    ]

    return valid_actions

def _would_cause_overlap(self, action: LayoutAction, state: LayoutState) -> bool:
    """Check if action would cause element overlap"""

    # Estimate element bounding box
    text_width = estimate_text_width(action.element.text_content, action.font_size)
    text_height = estimate_text_height(action.element.text_content, action.font_size)
    new_box = BoundingBox(action.position[0], action.position[1], text_width, text_height)

    # Check against all placed elements
    for placed_elem in state.placed_elements:
        if new_box.overlaps(placed_elem.get_bounding_box()):
            return True

    return False
```

**Impact**: Action space 5,000 → ~500 (10× reduction, faster MCTS)

### Combined Optimization Impact

**Before**:
- VLM template analysis: 100s
- Sequential card processing: 400s (200 × 2s)
- Full 300 rollout budget per card
- **Total: ~600s (10 min)**

**After**:
- VLM caching: ~0s (cached)
- Parallel batch processing: 100s (4× speedup)
- Adaptive rollout budget: ~50% fewer rollouts
- Early convergence: ~30% time savings
- **Total: ~200s (3.3 min)**

**3× overall speedup**

---

## Deployment & Success Criteria

### Technical Validation

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| MCTS convergence | ≤100 rollouts | Avg rollouts per card |
| Layout quality | ≥0.8 for 95%+ cards | Quality score distribution |
| VLM integration | 100% success | VLM call failure rate |
| Template coverage | 50+ templates | Unique template types downloaded |
| Spreadsheet parsing | ≥95% accuracy | Cards correctly extracted |
| Batch processing | <10 min for 200 cards | End-to-end workflow time |

### Integration Validation

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| End-to-end workflow | Zero manual intervention | Automation completeness |
| Print quality | 300 DPI, 750×1050px | Image resolution check |
| Text readability | Legible at 2.5"×3.5" | Visual inspection |
| Element positioning | No overlap | Bounding box validation |
| Artwork handling | Graceful failure | Error logging verification |

### Deployment Checklist

**Prerequisites**:
```bash
# 1. Install Ollama
curl https://ollama.ai/install.sh | sh
ollama pull llava:13b

# 2. Install Python dependencies
pip install pandas openpyxl Pillow requests beautifulsoup4 python-pptx pydantic

# 3. Verify monorepo MCTS algorithm
cd /home/joey/Documents/GitHub/monorepo
BACKEND=ollama pytest tests/unit/algorithms/mcts/ -v
BACKEND=ollama behave tests/components/algorithms/mcts_layout.feature

# 4. Clone magic-cards-edh-deck repo
cd /home/joey/Documents/GitHub/magic-cards-edh-deck
git checkout 012-hellcube-proxy-generator
```

**Deployment Steps**:
```bash
# 1. Parse Hellcube spreadsheet
python -m a2a_orchestrator.skills.excel_parser_skill "Hellcube AJ.xlsx"

# 2. Download templates
python -m a2a_orchestrator.skills.template_downloader_skill

# 3. Analyze templates with VLM (one-time)
python -m a2a_orchestrator.skills.template_analyzer

# 4. Generate proxies
BACKEND=ollama python -m a2a_orchestrator.workflows.hellcube_proxy_generation

# 5. Verify output
ls output/*.png | wc -l  # Should be 200+
python -m scripts.validate_proxy_quality output/
```

### Success Metrics Dashboard

```python
# generate_success_report.py
import pandas as pd
import json

results = json.load(open('execution_manifest.json'))

df = pd.DataFrame(results)

print("=== MCTS Layout Optimization Success Report ===\n")

print(f"Total cards processed: {len(df)}")
print(f"Successful generations: {df['success'].sum()} ({df['success'].sum()/len(df)*100:.1f}%)")
print(f"Failed generations: {(~df['success']).sum()}\n")

print(f"Quality score distribution:")
print(f"  Mean: {df['quality_score'].mean():.3f}")
print(f"  Median: {df['quality_score'].median():.3f}")
print(f"  Min: {df['quality_score'].min():.3f}")
print(f"  Max: {df['quality_score'].max():.3f}")
print(f"  ≥0.8: {(df['quality_score'] >= 0.8).sum()} ({(df['quality_score'] >= 0.8).sum()/len(df)*100:.1f}%)\n")

print(f"MCTS convergence:")
print(f"  Avg rollouts: {df['rollouts'].mean():.1f}")
print(f"  Converged: {df['converged'].sum()} ({df['converged'].sum()/len(df)*100:.1f}%)\n")

print(f"Performance:")
print(f"  Total time: {df['time'].sum():.1f}s ({df['time'].sum()/60:.1f} min)")
print(f"  Avg time per card: {df['time'].mean():.2f}s")
print(f"  Target: ≤10 min → {'✅ PASS' if df['time'].sum() <= 600 else '❌ FAIL'}\n")

print(f"Success criteria:")
print(f"  ✅ Quality ≥0.8: {(df['quality_score'] >= 0.8).sum()/len(df)*100:.1f}% (target: ≥95%)")
print(f"  ✅ Convergence: {df['converged'].sum()/len(df)*100:.1f}%")
print(f"  ✅ Batch time: {df['time'].sum()/60:.1f} min (target: ≤10 min)")
```

---

## Risk Mitigation

### Risk 1: Ollama VLM Accuracy Issues

**Risk**: llava-1.5 may misdetect template regions

**Likelihood**: Medium
**Impact**: High (poor layouts)

**Mitigation**:
1. **Validation**: Manually verify VLM region detection for 10 sample templates
2. **Fallback**: If VLM quality < threshold, use heuristic region detection
3. **Iteration**: Test multiple VLM models (llava-1.5, bakllava, llava-1.6) and pick best

**Contingency**: If VLM unreliable, fall back to manual template region annotation (50 templates × 5 min = 4 hours one-time cost)

### Risk 2: MCTS Not Converging

**Risk**: MCTS may not find optimal layouts within 100 rollouts

**Likelihood**: Low
**Impact**: Medium (suboptimal quality)

**Mitigation**:
1. **Grid world validation**: Prove MCTS correctness on simple problem first
2. **Rollout budget tuning**: Increase to 300 rollouts if needed
3. **Heuristic guidance**: Add biased rollout policy to accelerate convergence

**Contingency**: If MCTS fails, fall back to heuristic top-to-bottom placement (quality ~0.6)

### Risk 3: Performance Too Slow

**Risk**: Batch processing takes >10 min for 200 cards

**Likelihood**: Low (with optimizations)
**Impact**: Medium (user experience)

**Mitigation**:
1. **Parallel processing**: Feature 010 batch processor (4× speedup)
2. **VLM caching**: Persistent template region cache
3. **Adaptive rollouts**: Reduce budget for simple cards
4. **Action pruning**: Filter invalid actions before MCTS

**Contingency**: Increase `max_concurrent` to 8 workers (requires more CPU cores)

### Risk 4: VLM Dependency Installation

**Risk**: User may struggle to install Ollama + llava model

**Likelihood**: Medium
**Impact**: Low (deployment blocker)

**Mitigation**:
1. **Documentation**: Detailed quickstart.md with step-by-step Ollama setup
2. **Fallback mode**: MCTS works with heuristic scoring if VLM unavailable
3. **Docker**: Provide Dockerfile with Ollama pre-installed

**Contingency**: Offer cloud-based VLM option (Claude Code MCP) for users who can't install Ollama

---

**Document Status**: ✅ Complete
**Last Updated**: 2025-11-15

**Next Step**: Begin Phase 1 - VLM + Reflexion integration testing

**All 4 Documents Complete! Ready for implementation.** ✨
