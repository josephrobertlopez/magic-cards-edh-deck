# Problem Statement & Design Rationale
## MCTS Layout Optimization for Hellcube Proxy Generator

**Document**: 01-Problem-And-Design-Rationale.md
**Version**: 1.0.0
**Created**: 2025-11-15
**Related**: [spec.md](./spec.md), [plan.md](./plan.md)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Why MCTS?](#why-mcts)
4. [Current Codebase State](#current-codebase-state)
5. [Design Decisions](#design-decisions)
6. [Architecture Principles](#architecture-principles)

---

## Executive Summary

**Hellcube Proxy Generator (Feature 012)** generates print-ready MTG proxy cards from unstructured Excel data. The core technical challenge is **optimal layout positioning** of variable card elements (1-3 text boxes, power/toughness, flavor text) on templates with dynamically detected boundaries.

**Key Innovation**: Monte Carlo Tree Search (MCTS) combined with Vision Language Model (VLM) evaluation to explore layout combinations and achieve optimal readability while maintaining MTG convention compliance.

**Why This Matters**:
- Traditional fixed-coordinate approaches fail with variable card structures
- Heuristic-based placement produces suboptimal readability
- VLM-based region detection enables dynamic template adaptation
- MCTS explores the combinatorial space efficiently

**Performance Targets**:
- MCTS convergence: <2 seconds per card
- Batch processing: 200+ cards in <5 minutes
- Layout quality: ≥0.8 score for 95%+ of cards
- Cost efficiency: Zero API costs via Ollama local VLM

---

## Problem Statement

### The Core Challenge

**Optimally position variable MTG card elements on card templates with dynamically detected boundaries to maximize readability and MTG convention compliance.**

This is fundamentally a **constrained optimization problem** in a high-dimensional search space:

#### Search Space Complexity

- **Positioning decisions**: 5-8 elements per card
- **Coordinate space**: Continuous 2D positioning (750×1050 pixels)
- **Font size decisions**: 8-20pt range per element
- **Alignment choices**: Left/center/right per element
- **Combinatorial explosion**: ~10²⁰ possible configurations per card

**Example calculation** for a card with 7 elements:
```
Positions: 750 × 1050 = 787,500 per element
Font sizes: 13 choices (8-20pt)
Alignment: 3 choices (left/center/right)

Per element: 787,500 × 13 × 3 = 30,712,500 states
7 elements: 30,712,500^7 ≈ 6.5 × 10^52 total states
```

This is computationally intractable to exhaustively search.

#### Constraints

**Hard Constraints** (must satisfy):
- Elements must fit within VLM-detected template region boundaries
- No text overlap between elements
- Minimum font size for readability (8pt minimum)
- Maximum font size to prevent template overflow
- Power/toughness only for creature cards

**Soft Constraints** (optimize for):
- MTG convention compliance (name centered, abilities left-aligned, etc.)
- Aesthetic balance (even spacing, visual hierarchy)
- Text readability (adequate whitespace, appropriate font sizing)

#### Objective Function

Multi-criteria optimization scored by VLM:

```python
quality_score = weighted_sum([
    readability_score,        # Text legibility, font sizing
    convention_compliance,    # MTG standard layout patterns
    aesthetic_balance,        # Visual harmony, spacing
])
```

Each criterion is evaluated on 0.0-1.0 scale, target overall score ≥0.8.

#### Variable Structure

Unlike fixed-layout problems, each card has different element combinations:

**Example Card A** (Simple Creature):
```
- Card name
- Mana cost
- Type line
- Ability text (1 box)
- Power/Toughness
Total: 5 elements
```

**Example Card B** (Complex Planeswalker):
```
- Card name
- Mana cost
- Type line
- Loyalty ability 1
- Loyalty ability 2
- Loyalty ability 3
- Flavor text
Total: 7 elements
```

**Example Card C** (Vanilla Creature with Flavor):
```
- Card name
- Mana cost
- Type line
- Flavor text
- Power/Toughness
Total: 5 elements (but different structure than Card A)
```

A fixed heuristic cannot handle this variability optimally.

---

## Why MCTS?

### Sequential Decision Structure

Layout positioning has natural **sequential dependencies**:

```
Place card name
  ↓ (constrains position of mana cost)
Place mana cost
  ↓ (constrains type line position)
Place type line
  ↓ (constrains ability text region)
Place ability 1
  ↓ (constrains ability 2 if exists)
Place ability 2 (if exists)
  ↓ (constrains ability 3 if exists)
Place ability 3 (if exists)
  ↓ (constrains P/T region)
Place P/T (if creature)
  ↓ (constrains remaining space for flavor)
Place flavor text (if exists)
```

Each placement decision reduces the action space for subsequent decisions. This forms a **decision tree** - exactly what MCTS is designed to explore.

### MCTS Algorithm Advantages

**1. Handles Delayed Evaluation**

Layout quality cannot be assessed until all elements are placed. MCTS addresses this through:

- **Rollout simulation**: Randomly complete partial layouts to terminal state
- **VLM evaluation**: Score completed layouts for quality
- **Backpropagation**: Update statistics for partial placements based on final outcomes

This allows MCTS to learn which early decisions lead to high-quality final layouts.

**2. Exploration vs Exploitation Trade-off**

UCB1 (Upper Confidence Bound) selection balances:

```python
UCB1(node) = average_reward(node) + C × sqrt(ln(parent_visits) / node_visits)
                    ↑                              ↑
              Exploitation                    Exploration
```

- **Exploitation**: Choose placements with proven high average rewards
- **Exploration**: Try underexplored placements that might be better
- **Convergence**: Automatically focuses on best regions as rollouts increase

With C=1.414 (√2), the algorithm converges to optimal solutions.

**3. Adapts to Variable Structure**

MCTS naturally handles cards with different element counts:

- **1 ability**: Tree depth = 6 (name, cost, type, ability, P/T, flavor)
- **3 abilities**: Tree depth = 8 (name, cost, type, ability×3, P/T, flavor)

The algorithm doesn't need special cases - it explores whatever action space exists for the current card.

**4. Efficient Search**

MCTS focuses computational effort on promising regions:

- Poor placements get few visits (low UCB1 scores)
- Good placements get many visits (exploration refines them)
- Result: 100 rollouts can find near-optimal solutions in 10²⁰ space

### Why Not Simple Heuristics?

**Heuristic approach**: "Place name centered, mana cost top-right, type line below name, abilities stacked vertically..."

**Failure Case 1 - Long Ability Text**:
```
Card with single 8-line ability:
- Heuristic: Place in first text box, shrink to 8pt font → UNREADABLE
- MCTS: Explore splitting across 2-3 boxes, use 10pt font → READABLE
```

**Failure Case 2 - Three Short Abilities**:
```
Card with three 1-line abilities:
- Heuristic: Stack in 3 separate boxes → WASTED SPACE
- MCTS: Group in single box with good spacing → BALANCED
```

**Failure Case 3 - Flavor Text Priority**:
```
Card with 2 abilities + flavor:
- Heuristic: Abilities first, flavor at bottom → CRAMPED FLAVOR
- MCTS: Flavor in middle if abilities are short → AESTHETIC BALANCE
```

MCTS **discovers these nuances** through exploration. Heuristics **cannot** without hardcoded special cases for every edge case.

### MCTS vs Other Algorithms

**Why not Genetic Algorithm (GA)?**
- GA requires crossover/mutation operators for "partial layouts" - not well-defined
- MCTS naturally builds partial solutions incrementally
- MCTS converges faster on sequential decision problems

**Why not Deep Reinforcement Learning (DRL)?**
- DRL requires 10,000+ training examples to learn layout policy
- MCTS works zero-shot on new card types
- Training overhead not justified for 200-card batch

**Why not Simulated Annealing (SA)?**
- SA explores by random perturbations of complete layouts
- MCTS explores structured decision tree
- MCTS has better sample efficiency (fewer evaluations to converge)

### Contrast with Folder Organization

**Folder organization** (color-first vs type-first) **IS** a simple heuristic problem:

**Why?**
- **Binary choice**: Multiple organizational strategies
- **Simple evaluation**: Count card distribution, compute once
- **No sequential dependencies**: Grouping choice doesn't affect card content
- **Closed-form solution**: Multi-strategy voting on distribution patterns

**Example**:
```python
cards_by_color = count_cards_per_color(cards)
cards_by_type = count_cards_per_type(cards)

if max(cards_by_color.values()) > 0.7 * total:
    strategy = "color-first"  # 70%+ single color → color grouping
else:
    strategy = "type-first"   # Balanced → type grouping
```

**Layout optimization** requires MCTS because:
- **Combinatorial choices**: 10²⁰ position combinations
- **Complex evaluation**: VLM-based quality scoring, multi-criteria
- **Sequential dependencies**: Each placement constrains subsequent placements
- **No closed form**: Must explore via rollout simulation

---

## Current Codebase State

### Magic Cards EDH Deck Repository

**Location**: `/home/joey/Documents/GitHub/magic-cards-edh-deck`

**Architecture**: A2A Orchestrator framework with domain-agnostic skills

#### Key Components

```
a2a_orchestrator/
├── orchestrator.py           # Main orchestration engine (600 LOC)
│   - Workflow execution coordinator
│   - Skill discovery and registration
│   - Error handling and retry logic
│
├── workflow_skill.py         # YAML workflow execution (400 LOC)
│   - Declarative workflow definitions
│   - Variable substitution
│   - Output aliasing
│
├── batch_processor.py        # Parallel batch processing (350 LOC)
│   - Feature 010: Async execution
│   - Configurable batch_size, max_concurrent
│   - Exponential backoff retry policy
│
├── execution_manifest.py     # Execution tracking (200 LOC)
│   - JSON-based execution logs
│   - Input/output capturing
│   - Timing metrics
│
├── retry_policy.py           # Retry strategies (150 LOC)
│   - ExponentialBackoff
│   - FixedDelay
│   - Circuit breaker pattern
│
├── skill_contract.py         # Skill protocol definitions (100 LOC)
│   - BaseSkill interface
│   - Input/output schemas
│   - Validation rules
│
└── skills/                   # Domain-agnostic skills
    ├── html_extractor_skill.py      # CSS selector extraction
    ├── web_fetcher_skill.py         # HTTP requests
    ├── data_fetcher_skill.py        # JSON API calls
    └── document_generator_skill.py  # PPTX/PDF generation
```

#### Testing Infrastructure

```
tests/
├── unit/                     # pytest unit tests (35 files)
│   ├── test_orchestrator.py
│   ├── test_batch_processor.py
│   ├── test_retry_policy.py
│   └── ...
│
├── integration/              # Integration tests (12 files)
│   ├── test_workflow_execution.py
│   ├── test_variable_substitution.py
│   ├── test_error_handling.py
│   └── ...
│
├── e2e/                      # End-to-end tests (3 files)
│   ├── test_proxy_pipeline.py
│   ├── test_domain_agnostic.py
│   └── ...
│
└── features/                 # behave BDD tests (15 features)
    ├── batch_processing.feature
    ├── html_extract_css.feature
    ├── http_fetch_json.feature
    └── steps/
        ├── batch_processing_steps.py
        ├── html_extract_css_steps.py
        └── ...
```

**Test Coverage**: 97% (Feature 010 delivered with comprehensive tests)

#### Relevant Features

**Feature 010: Parallel Batch Processing**
- Async execution with configurable concurrency
- Rate limiting with exponential backoff
- Successfully processes 200+ items in <2 minutes
- **Directly applicable** to MCTS batch proxy generation

**Feature 007: Protocol-First Refactoring**
- JSON schemas for all skill inputs/outputs
- Runtime validation with pydantic
- **Pattern to follow** for MCTS layout output schemas

**Feature 003: A2A Orchestration**
- YAML workflow composition
- Skill chaining with data flow
- **Framework for** integrating MCTS as a skill

#### Current Gaps

**Missing Capabilities** (required for Feature 012):
- ❌ **No MCTS algorithm implementation** - Need to import from monorepo
- ❌ **No VLM integration** - Need PerceptInterface + Ollama backend
- ❌ **No layout optimization** - Core feature requirement
- ❌ **No image analysis** - VLM template region detection needed
- ❌ **No semantic spreadsheet parser** - Excel parsing with adjacency detection

**Existing Capabilities** (leverage for Feature 012):
- ✅ **Batch processing infrastructure** - Feature 010 handles 200+ cards
- ✅ **Skill-based architecture** - Extensible for new MCTS skill
- ✅ **HTTP skills** - Template downloading from web sources
- ✅ **Document generation** - PPTX/PDF output (adapt for PNG proxies)
- ✅ **Testing framework** - behave BDD + pytest ready

---

## Design Decisions

### Decision 1: MCTS vs Heuristics

**Decision**: Use MCTS for layout optimization, NOT simple top-to-bottom heuristic

**Rationale**:
- Heuristic fails on variable structures (1-3 text boxes)
- MCTS explores combinatorial space efficiently
- VLM evaluation provides ground truth for quality
- Convergence in <2s per card is achievable (100 rollouts)

**Trade-offs**:
- **Complexity**: MCTS is more complex than heuristic (300 LOC vs 50 LOC)
- **Compute**: 100 VLM calls per card vs 0 for heuristic
- **Benefits**: Optimal layouts, handles edge cases, no hardcoded rules

**Mitigation**: Use Ollama local VLM (zero API cost), parallelize across cards

### Decision 2: VLM for Region Detection

**Decision**: Use VLM to detect template regions dynamically, NOT hardcoded coordinates

**Rationale**:
- Templates have varying dimensions and styles
- VLM adapts to any template automatically
- Eliminates manual coordinate measurement per template
- Robust to template variations (historic vs modern frames)

**Trade-offs**:
- **One-time cost**: VLM analysis per template (~50 templates × 2s = 100s setup)
- **Dependency**: Requires Ollama + VLM model installed
- **Benefits**: Zero manual work, handles 50+ template types, future-proof

**Mitigation**: Cache VLM region analysis (one-time per template), fail gracefully to heuristic if VLM unavailable

### Decision 3: Ollama Local VLM

**Decision**: Use Ollama local VLM backend, NOT cloud API (Claude/GPT-4V)

**Rationale**:
- **Cost**: 20,000 VLM calls (100 rollouts × 200 cards) = $200+ on cloud
- **Speed**: Local inference faster than API round-trips (0.2s vs 1-2s)
- **Privacy**: Card data stays local
- **Reliability**: No rate limits or API downtime

**Trade-offs**:
- **Setup**: User must install Ollama + download llava-1.5 model (~4GB)
- **Quality**: Local VLM slightly less accurate than GPT-4V
- **Benefits**: Free, fast, private, reliable

**Mitigation**: Document Ollama setup in quickstart.md, provide fallback heuristic scoring

### Decision 4: Follow Reflexion Template Pattern

**Decision**: Implement MCTSLayoutAlgorithm following monorepo Reflexion algorithm structure

**Rationale**:
- **Consistency**: Matches existing algorithm patterns
- **Integration**: Works with algorithm registry, discovery system
- **Testing**: Follows behave BDD testing conventions
- **Maintainability**: Familiar structure for future developers

**Pattern Requirements**:
- Inherit from `BaseAlgorithm`
- Support unified parameters (`max_steps`, `max_depth`, `branching_factor`, `domain`)
- Stateless execution with `iteration_context` support
- Instructor-based structured output generation
- Behave tests with step definitions

**Benefits**: Drop-in replacement for other algorithms, protocol compliance, testable

### Decision 5: Incremental Testing Strategy

**Decision**: Validate in 5 phases (VLM+Reflexion → MCTS → Behave → Grid World → Excel)

**Rationale**:
- **Fast feedback**: Validate infrastructure before full implementation
- **Risk mitigation**: Test on simple domains (grid world) before production
- **Tractability check**: Ensure VLM+MCTS integration works early

**Phases**:
1. VLM + Reflexion integration test (validate plumbing)
2. MCTS algorithm implementation (core logic)
3. MCTS behave tests (audit correctness)
4. Grid world test (validate on known-good problem)
5. Excel integration (production use case)

**Benefits**: Early failure detection, confidence in approach, debuggable increments

---

## Architecture Principles

### Principle 1: Protocol-First Design

**All components communicate via well-defined protocols:**

- **MCTS Input Protocol**: JSON schema for card data + template regions
- **MCTS Output Protocol**: JSON schema for layout state + quality score
- **VLM Input Protocol**: Image path + detection schema (TemplateRegions)
- **VLM Output Protocol**: Pydantic BaseModel with bounding boxes

**Benefits**: Runtime validation, composability, testability, documentation

### Principle 2: Stateless Execution

**MCTS algorithm is a pure function:**

```python
def execute(problem: str, **kwargs) -> Dict[str, Any]:
    # No instance state modification
    # All inputs from problem/kwargs
    # All outputs in return dict
    # Reproducible given same inputs
```

**Benefits**: No hidden dependencies, parallelizable, testable, cacheable

### Principle 3: Graceful Degradation

**System works even when optional dependencies unavailable:**

- **VLM unavailable**: Fall back to heuristic region detection
- **MCTS fails**: Fall back to top-to-bottom placement heuristic
- **Template download fails**: Use placeholder template with solid color

**Benefits**: Robustness, development without Ollama, testing without VLM

### Principle 4: Instructor-Based Structured Output

**All LLM/VLM calls use instructor for type safety:**

```python
class TemplateRegions(BaseModel):
    name_box: BoundingBox
    mana_cost_box: BoundingBox
    text_boxes: List[BoundingBox]
    # Pydantic validates at runtime

result = instructor.generate_structured(
    prompt="Detect text regions...",
    response_model=TemplateRegions  # Type-safe!
)
```

**Benefits**: Runtime type checking, validation, IDE autocomplete, self-documenting

### Principle 5: Backend Agnostic

**MCTS works with any backend (claude_code/ollama/test):**

```python
backend = get_backend()  # From environment variable
instructor = get_instructor(backend)

# MCTS doesn't care which backend
mcts = MCTSLayoutAlgorithm(instructor=instructor)
```

**Benefits**: Testing with mock backend, swapping VLM models, cloud/local hybrid

---

## Next Steps

This document establishes the **problem**, **rationale**, and **principles**. Continue to:

- **[02-Monorepo-Code-Structure.md](./02-Monorepo-Code-Structure.md)**: Deep dive into monorepo algorithm patterns
- **[03-MCTS-Implementation-Spec.md](./03-MCTS-Implementation-Spec.md)**: Detailed MCTS algorithm specification
- **[04-Testing-Integration-Deployment.md](./04-Testing-Integration-Deployment.md)**: Testing strategy and deployment

---

**Document Status**: ✅ Complete
**Last Updated**: 2025-11-15
**Next Review**: After Phase 1 VLM+Reflexion integration test
