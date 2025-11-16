# Monorepo Code Structure & Patterns
## Algorithm Library Deep Dive for MCTS Implementation

**Document**: 02-Monorepo-Code-Structure.md
**Version**: 1.0.0
**Created**: 2025-11-15
**Related**: [01-Problem-And-Design-Rationale.md](./01-Problem-And-Design-Rationale.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Algorithm Directory Structure](#algorithm-directory-structure)
3. [BaseAlgorithm Protocol](#basealgorithm-protocol)
4. [Reflexion Template Pattern](#reflexion-template-pattern)
5. [Instructor Framework](#instructor-framework)
6. [PerceptInterface](#perceptinterface)
7. [Testing Patterns](#testing-patterns)
8. [Integration Points](#integration-points)

---

## Overview

The **monorepo agentic library** provides the foundational patterns and utilities for implementing MCTSLayoutAlgorithm. This document provides a comprehensive walkthrough of the code structure, protocols, and patterns to follow.

**Location**: `/home/joey/Documents/GitHub/monorepo/agentic`

**Purpose**: Understand existing patterns to ensure MCTS implementation:
- Follows established conventions
- Integrates seamlessly with algorithm registry
- Passes behave BDD tests
- Supports instructor-based structured output
- Works with VLM backend via PerceptInterface

---

## Algorithm Directory Structure

```
/home/joey/Documents/GitHub/monorepo/agentic/algorithms/
├── __init__.py                    # Algorithm package exports
├── base_algorithm.py              # Abstract base class (92 LOC)
├── algorithm_registry.py          # Discovery and registration system
├── discovery.py                   # Dynamic algorithm loading
│
├── reflexion/                     # Reflexion algorithm (TEMPLATE TO FOLLOW)
│   ├── __init__.py
│   └── reflexion.py               # ReflexionAlgorithm implementation (154 LOC)
│
├── chain_of_thought/
│   ├── __init__.py
│   └── chain_of_thought.py
│
├── react/
│   ├── __init__.py
│   └── react.py
│
├── tree_of_thought/
│   ├── __init__.py
│   └── tree_of_thought.py         # Tree search pattern (similar to MCTS)
│
└── mcts/                          # ← NEW: MCTS implementation goes here
    ├── __init__.py                # To create
    └── mcts_layout.py             # MCTSLayoutAlgorithm class to implement
```

### Key Utilities

```
/home/joey/Documents/GitHub/monorepo/agentic/core/
├── interfaces/
│   └── percept_interface.py      # VLM integration support (200 LOC)
│       - PerceptInterface class
│       - process_with_vlm() method
│       - Instructor integration
│
└── utils/
    └── instructor.py              # Structured output generation (350 LOC)
        - get_backend() → 'claude_code' | 'ollama' | 'test'
        - get_instructor(backend) → Instructor instance
        - generate_structured(prompt, response_model)
        - Backend switching logic
```

### Testing Structure

```
/home/joey/Documents/GitHub/monorepo/agentic/tests/
├── unit/algorithms/               # pytest unit tests
│   ├── reflexion/
│   │   └── test_reflexion.py      # Unit tests for Reflexion
│   ├── tree_of_thought/
│   │   └── test_tree_of_thought.py
│   └── mcts/                      # ← NEW: MCTS unit tests
│       └── test_mcts_layout.py    # To create
│
└── components/algorithms/         # behave BDD tests
    ├── environment.py             # Test environment setup
    ├── reflexion.feature          # Reflexion behavior specs
    ├── tree_of_thought.feature
    ├── mcts_layout.feature        # ← NEW: MCTS behavior specs (to create)
    │
    └── steps/
        ├── reflexion_steps.py     # Reflexion step definitions
        ├── tree_of_thought_steps.py
        └── mcts_layout_steps.py   # ← NEW: MCTS step definitions (to create)
```

---

## BaseAlgorithm Protocol

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/algorithms/base_algorithm.py`

**Line Count**: 92 LOC (ultra-minimal pruned version)

### Full Code Walkthrough

```python
#!/usr/bin/env python3.11
"""
Ultra-minimal Base Algorithm for agentic2
Pruned from 150+ lines to 15 lines following aggressive pruning philosophy

4D JUDGE RULING: UNIFORM PARAMETER SCHEMA ENFORCED
All algorithms must support unified parameter interface for true AOL uniformity
"""

import os
from typing import Any, Dict, Optional, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from agentic.core.protocols import AlgorithmProtocol

def _get_backend() -> str:
    """Get backend from environment at runtime (lazy load to support dynamic env changes)."""
    return os.getenv('BACKEND', 'test')
```

**Key Insight**: Backend is determined **at runtime** from `BACKEND` environment variable.
- `BACKEND=claude_code` → Use Claude Code MCP
- `BACKEND=ollama` → Use local Ollama VLM
- `BACKEND=test` → Use mock/fallback mode

This enables testing without Ollama installed.

```python
class BaseAlgorithm(ABC):  # Conforms to AlgorithmProtocol
    """Ultra-minimal base algorithm interface - agentic2 pruned version

    Protocol Conformance: Implements AlgorithmProtocol (typing.Protocol)
    - execute() method with unified signature
    - get_info() method for metadata

    4D JUDGE MANDATE: Unified parameter schema for seamless algorithm swapping:
    - max_steps: int = 3      # Iteration control (universal)
    - max_depth: int = 1      # Depth control (1=linear, >1=hierarchical)
    - branching_factor: int = 1  # Branch control (1=linear, >1=tree-like)
    - domain: str = "general"    # Problem domain context

    STATELESS HYBRID ARCHITECTURE (FR-026, Constitutional Principle VI):
    - Provider owns loop and maintains state (iteration_num, history)
    - Algorithm is STATELESS pure function receiving optional iteration_context
    - iteration_context enables provider coordination, None enables standalone/MCP use
    - Algorithm returns continue_iteration signal for provider control
    """

    # Problem-solving strategy introspection for ExecutionEngine
    # True = Trial-and-error strategy (benefits from multi-episode iteration)
    # False = Internal search strategy (completes in single episode)
    SUPPORTS_ITERATION = True
```

**Critical Attribute**: `SUPPORTS_ITERATION`
- **True**: Algorithm uses trial-and-error (Reflexion, ReAct)
  - Needs multiple episodes to improve
  - Provider calls `execute()` in a loop
- **False**: Algorithm uses internal search (MCTS, Tree of Thought)
  - Completes all exploration internally
  - Single `execute()` call is sufficient

**MCTS will set `SUPPORTS_ITERATION = False`** because MCTS runs 100 rollouts internally.

```python
    def __init__(self, name: str = "unknown", **config):
        self.name = name
        self.config = config

        # UNIFIED PARAMETER SCHEMA - All algorithms support these parameters
        self.max_steps = config.get('max_steps', 3)
        self.max_depth = config.get('max_depth', 1)  # 1=linear, >1=hierarchical
        self.branching_factor = config.get('branching_factor', 1)  # 1=linear, >1=tree-like
        self.domain = config.get('domain', 'general')

        # Legacy parameter mapping for backwards compatibility
        if 'max_trials' in config:
            self.max_steps = config['max_trials']  # Reflexion compatibility

        self.metadata = {
            "algorithm": name,
            "backend": _get_backend(),
            "parameters": {
                "max_steps": self.max_steps,
                "max_depth": self.max_depth,
                "branching_factor": self.branching_factor,
                "domain": self.domain
            }
        }
```

**Unified Parameters Explained**:

| Parameter | Meaning | MCTS Usage |
|-----------|---------|------------|
| `max_steps` | Iteration/trial count | Rollout multiplier (max_steps × 100 = rollouts) |
| `max_depth` | Tree depth limit | MCTS tree depth (7-8 for card layouts) |
| `branching_factor` | Children per node | Action space size per state |
| `domain` | Problem domain | "mtg_layout" for card layouts |

**Example MCTS configuration**:
```python
mcts = MCTSLayoutAlgorithm(
    name="mcts_layout",
    max_steps=3,           # 300 rollouts (3 × 100)
    max_depth=8,           # Max tree depth (7 elements + root)
    branching_factor=10,   # ~10 position choices per element
    domain="mtg_layout"
)
```

```python
    # Protocol-required getter methods for AlgorithmProtocol
    def get_name(self) -> str:
        """Get algorithm name."""
        return self.name

    def get_max_steps(self) -> int:
        """Get maximum reasoning steps."""
        return self.max_steps

    def get_domain(self) -> Optional[str]:
        """Get target domain for algorithm."""
        return self.domain
```

**Protocol Compliance**: These getters enable algorithm introspection by the registry and execution engine.

```python
    @abstractmethod
    def execute(self,
                problem: str,
                on_trial: Optional[Callable[[Dict[str, Any]], bool]] = None,
                iteration_context: Optional[Dict[str, Any]] = None,
                **kwargs) -> Any:
        """Execute algorithm with optional trial iteration control.

        Args:
            problem: Problem description to solve
            on_trial: Optional callback for trial iteration control
                     Receives trial dict (attempt, score, reflection, trial_num, timestamp)
                     Returns True to continue, False to stop iteration
            iteration_context: Optional provider-managed iteration state for stateless execution
                             Fields: iteration_num (int), max_iterations (int), history (List[Dict])
                             When None, algorithm runs standalone (graceful degradation for MCP/direct use)
                             When provided, algorithm uses these values and returns continue_iteration signal
            **kwargs: Additional algorithm-specific parameters

        Returns:
            Algorithm execution result (Dict with optional 'continue_iteration' field when iteration_context provided)
        """
        pass
```

**Signature Breakdown**:

**1. `problem: str`** - Problem description (JSON-encoded for MCTS)
```python
problem = json.dumps({
    'card_data': {...},
    'template_regions': {...}
})
```

**2. `on_trial: Optional[Callable]`** - Progress callback
```python
def progress_callback(trial_data: Dict[str, Any]) -> bool:
    print(f"Rollout {trial_data['rollout']}: score={trial_data['best_score']}")
    return True  # Continue

mcts.execute(problem, on_trial=progress_callback)
```

**3. `iteration_context: Optional[Dict]`** - Provider-managed state
```python
# Stateless execution - provider owns loop
for i in range(max_iterations):
    iteration_context = {
        'iteration_num': i,
        'max_iterations': max_iterations,
        'history': previous_results
    }
    result = algorithm.execute(problem, iteration_context=iteration_context)

    if not result.get('continue_iteration', False):
        break  # Algorithm signals completion
```

MCTS **ignores** `iteration_context` (internal search completes in single call).

**4. `**kwargs`** - Algorithm-specific parameters
```python
# MCTS-specific
result = mcts.execute(
    problem,
    card_data=card_obj,              # Parsed card object
    template_regions=regions_dict,   # VLM-detected regions
    vlm_evaluator=evaluator          # Quality scoring function
)
```

```python
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "backend": _get_backend(),
            "type": "base",
            "unified_parameters": {
                "max_steps": self.max_steps,
                "max_depth": self.max_depth,
                "branching_factor": self.branching_factor,
                "domain": self.domain
            }
        }

__all__ = ['BaseAlgorithm']
```

**Summary**: BaseAlgorithm defines the **contract** all algorithms must implement:
- Unified parameters (`max_steps`, `max_depth`, `branching_factor`, `domain`)
- Stateless `execute()` method
- Protocol-compliant getters
- Backend-agnostic design

---

## Reflexion Template Pattern

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/algorithms/reflexion/reflexion.py`

**Line Count**: 154 LOC

**Purpose**: This is the **exact pattern** MCTS must follow for consistency.

### Full Code Walkthrough

```python
#!/usr/bin/env python3.11
"""
Ultra-minimal Reflexion Algorithm - Uniform Interface
Properly inherits from BaseAlgorithm for seamless swapping
"""

from typing import Dict, Any, List, Optional, Callable
from ..base_algorithm import BaseAlgorithm

class ReflexionAlgorithm(BaseAlgorithm):
    """Reflexion reasoning with uniform interface for experimentation

    Problem-solving strategy: Trial-and-error (multi-episode)
    Each execution is ONE trial with reflection to improve next attempt.
    """

    # Uses trial-and-error strategy - benefits from multi-episode iteration
    SUPPORTS_ITERATION = True
```

**MCTS equivalent**:
```python
class MCTSLayoutAlgorithm(BaseAlgorithm):
    """MCTS for card layout optimization - uniform interface

    Problem-solving strategy: Internal search (single episode)
    Each execution runs MCTS rollouts to convergence.
    """

    # Internal search strategy - completes in single episode
    SUPPORTS_ITERATION = False  # ← KEY DIFFERENCE
```

```python
    def __init__(self, name: str = "reflexion", **config):
        """Uniform constructor - uses unified parameter schema from BaseAlgorithm"""
        super().__init__(name, **config)  # Pass config to parent for unified parameters
        # Legacy max_trials mapped to max_steps by BaseAlgorithm
        # Instructor injected via config or defaults to None for test mode
        self.instructor = config.get('instructor')
```

**MCTS equivalent**:
```python
    def __init__(self, name: str = "mcts_layout", **config):
        """Uniform constructor - uses unified parameter schema"""
        super().__init__(name, **config)
        self.instructor = config.get('instructor')
        self.percept_interface = config.get('percept_interface')  # ← MCTS addition

        # MCTS-specific parameters (map from unified schema)
        self.max_rollouts = self.max_steps * 100  # max_steps × rollout multiplier
        self.exploration_constant = config.get('exploration_constant', 1.414)
        self.convergence_threshold = config.get('convergence_threshold', 0.01)
```

```python
    def execute(self,
                problem: str,
                on_trial: Optional[Callable[[Dict[str, Any]], bool]] = None,
                iteration_context: Optional[Dict[str, Any]] = None,
                **kwargs) -> Dict[str, Any]:
        """Execute Reflexion with real LLM backend

        STATELESS PATTERN (FR-026): Algorithm is pure function, provider maintains state

        Args:
            problem: Problem description to solve
            on_trial: Optional callback for trial iteration control
                     Receives trial dict (attempt, score, reflection, trial_num, timestamp)
                     Returns True to continue, False to stop iteration
            iteration_context: Optional provider-managed state (iteration_num, max_iterations, history)
                             When None: standalone mode (graceful degradation)
                             When provided: uses provider's iteration state, returns continue_iteration signal
            **kwargs: Additional algorithm-specific parameters

        Returns:
            Dict with 'result' field and optional 'continue_iteration' (bool)
        """
        # Use unified max_steps parameter (mapped from max_trials by BaseAlgorithm)

        # Fallback if no instructor
        if self.instructor is None:
            result = self._execute_fallback(problem)
        else:
            # Real Reflexion with instructor
            try:
                from pydantic import BaseModel, Field
                from typing import List as TypingList

                class ReflexionTrial(BaseModel):
                    trial: int = Field(description="Trial number")
                    attempt: str = Field(description="Solution attempt for this trial")
                    reflection: str = Field(description="Critical reflection on the attempt")
                    score: float = Field(ge=0.0, le=1.0, description="Quality score for this attempt")

                class ReflexionChain(BaseModel):
                    trials: TypingList[ReflexionTrial] = Field(description="Progressive trials with reflection")

                prompt = f"""You are solving this problem using Reflexion (self-reflection and improvement).

Problem: {problem}
Max trials: {self.max_steps}

Generate {self.max_steps} trials where each trial:
- Attempts a solution
- Critically reflects on what could be improved
- Builds on previous reflection to improve the next attempt

Each trial should show progressive improvement in quality (increasing scores from 0.4 to 0.95).
Be specific and show real learning between trials."""

                instructor_result = self.instructor.generate_structured(
                    prompt=prompt,
                    response_model=ReflexionChain
                )

                trials = [
                    {
                        'trial': t.trial,
                        'attempt': t.attempt,
                        'reflection': t.reflection,
                        'score': t.score
                    }
                    for t in instructor_result.trials
                ]

                result = type('Result', (), {
                    'success': True,
                    'data': {
                        'trials': trials,
                        'final_solution': trials[-1]['attempt'],
                        'improvement_trajectory': [t['score'] for t in trials]
                    },
                    'metadata': {
                        'algorithm': 'reflexion',
                        'trials_completed': len(trials),
                        'final_score': trials[-1]['score'],
                        'max_trials': self.max_steps
                    }
                })()

            except Exception as e:
                print(f"⚠️  Instructor failed: {e}, using fallback")
                result = self._execute_fallback(problem)

        # STATELESS PATTERN: Return structured response with continue_iteration signal
        response = {'result': result}

        # If iteration_context provided, calculate continue_iteration signal
        if iteration_context is not None:
            iteration_num = iteration_context.get('iteration_num', 0)
            max_iterations = iteration_context.get('max_iterations', self.max_steps)

            # Continue if successful AND haven't reached max iterations
            should_continue = result.success and (iteration_num + 1 < max_iterations)
            response['continue_iteration'] = should_continue

        return response

    def _execute_fallback(self, problem: str) -> Any:
        """Fallback hardcoded execution for test mode"""
        trials = []
        for i in range(self.max_steps):
            trial_num = i + 1
            base_score = 0.4 + (0.3 * i)  # Progressive improvement
            trials.append({
                'trial': trial_num,
                'attempt': f'Trial {trial_num} solution for {problem}',
                'reflection': f'Trial {trial_num} reflection: {"Initial attempt" if i == 0 else "Refined approach" if i < self.max_steps-1 else "Final optimization"}',
                'score': min(base_score, 0.95)
            })
        return type('Result', (), {
            'success': True,
            'data': {
                'trials': trials,
                'final_solution': trials[-1]['attempt'],
                'improvement_trajectory': [t['score'] for t in trials]
            },
            'metadata': {
                'algorithm': 'reflexion',
                'trials_completed': len(trials),
                'final_score': trials[-1]['score'],
                'max_trials': self.max_steps
            }
        })()

__all__ = ['ReflexionAlgorithm']
```

### Key Patterns to Follow for MCTS

**1. Instructor-Based Structured Output**
```python
# Define Pydantic models for type-safe output
class LayoutQuality(BaseModel):
    readability_score: float = Field(ge=0.0, le=1.0)
    convention_compliance: float = Field(ge=0.0, le=1.0)
    aesthetic_balance: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    issues: List[str]

# Use instructor to generate structured output
result = self.instructor.generate_structured(
    prompt="Evaluate this MTG card layout...",
    response_model=LayoutQuality
)
```

**2. Fallback Execution**
```python
def _execute_fallback(self, card_data, template_regions):
    """Fallback heuristic layout for test mode"""
    # Simple top-to-bottom placement without optimization
    # Enables testing without VLM/Ollama
```

**3. Result Structure**
```python
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
```

**4. Return Dict with 'result' Key**
```python
response = {'result': result}
return response
```

---

## Instructor Framework

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/core/utils/instructor.py`

**Line Count**: ~350 LOC

**Purpose**: Provides structured output generation with backend switching.

### Key Functions

```python
def get_backend() -> str:
    """Get current backend from environment - DI LAW compliant"""
    from .di_resolver import get_backend
    return get_backend()  # Returns 'claude_code', 'ollama', or 'test'

def get_available_backends() -> List[str]:
    """Get list of available backends"""
    return ["claude_code", "ollama", "test"]

def get_instructor(backend: str = None) -> Instructor:
    """Get instructor instance for specified backend

    Args:
        backend: 'claude_code', 'ollama', or 'test'

    Returns:
        Instructor instance configured for backend
    """
    if backend is None:
        backend = get_backend()

    if backend == "ollama":
        return OllamaInstructor()
    elif backend == "claude_code":
        return ClaudeCodeInstructor()
    else:  # test
        return TestInstructor()
```

### Instructor Interface

```python
class Instructor(ABC):
    """Base instructor interface"""

    @abstractmethod
    def generate_structured(self,
                          prompt: str,
                          response_model: Type[BaseModel],
                          **kwargs) -> BaseModel:
        """Generate structured output conforming to Pydantic model

        Args:
            prompt: Natural language prompt
            response_model: Pydantic BaseModel class
            **kwargs: Backend-specific parameters

        Returns:
            Instance of response_model with validated data
        """
        pass
```

### Usage Pattern for MCTS

```python
# In MCTSLayoutAlgorithm.__init__
self.instructor = config.get('instructor')
if self.instructor is None:
    backend = get_backend()
    self.instructor = get_instructor(backend)

# In VLM evaluation
class LayoutQuality(BaseModel):
    readability_score: float = Field(ge=0.0, le=1.0)
    convention_compliance: float = Field(ge=0.0, le=1.0)
    aesthetic_balance: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    issues: List[str]

result = self.instructor.generate_structured(
    prompt=f"Evaluate this MTG card layout...",
    response_model=LayoutQuality
)

score = result.overall_score  # Type-safe access
```

---

## PerceptInterface

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/core/interfaces/percept_interface.py`

**Line Count**: ~200 LOC

**Purpose**: Provides VLM vision processing capabilities.

### Key Implementation

```python
class PerceptInterface:
    """Real percept interface for environmental sensing"""

    def __init__(self, instructor=None):
        self.instructor = instructor
        self.vlm_enabled = False

    def process_with_vlm(self, visual_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process visual data with VLM - can fail if VLM unavailable

        Args:
            visual_data: Dict containing image_path or image_data

        Returns:
            Structured VLM output

        Raises:
            RuntimeError: If VLM not available
        """
        if not self.vlm_enabled and self.instructor is None:
            raise RuntimeError("VLM processing not available without instructor backend")

        # Use instructor to generate structured vision output
        # ...
```

### Usage Pattern for MCTS

```python
# In MCTSLayoutAlgorithm.__init__
self.percept_interface = config.get('percept_interface')
if self.percept_interface is None:
    self.percept_interface = PerceptInterface(instructor=self.instructor)

# In VLM template analysis
class TemplateRegions(BaseModel):
    name_box: BoundingBox
    mana_cost_box: BoundingBox
    type_line_box: BoundingBox
    text_boxes: List[BoundingBox]
    pt_box: Optional[BoundingBox]
    flavor_box: Optional[BoundingBox]

visual_data = {"image_path": template_image_path}
result = self.percept_interface.process_with_vlm(visual_data)

regions = self.instructor.generate_structured(
    prompt="Detect all text regions in this MTG card template...",
    response_model=TemplateRegions
)
```

---

## Testing Patterns

### Unit Tests (pytest)

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/unit/algorithms/reflexion/test_reflexion.py`

**Pattern**:
```python
import pytest
from agentic.algorithms.reflexion import ReflexionAlgorithm

def test_reflexion_init():
    """Test algorithm initialization"""
    algo = ReflexionAlgorithm(name="test_reflexion", max_steps=5)
    assert algo.name == "test_reflexion"
    assert algo.max_steps == 5
    assert algo.SUPPORTS_ITERATION == True

def test_reflexion_execute_fallback():
    """Test fallback execution without instructor"""
    algo = ReflexionAlgorithm(max_steps=3)
    result = algo.execute("Test problem")

    assert 'result' in result
    assert result['result'].success == True
    assert len(result['result'].data['trials']) == 3

def test_reflexion_with_instructor(mock_instructor):
    """Test with real instructor backend"""
    algo = ReflexionAlgorithm(max_steps=2, instructor=mock_instructor)
    result = algo.execute("Solve this problem")

    assert result['result'].success == True
    assert result['result'].metadata['trials_completed'] == 2
```

**MCTS equivalent to create**:
```python
# test_mcts_layout.py
def test_mcts_init():
    """Test MCTS algorithm initialization"""
    algo = MCTSLayoutAlgorithm(name="test_mcts", max_steps=1)
    assert algo.name == "test_mcts"
    assert algo.max_rollouts == 100  # 1 × 100
    assert algo.SUPPORTS_ITERATION == False

def test_mcts_convergence():
    """Test MCTS converges within rollout budget"""
    algo = MCTSLayoutAlgorithm(max_steps=1)  # 100 rollouts
    card_data = create_test_card()
    template_regions = create_test_regions()

    result = algo.execute(
        problem=json.dumps({'card_data': card_data}),
        card_data=card_data,
        template_regions=template_regions
    )

    assert result['result'].success == True
    assert result['result'].data['rollouts_completed'] <= 100
    assert result['result'].data['quality_score'] >= 0.8
```

### Behave BDD Tests

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/components/algorithms/reflexion.feature`

**Pattern**:
```gherkin
Feature: Reflexion Algorithm

  Scenario: Reflexion improves solution quality across trials
    Given a Reflexion algorithm with max_steps=3
    When I execute the algorithm with problem "Find optimal path"
    Then the result should contain 3 trials
    And trial scores should show improvement
    And the final score should be >= 0.7

  Scenario: Reflexion with instructor backend
    Given the backend is set to "ollama"
    And a Reflexion algorithm with instructor
    When I execute with a test problem
    Then the result should use structured output
    And the output should conform to ReflexionChain schema
```

**MCTS equivalent to create**:
```gherkin
# mcts_layout.feature
Feature: MCTS Layout Optimization Algorithm

  Scenario: MCTS converges to optimal layout within rollout budget
    Given a card with 3 ability text boxes
    And a template with detected regions
    And an MCTS algorithm with max_steps=1
    When I execute the algorithm
    Then the result should contain an optimal layout
    And the quality score should be >= 0.8
    And the rollouts completed should be <= 100

  Scenario: MCTS with VLM backend
    Given the backend is set to "ollama"
    And an MCTS algorithm with instructor and percept interface
    When I execute with a card layout problem
    Then VLM should evaluate layout quality
    And the output should conform to LayoutState schema
```

**Step Definitions**:
```python
# mcts_layout_steps.py
from behave import given, when, then
from agentic.algorithms.mcts import MCTSLayoutAlgorithm

@given('a card with {num:d} ability text boxes')
def step_create_card(context, num):
    context.card = create_test_card(num_abilities=num)

@given('a template with detected regions')
def step_create_template(context):
    context.template_regions = create_test_template_regions()

@given('an MCTS algorithm with max_steps={steps:d}')
def step_create_mcts(context, steps):
    context.algorithm = MCTSLayoutAlgorithm(max_steps=steps)

@when('I execute the algorithm')
def step_execute_mcts(context):
    context.result = context.algorithm.execute(
        problem=json.dumps({'card_data': context.card}),
        card_data=context.card,
        template_regions=context.template_regions
    )

@then('the result should contain an optimal layout')
def step_verify_layout(context):
    assert 'layout' in context.result['result'].data

@then('the quality score should be >= {score:f}')
def step_verify_quality(context, score):
    assert context.result['result'].data['quality_score'] >= score
```

---

## Integration Points

### Algorithm Registry

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/algorithms/algorithm_registry.py`

MCTS will be auto-discovered if placed in `agentic/algorithms/mcts/` directory:

```python
# In __init__.py
from .mcts_layout import MCTSLayoutAlgorithm

__all__ = ['MCTSLayoutAlgorithm']
```

Usage:
```python
from agentic.algorithms import get_algorithm

# Auto-discovery finds MCTSLayoutAlgorithm
mcts = get_algorithm('mcts_layout', max_steps=3)
```

### Backend Switching

Test with different backends:

```bash
# Test mode (no dependencies)
BACKEND=test pytest tests/unit/algorithms/mcts/

# Ollama local VLM
BACKEND=ollama behave tests/components/algorithms/mcts_layout.feature

# Claude Code (for comparison)
BACKEND=claude_code python -m agentic.algorithms.mcts
```

---

## Summary

**Monorepo provides**:
1. **BaseAlgorithm protocol** - Unified interface all algorithms follow
2. **Reflexion template** - Exact pattern for MCTS to replicate
3. **Instructor framework** - Structured output with backend switching
4. **PerceptInterface** - VLM integration utilities
5. **Testing patterns** - pytest unit + behave BDD conventions

**MCTS implementation must**:
1. Inherit from `BaseAlgorithm`
2. Follow Reflexion code structure
3. Use instructor for structured VLM output
4. Provide fallback execution for test mode
5. Include pytest unit tests + behave BDD tests
6. Support backend switching (claude_code/ollama/test)

**Next Document**: [03-MCTS-Implementation-Spec.md](./03-MCTS-Implementation-Spec.md) - Detailed MCTS algorithm specification

---

**Document Status**: ✅ Complete
**Last Updated**: 2025-11-15
