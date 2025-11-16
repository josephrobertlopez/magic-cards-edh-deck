# Phase 0: Empirical Validation & Implementation Go Decision
## Resolving Adversarial Review Through Experiments, Not Debate

**Document**: 07-Phase-0-Validation-And-Go-Decision.md
**Version**: 1.0.0
**Created**: 2025-11-16
**Status**: Pre-Implementation Validation Gate
**Response To**: Document 06 - Adversarial Review

---

## Executive Summary

Document 06 (Adversarial Review) correctly identified **4 critical untested assumptions** that could invalidate the two-phase MCTS approach. Rather than theoretical debate, this document proposes **empirical validation experiments** to prove or disprove each assumption before committing to full implementation.

**Validation Philosophy**: "Show me the data, not the argument."

---

## Table of Contents

1. [Validation Strategy](#validation-strategy)
2. [Monorepo Integration Analysis](#monorepo-integration-analysis)
3. [Test 1: Heuristic-VLM Correlation](#test-1-heuristic-vlm-correlation)
4. [Test 2: VLM Evaluation Consistency](#test-2-vlm-evaluation-consistency)
5. [Test 3: Action Space Sufficiency](#test-3-action-space-sufficiency)
6. [Test 4: Template Region Detection](#test-4-template-region-detection)
7. [Implementation Timeline](#implementation-timeline)
8. [Decision Gate](#decision-gate)
9. [Next Steps](#next-steps)

---

## Validation Strategy

### The 4 Critical Assumptions

| ID | Assumption | Risk if False | Test Duration |
|----|------------|---------------|---------------|
| **A1** | Heuristic-VLM correlation ≥0.7 | Two-phase approach fails | 1 day |
| **A2** | VLM std dev ≤0.05 | MCTS won't converge | 0.5 day |
| **A3** | 24 actions sufficient | Miss optimal layouts | 1 day |
| **A4** | VLM detects regions ±10px | Need manual annotation | 0.5 day |

**Total Validation Time**: 3 days
**Cost**: $0 (local Ollama, no API costs)
**Confidence Gain**: 60% → 85-90% (empirically validated)

### Decision Flow

```
┌──────────────────────────────────────────────┐
│  Day 0: Setup Environment                    │
│  - Install Ollama + llava:13b                │
│  - Prepare test fixtures (cards, templates)  │
│  - Manual ground truth annotations           │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│  Days 1-3: Run 4 Validation Experiments      │
│  - Test 1: Heuristic-VLM correlation         │
│  - Test 2: VLM consistency                   │
│  - Test 3: Action space sufficiency          │
│  - Test 4: Template detection accuracy       │
└──────────────────────────────────────────────┘
                    ↓
            DECISION GATE
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
    ALL TESTS PASS        1+ TESTS FAIL
         ↓                     ↓
    ✅ GO: Phase 1       ⚠️ MITIGATE
    (VLM Integration)         ↓
                     Implement Fallback
                              ↓
                      DECISION GATE 2
                              ↓
                     ┌────────┴────────┐
                     ↓                 ↓
                 RESOLVED          STILL FAIL
                     ↓                 ↓
              ✅ GO: Phase 1      ❌ NO-GO
```

---

## Monorepo Integration Analysis

### Existing Structure (from /home/joey/Documents/GitHub/monorepo/agentic/)

**Current Algorithms**:
```
agentic/algorithms/
├── base_algorithm.py          # 4D unified parameter schema
├── algorithm_registry.py      # Discovery system
├── chain_of_thought/
├── react/
├── reflexion/                 # SUPPORTS_ITERATION = True
└── tree_of_thought/
```

**MCTS Will Add**:
```
agentic/algorithms/
└── mcts/                      # NEW
    ├── __init__.py
    ├── mcts_layout.py         # MCTSLayoutAlgorithm
    ├── data_structures.py     # LayoutState, MCTSNode, BoundingBox
    ├── heuristic_evaluator.py # Phase 1 scoring
    ├── vlm_evaluator.py       # Phase 2 scoring
    ├── template_analyzer.py   # Region detection
    └── template_cache.py      # Persistent cache
```

### BaseAlgorithm Pattern (From Actual Code)

**Unified Parameter Schema** (base_algorithm.py:28-32):
```python
class BaseAlgorithm(ABC):
    """4D JUDGE MANDATE: Unified parameter schema
    - max_steps: int = 3      # Iteration control
    - max_depth: int = 1      # Depth control
    - branching_factor: int = 1  # Branch control
    - domain: str = "general"    # Problem domain
    """

    SUPPORTS_ITERATION = True  # Trial-and-error vs internal search

    def __init__(self, name: str = "unknown", **config):
        self.name = name
        self.max_steps = config.get('max_steps', 3)
        self.max_depth = config.get('max_depth', 1)
        self.branching_factor = config.get('branching_factor', 1)
        self.domain = config.get('domain', 'general')
        self.config = config
```

**MCTS Adaptation**:
```python
class MCTSLayoutAlgorithm(BaseAlgorithm):
    """MCTS for MTG card layout optimization"""

    # Internal search strategy - single episode completion
    SUPPORTS_ITERATION = False  # Not trial-and-error like Reflexion

    def __init__(self, name: str = "mcts_layout", **config):
        super().__init__(name, **config)

        # Unified parameters
        # max_steps controls rollout budget: max_steps × 100 = total rollouts
        # max_depth controls MCTS tree depth (default 8 for card layouts)
        # branching_factor is average actions per state (~24)
        # domain = "mtg_layout"

        self.max_rollouts = self.max_steps * 100
        self.instructor = config.get('instructor')
        self.exploration_constant = config.get('exploration_constant', 1.414)

    def execute(self, problem: str, **kwargs) -> Dict[str, Any]:
        """Two-phase execution: heuristic MCTS + VLM validation

        Returns: {'result': Result} with continue_iteration=False (single episode)
        """
        # Phase 1: MCTS with heuristic
        # Phase 2: VLM validates top-5
        # (Implementation from Doc 05)
```

### Existing Test Infrastructure

**Behave Tests** (agentic/tests/components/algorithms/):
```
tests/components/algorithms/
├── reflexion.feature          # Example pattern
├── chain_of_thought.feature
├── tree_of_thought.feature
└── steps/
    ├── reflexion_steps.py
    └── ...
```

**MCTS Will Add**:
```
tests/components/algorithms/
├── mcts_layout.feature        # NEW: Two-phase validation tests
└── steps/
    └── mcts_layout_steps.py   # NEW: Step definitions
```

### PerceptInterface Reality (From Actual Code)

**File**: `/home/joey/Documents/GitHub/monorepo/agentic/core/interfaces/percept_interface.py`

**Actual Implementation** (lines 11-20):
```python
class PerceptInterface:
    """Real percept interface for environmental sensing"""

    def __init__(self, instructor=None):
        self.instructor = instructor
        self.perception_history = []
        self.sensor_types = ["world_state", "visual", "audio", "inventory"]
        self.quality_thresholds = {"visual": 0.7, "world_state": 0.8, "audio": 0.6}
        self.vlm_enabled = False
```

**Key Finding**: PerceptInterface exists but `process_with_vlm()` is incomplete (stub). **Doc 05 resolution to use `instructor` directly is correct.**

---

## Test 1: Heuristic-VLM Correlation

### Claim to Validate

"HeuristicLayoutEvaluator correlates ≥0.7 with VLMLayoutEvaluator scores on diverse MTG card layouts"

### Why Critical

Two-phase evaluation depends on heuristic guiding MCTS toward VLM-optimal regions in Phase 1. If correlation < 0.6, Phase 1 explores wrong areas and Phase 2 VLM rejects all top-5 candidates.

### Test Implementation

**Location**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/validation/test_heuristic_vlm_correlation.py`

**Test Protocol**:
```python
#!/usr/bin/env python3.11
"""
Test 1: Heuristic-VLM Correlation Validation
Duration: 1 day (6-8 hours)
Location: agentic/tests/validation/test_heuristic_vlm_correlation.py
"""

import numpy as np
from scipy.stats import pearsonr
from typing import List, Tuple
import pytest

from agentic.algorithms.mcts.heuristic_evaluator import HeuristicLayoutEvaluator
from agentic.algorithms.mcts.vlm_evaluator import VLMLayoutEvaluator
from agentic.algorithms.mcts.data_structures import LayoutState
from agentic.core.utils.instructor import get_instructor

@pytest.mark.validation
@pytest.mark.slow
def test_heuristic_vlm_correlation():
    """Validate heuristic-VLM correlation ≥0.7

    Success Criteria:
    1. Pearson correlation ≥ 0.7
    2. Top-5 overlap ≥ 60% (3/5 cards)
    3. VLM-optimal in heuristic top-10 for ≥90% cards

    If ANY fails → Two-phase approach INVALID
    """

    # Generate 20 diverse test layouts (5 cards × 4 variations)
    test_layouts = generate_diverse_test_layouts()

    # Initialize evaluators
    heuristic_eval = HeuristicLayoutEvaluator()
    vlm_eval = VLMLayoutEvaluator(instructor=get_instructor('ollama'))

    # Score all layouts with both evaluators
    heuristic_scores = []
    vlm_scores = []

    print("\n=== Scoring 20 Test Layouts ===")
    for i, layout in enumerate(test_layouts):
        h_score = heuristic_eval.evaluate(layout)
        v_score = vlm_eval.score_layout(layout)

        heuristic_scores.append(h_score)
        vlm_scores.append(v_score)

        print(f"Layout {i+1:2d}: Heuristic={h_score:.3f}, VLM={v_score:.3f}, Diff={abs(h_score-v_score):.3f}")

    # Criterion 1: Pearson correlation
    correlation, p_value = pearsonr(heuristic_scores, vlm_scores)
    print(f"\n--- Criterion 1: Correlation ---")
    print(f"Pearson correlation: {correlation:.3f} (target ≥0.7)")
    print(f"P-value: {p_value:.4f}")
    assert correlation >= 0.7, f"❌ FAIL: Correlation {correlation:.3f} < 0.7"
    print("✅ PASS")

    # Criterion 2: Top-5 overlap
    h_top5_indices = set(np.argsort(heuristic_scores)[-5:])
    v_top5_indices = set(np.argsort(vlm_scores)[-5:])
    overlap = len(h_top5_indices & v_top5_indices)
    overlap_pct = overlap / 5 * 100

    print(f"\n--- Criterion 2: Top-5 Overlap ---")
    print(f"Heuristic top-5: {sorted(h_top5_indices)}")
    print(f"VLM top-5: {sorted(v_top5_indices)}")
    print(f"Overlap: {overlap}/5 ({overlap_pct:.0f}%, target ≥60%)")
    assert overlap >= 3, f"❌ FAIL: Overlap {overlap}/5 < 3/5"
    print("✅ PASS")

    # Criterion 3: VLM-optimal in heuristic top-10
    v_optimal_idx = np.argmax(vlm_scores)
    h_top10_indices = set(np.argsort(heuristic_scores)[-10:])

    print(f"\n--- Criterion 3: VLM-Optimal Ranking ---")
    print(f"VLM optimal: Layout {v_optimal_idx} (score={vlm_scores[v_optimal_idx]:.3f})")

    if v_optimal_idx in h_top10_indices:
        h_rank = sorted(np.argsort(heuristic_scores), reverse=True).index(v_optimal_idx) + 1
        print(f"Heuristic rank: #{h_rank} (in top-10)")
        print("✅ PASS")
    else:
        h_rank = sorted(np.argsort(heuristic_scores), reverse=True).index(v_optimal_idx) + 1
        print(f"❌ FAIL: Heuristic rank #{h_rank} (not in top-10)")
        raise AssertionError(f"VLM-optimal not in heuristic top-10")

    print(f"\n{'='*50}")
    print("✅ ALL CRITERIA PASSED - Two-phase approach validated")
    print(f"{'='*50}")

    return {
        'correlation': correlation,
        'p_value': p_value,
        'top5_overlap': overlap,
        'vlm_optimal_rank': h_rank
    }


def generate_diverse_test_layouts() -> List[LayoutState]:
    """Generate 20 test layouts with varying quality

    Returns 5 cards × 4 variations:
    - Variation 1: Good (conventions, no overlap, optimal fonts)
    - Variation 2: Mediocre (minor violations, cramped)
    - Variation 3: Poor (overlaps, bad fonts, wrong alignment)
    - Variation 4: Random (baseline chaos)
    """
    from .fixtures import (
        create_vanilla_creature,
        create_2_ability_creature,
        create_3_ability_planeswalker,
        create_long_text_instant,
        create_flavor_heavy_card
    )

    cards = [
        create_vanilla_creature(),
        create_2_ability_creature(),
        create_3_ability_planeswalker(),
        create_long_text_instant(),
        create_flavor_heavy_card()
    ]

    layouts = []

    for card in cards:
        # Hand-craft 4 layouts per card
        layouts.append(create_good_layout(card))      # Quality ~0.9
        layouts.append(create_mediocre_layout(card))  # Quality ~0.7
        layouts.append(create_poor_layout(card))      # Quality ~0.4
        layouts.append(create_random_layout(card))    # Quality ~0.3

    return layouts  # 20 total layouts
```

### Success Criteria

1. ✅ **Correlation ≥ 0.7**: Heuristic and VLM agree on layout quality
2. ✅ **Top-5 overlap ≥ 60%**: At least 3/5 top candidates match
3. ✅ **VLM-optimal in top-10**: Heuristic doesn't miss the best layout

### Expected Outcome

**Hypothesis**: Correlation will be 0.75-0.85 (good agreement)

**If Passes**: Proceed to Test 2
**If Correlation 0.6-0.7**: ⚠️ Marginal - increase VLM candidates from 5 to 10
**If Correlation < 0.6**: ❌ **STOP** - Two-phase invalid, switch to fallback

### Fallback Options

**Option A: VLM-Only** (if correlation < 0.6):
```python
# Remove heuristic phase entirely
def execute(self, problem, **kwargs):
    # Phase 1: MCTS with VLM scoring (slow but accurate)
    for rollout in range(50):  # Reduce rollouts to compensate
        reward = vlm_evaluator.score_layout(simulation_state)
        # ... MCTS operations ...

    # No Phase 2 needed - already using VLM

    # Performance: 50 rollouts × 0.2s = 10s/card (vs 1.1s)
    # But still meets <60s target with reduced rollouts
```

**Option C: Hybrid** (if correlation 0.6-0.7):
```python
# Use heuristic most of the time, VLM every 10th rollout
def _simulate(self, node, heuristic_eval, vlm_eval, rollout_num):
    # ... complete rollout ...

    if rollout_num % 10 == 0:
        return vlm_eval.score_layout(state)  # Accurate
    else:
        return heuristic_eval.evaluate(state)  # Fast

    # Performance: 90×0.001s + 10×0.2s = 2.1s/card (acceptable)
```

---

## Test 2: VLM Evaluation Consistency

### Claim to Validate

"VLMLayoutEvaluator produces consistent scores (std dev ≤0.05) when evaluating the same layout multiple times"

### Why Critical

MCTS assumes deterministic reward function. If VLM gives 0.85, then 0.72, then 0.91 for the same layout, MCTS tree operations break (backpropagation assumes stable values).

### Test Implementation

**Location**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/validation/test_vlm_consistency.py`

```python
#!/usr/bin/env python3.11
"""
Test 2: VLM Evaluation Consistency
Duration: 0.5 day (3-4 hours)
"""

import numpy as np
import pytest

@pytest.mark.validation
def test_vlm_consistency():
    """Validate VLM score stability

    Success Criteria:
    1. Standard deviation ≤ 0.05
    2. Min-max range ≤ 0.1
    3. No inversions (all within 0.2 of mean)

    If fails → VLM too noisy for MCTS
    """
    from agentic.algorithms.mcts.vlm_evaluator import VLMLayoutEvaluator
    from agentic.core.utils.instructor import get_instructor
    from .fixtures import create_test_layout

    # Create single high-quality test layout
    test_layout = create_test_layout(
        card=create_2_ability_creature(),
        quality='good'  # Should score ~0.8-0.9
    )

    # Evaluate 10 times
    vlm_eval = VLMLayoutEvaluator(instructor=get_instructor('ollama'))
    scores = []

    print("\n=== Evaluating Same Layout 10 Times ===")
    for i in range(10):
        score = vlm_eval.score_layout(test_layout)
        scores.append(score)
        print(f"Evaluation {i+1:2d}: {score:.3f}")

    # Statistics
    mean_score = np.mean(scores)
    std_dev = np.std(scores)
    score_range = max(scores) - min(scores)

    print(f"\n--- Statistics ---")
    print(f"Mean: {mean_score:.3f}")
    print(f"Std Dev: {std_dev:.3f} (target ≤0.05)")
    print(f"Range: {score_range:.3f} (target ≤0.1)")
    print(f"Min: {min(scores):.3f}, Max: {max(scores):.3f}")

    # Criterion 1: Standard deviation
    print(f"\n--- Criterion 1: Std Dev ---")
    assert std_dev <= 0.05, f"❌ FAIL: Std dev {std_dev:.3f} > 0.05"
    print("✅ PASS")

    # Criterion 2: Range
    print(f"\n--- Criterion 2: Range ---")
    assert score_range <= 0.1, f"❌ FAIL: Range {score_range:.3f} > 0.1"
    print("✅ PASS")

    # Criterion 3: No inversions
    print(f"\n--- Criterion 3: No Inversions ---")
    for i, score in enumerate(scores):
        deviation = abs(score - mean_score)
        assert deviation <= 0.2, f"❌ FAIL: Score {i+1} ({score:.3f}) deviates {deviation:.3f} from mean"
    print("✅ PASS")

    print("\n✅ ALL CRITERIA PASSED - VLM consistency validated")

    return {
        'mean': mean_score,
        'std_dev': std_dev,
        'range': score_range
    }
```

### Success Criteria

1. ✅ **Std dev ≤ 0.05**: Scores are stable
2. ✅ **Range ≤ 0.1**: No wild swings
3. ✅ **No inversions**: All within 0.2 of mean

### Expected Outcome

**Hypothesis**: Std dev = 0.03-0.05 (acceptable variance)

**If Passes**: Proceed to Test 3
**If Std Dev 0.05-0.1**: ⚠️ Use median of 3 evaluations
**If Std Dev > 0.1**: ❌ **STOP** - VLM too noisy

### Mitigation

**Set temperature=0.0** (deterministic mode):
```python
vlm_eval = VLMLayoutEvaluator(
    instructor=get_instructor('ollama', temperature=0.0)
)
```

**Or use ensemble voting**:
```python
def score_layout(self, state):
    scores = [self._score_once(state) for _ in range(3)]
    return np.median(scores)  # Robust to outliers
```

---

## Test 3: Action Space Sufficiency

### Claim to Validate

"24 actions per element (via position sampling) finds near-optimal layouts compared to 100-action baseline"

### Why Critical

2,275× action space reduction (54,600 → 24) enables MCTS tractability, but might miss optimal solutions if sampling is too aggressive.

### Test Implementation

**Location**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/validation/test_action_space_sufficiency.py`

```python
#!/usr/bin/env python3.11
"""
Test 3: Action Space Sufficiency
Duration: 1 day (6-8 hours)
"""

import time
import json
import pytest
from typing import List, Dict

@pytest.mark.validation
@pytest.mark.slow
def test_action_space_sufficiency():
    """Compare 24-action vs 100-action MCTS

    Success Criteria:
    1. Quality pass rate ≥ 80% (quality diff ≤0.05)
    2. Time <2s per card
    3. Convergence within rollout budget

    If fails → Need larger action space (48-64 actions)
    """
    from agentic.algorithms.mcts import MCTSLayoutAlgorithm
    from agentic.core.utils.instructor import get_instructor
    from .fixtures import (
        create_vanilla_creature,
        create_1_ability_creature,
        create_2_ability_creature,
        create_3_ability_planeswalker,
        create_long_text_instant,
        create_flavor_heavy_card,
        create_ptless_enchantment,
        create_split_card,
        create_modal_spell,
        create_legendary_creature
    )

    test_cards = [
        create_vanilla_creature(),
        create_1_ability_creature(),
        create_2_ability_creature(),
        create_3_ability_planeswalker(),
        create_long_text_instant(),
        create_flavor_heavy_card(),
        create_ptless_enchantment(),
        create_split_card(),
        create_modal_spell(),
        create_legendary_creature()
    ]

    instructor = get_instructor('ollama')
    results = []

    print("\n=== Comparing Action Spaces ===\n")

    for card in test_cards:
        print(f"Testing: {card['name']}")

        # Baseline: 100 actions (25 positions × 4 configs)
        mcts_baseline = MCTSLayoutAlgorithm(
            max_steps=1,
            action_sampling_n=25,
            instructor=instructor
        )

        start = time.time()
        baseline_result = mcts_baseline.execute(
            problem=json.dumps({'card_data': card}),
            card_data=card,
            template_regions=get_test_template_regions()
        )
        baseline_time = time.time() - start
        baseline_score = baseline_result['result'].data['quality_score']

        # Proposed: 24 actions (8 positions × 3 configs)
        mcts_proposed = MCTSLayoutAlgorithm(
            max_steps=1,
            action_sampling_n=8,
            instructor=instructor
        )

        start = time.time()
        proposed_result = mcts_proposed.execute(
            problem=json.dumps({'card_data': card}),
            card_data=card,
            template_regions=get_test_template_regions()
        )
        proposed_time = time.time() - start
        proposed_score = proposed_result['result'].data['quality_score']

        # Compare
        quality_diff = abs(baseline_score - proposed_score)

        result = {
            'card': card['name'],
            'baseline_score': baseline_score,
            'proposed_score': proposed_score,
            'quality_diff': quality_diff,
            'baseline_time': baseline_time,
            'proposed_time': proposed_time,
            'meets_quality': quality_diff <= 0.05,
            'meets_time': proposed_time < 2.0
        }
        results.append(result)

        status = '✅' if result['meets_quality'] else '❌'
        print(f"  Baseline: {baseline_score:.3f} ({baseline_time:.2f}s)")
        print(f"  Proposed: {proposed_score:.3f} ({proposed_time:.2f}s)")
        print(f"  Diff: {quality_diff:.3f} {status}")
        print()

    # Aggregate
    quality_pass_rate = sum(r['meets_quality'] for r in results) / len(results)
    time_pass_rate = sum(r['meets_time'] for r in results) / len(results)
    avg_quality_diff = np.mean([r['quality_diff'] for r in results])

    print("="*50)
    print(f"Quality Pass Rate: {quality_pass_rate*100:.0f}% (target ≥80%)")
    print(f"Time Pass Rate: {time_pass_rate*100:.0f}% (target 100%)")
    print(f"Avg Quality Diff: {avg_quality_diff:.3f} (target ≤0.05)")
    print("="*50)

    assert quality_pass_rate >= 0.8, f"❌ FAIL: Quality pass rate {quality_pass_rate*100:.0f}% < 80%"
    assert time_pass_rate == 1.0, f"❌ FAIL: {len(results) - sum(r['meets_time'] for r in results)} cards >2s"

    print("\n✅ ALL CRITERIA PASSED - Action space validated")

    return results
```

### Success Criteria

1. ✅ **Quality pass rate ≥ 80%**: 24-action finds near-optimal for most cards
2. ✅ **Time <2s per card**: Meets performance targets
3. ✅ **Convergence**: MCTS terminates within rollout budget

### Expected Outcome

**Hypothesis**: 24 actions sufficient for 90%+ of cards

**If Passes**: Proceed to Test 4
**If Pass Rate 60-80%**: ⚠️ Increase to 48 actions
**If Pass Rate < 60%**: ❌ Need 64-100 actions (larger action space)

### Adaptive Fallback

```python
def _generate_actions_adaptive(self, state):
    """Adaptive action space based on complexity"""
    elem_count = len(state.remaining_elements)

    if elem_count <= 5:  # Simple
        return self._sample_actions(state, n_positions=8)  # 24
    elif elem_count <= 7:  # Medium
        return self._sample_actions(state, n_positions=16)  # 48
    else:  # Complex
        return self._sample_actions(state, n_positions=25)  # 75
```

---

## Test 4: Template Region Detection

### Claim to Validate

"VLM accurately detects text box boundaries in MTG card templates within ±10px of manual annotations"

### Why Critical

Entire layout system depends on knowing where text regions are. If VLM misdetects regions by >20px, element placement will be wrong.

### Test Implementation

**Location**: `/home/joey/Documents/GitHub/monorepo/agentic/tests/validation/test_template_detection.py`

```python
#!/usr/bin/env python3.11
"""
Test 4: VLM Template Region Detection
Duration: 0.5 day (3-4 hours + manual annotation time)
"""

import pytest
import numpy as np

@pytest.mark.validation
def test_template_detection_accuracy():
    """Validate VLM template region detection

    Success Criteria:
    1. Detection rate ≥ 90% (finds all required regions)
    2. Accuracy ≥ 90% (bbox error ≤10px)
    3. No false positives (artwork detected as text)

    If fails → Manual annotation fallback
    """
    from agentic.algorithms.mcts.template_analyzer import VLMTemplateAnalyzer
    from agentic.algorithms.mcts.data_structures import BoundingBox
    from agentic.core.utils.instructor import get_instructor

    # Load manually annotated templates (ground truth)
    templates = load_annotated_templates([
        'modern_creature.png',
        'planeswalker.png',
        'historic_artifact.png',
        'instant_sorcery.png',
        'enchantment.png',
        'legendary_creature.png',
        'multicolor_card.png',
        'colorless_card.png',
        'full_art_land.png',
        'showcase_frame.png'
    ])

    vlm_analyzer = VLMTemplateAnalyzer(instructor=get_instructor('ollama'))

    results = []

    print("\n=== Testing VLM Template Detection ===\n")

    for template_path, ground_truth in templates:
        print(f"Template: {template_path}")

        # VLM detection
        detected = vlm_analyzer.analyze_template(template_path)

        # Compare each region
        for region_name in ground_truth.keys():
            if region_name not in detected.regions:
                print(f"  ❌ Missing: {region_name}")
                results.append({
                    'template': template_path,
                    'region': region_name,
                    'error': float('inf'),
                    'detected': False
                })
                continue

            detected_box = detected.regions[region_name]
            truth_box = ground_truth[region_name]

            # Calculate error (average pixel distance of 4 corners)
            error = bbox_euclidean_error(detected_box, truth_box)

            results.append({
                'template': template_path,
                'region': region_name,
                'error': error,
                'detected': True,
                'within_tolerance': error <= 10
            })

            status = '✅' if error <= 10 else '❌'
            print(f"  {status} {region_name}: {error:.1f}px")

        print()

    # Aggregate
    detection_rate = sum(r['detected'] for r in results) / len(results)
    detected_results = [r for r in results if r['detected']]
    accuracy_rate = sum(r['within_tolerance'] for r in detected_results) / len(detected_results)
    avg_error = np.mean([r['error'] for r in detected_results])

    print("="*50)
    print(f"Detection Rate: {detection_rate*100:.0f}% (target 100%)")
    print(f"Accuracy Rate: {accuracy_rate*100:.0f}% (target ≥90%)")
    print(f"Avg Error: {avg_error:.1f}px (target ≤10px)")
    print("="*50)

    assert detection_rate >= 0.9, f"❌ FAIL: Detection {detection_rate*100:.0f}% < 90%"
    assert accuracy_rate >= 0.9, f"❌ FAIL: Accuracy {accuracy_rate*100:.0f}% < 90%"

    print("\n✅ ALL CRITERIA PASSED - Template detection validated")

    return results


def bbox_euclidean_error(detected: BoundingBox, truth: BoundingBox) -> float:
    """Average pixel distance of 4 corners"""
    errors = [
        abs(detected.x - truth.x),
        abs(detected.y - truth.y),
        abs((detected.x + detected.width) - (truth.x + truth.width)),
        abs((detected.y + detected.height) - (truth.y + truth.height))
    ]
    return np.mean(errors)
```

### Manual Annotation Required

**Tool**: Simple GUI for clicking boundaries

```bash
# Create manual annotations (one-time, 4 hours)
python scripts/annotate_template.py templates/modern_creature.png
# Opens image, click 4 corners of each region, saves JSON

# Output: templates/modern_creature_regions.json
{
  "name_box": {"x": 50, "y": 30, "width": 650, "height": 30},
  "mana_cost_box": {"x": 680, "y": 30, "width": 40, "height": 40},
  "type_line_box": {"x": 50, "y": 310, "width": 650, "height": 25},
  "text_box_1": {"x": 50, "y": 350, "width": 650, "height": 400},
  "pt_box": {"x": 650, "y": 980, "width": 70, "height": 50}
}
```

### Success Criteria

1. ✅ **Detection ≥ 90%**: VLM finds all required regions
2. ✅ **Accuracy ≥ 90%**: Bounding boxes within ±10px
3. ✅ **No false positives**: Artwork not detected as text

### Expected Outcome

**Hypothesis**: VLM detects regions within 5-10px accuracy

**If Passes**: Phase 0 complete ✅
**If Accuracy 70-90%**: ⚠️ Acceptable with ±20px tolerance
**If Accuracy < 70%**: ❌ Use manual annotations (4 hours one-time)

---

## Implementation Timeline

### Realistic Estimate: 18-22 Days

**Revised from original 9 days (too optimistic) and adversarial 25 days (too conservative)**

| Phase | Duration | Tasks | Deliverable |
|-------|----------|-------|-------------|
| **Phase 0** | **3 days** | **Validation experiments** | **Test reports** |
| Phase 1 | 2 days | VLM + instructor setup | Ollama working |
| Phase 2 | 6 days | MCTS + evaluators + text utils | Algorithm complete |
| Phase 3 | 2 days | Behave tests | Tests passing |
| Phase 4 | 1 day | Grid world validation | MCTS validated |
| Phase 5 | 4 days | Hellcube integration | 200 proxies |
| **Base Total** | **18 days** | **Core implementation** | |
| Contingency | +4 days | 20% risk buffer | |
| **With Buffer** | **22 days** | **Conservative estimate** | **Production ready** |

### Week-by-Week Breakdown

**Week 1**:
- Days 1-3: **Phase 0 validation** (this document)
- Days 4-5: Phase 1 (VLM setup)

**Week 2**:
- Days 6-11: Phase 2 (MCTS implementation)
  - Days 6-7: Core algorithm
  - Days 8-9: Heuristic + VLM evaluators
  - Days 10-11: Text wrapping + mana symbols
- Days 12-13: Phase 3 (Behave tests)

**Week 3**:
- Day 14: Phase 4 (Grid world)
- Days 15-18: Phase 5 (Integration)
  - Days 15-16: Excel parser
  - Day 17: Template matching
  - Day 18: End-to-end testing

**Week 4** (if needed):
- Days 19-22: Contingency buffer

---

## Decision Gate

### Go Decision Criteria (After Phase 0)

✅ **PROCEED to Phase 1** if ALL of:

1. ✅ Test 1: Heuristic-VLM correlation ≥ 0.7
2. ✅ Test 2: VLM consistency std dev ≤ 0.05
3. ✅ Test 3: Action space pass rate ≥ 80%
4. ✅ Test 4: Template detection accuracy ≥ 90%

### Contingency Matrix

| Test | Failure | Mitigation | Timeline Impact |
|------|---------|------------|-----------------|
| Test 1 | Correlation < 0.7 | VLM-only or hybrid | +2 days (redesign) |
| Test 2 | Std dev > 0.05 | Temperature=0 or ensemble | +1 day (rework) |
| Test 3 | Pass rate < 80% | Increase to 48 actions | +0.5 day (adjust) |
| Test 4 | Accuracy < 90% | Manual annotation | +0.5 day (annotate) |

### No-Go Triggers

❌ **STOP implementation** if:

1. Test 1 correlation < 0.6 (two-phase fundamentally broken)
2. Test 2 std dev > 0.1 (VLM too noisy for MCTS)
3. Test 3 pass rate < 60% (action space too small)
4. Test 4 accuracy < 70% AND manual annotation not feasible

### Confidence Levels

- **Before Phase 0**: 60% confidence (untested assumptions)
- **After Phase 0**: 85-90% confidence (empirically validated)
- **After Phase 2**: 95% confidence (MCTS implemented, tests passing)

---

## Next Steps

### Immediate Actions (Today)

1. ✅ **Review this document** (Phase 0 Validation Plan)
2. ✅ **Approve 3-day validation budget**
3. ✅ **Commit to 18-22 day timeline** (not 9 days)

### Short-Term (This Week)

**Day 0 Setup**:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh
ollama pull llava:13b

# Verify installation
ollama list | grep llava

# Clone monorepo
cd /home/joey/Documents/GitHub/monorepo

# Set backend
export BACKEND=ollama

# Create validation test directory
mkdir -p agentic/tests/validation
mkdir -p agentic/tests/validation/fixtures
```

**Prepare Test Fixtures**:
1. Manually create 5 diverse test cards (JSON)
2. Download 10 MTG card templates (various styles)
3. Manually annotate template regions (ground truth) - 4 hours

**Days 1-3: Run Phase 0 Experiments**:
```bash
# Day 1: Test 1 - Heuristic-VLM correlation
cd /home/joey/Documents/GitHub/monorepo
BACKEND=ollama pytest agentic/tests/validation/test_heuristic_vlm_correlation.py -v

# Day 2 AM: Test 2 - VLM consistency
BACKEND=ollama pytest agentic/tests/validation/test_vlm_consistency.py -v

# Day 2 PM: Test 3 - Action space (baseline runs)
BACKEND=ollama pytest agentic/tests/validation/test_action_space_sufficiency.py -v --durations=0

# Day 3 AM: Test 3 - Action space (comparison analysis)
python agentic/tests/validation/analyze_action_space_results.py

# Day 3 PM: Test 4 - Template detection
BACKEND=ollama pytest agentic/tests/validation/test_template_detection.py -v
```

### Decision Point (End of Week 1)

**Review Phase 0 Results**:
- Examine test reports
- Check all 4 tests passed
- Review any mitigations needed

**Make Go/No-Go Decision**:
- ✅ All pass → Proceed to Phase 1 (VLM integration)
- ⚠️ 1-2 fail → Implement mitigation, reassess
- ❌ 3+ fail → NO-GO, redesign approach

---

## Document Status

**Status**: ✅ Phase 0 Validation Plan Complete
**Timeline**: 3 days validation → Decision Gate → 15 days implementation = **18 days total**
**Confidence**: 85-90% (after Phase 0 validation)
**Recommendation**: **CONDITIONAL GO** - Run Phase 0 validation first, then decide

**Next Document**: Phase 0 Test Results (after validation experiments complete)

---

🔬 **Let's validate assumptions with experiments, not debate!**
