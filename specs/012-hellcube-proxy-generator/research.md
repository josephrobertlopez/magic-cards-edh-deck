# Research & Technical Decisions

**Feature**: 012 Hellcube Proxy Generator
**Phase**: 0 (Research & Unknowns Resolution)
**Date**: 2025-11-16
**Status**: Complete (findings consolidated from Documents 01-09)

---

## Overview

This document consolidates all technical research performed for the Hellcube Proxy Generator feature. All "NEEDS CLARIFICATION" items from the initial planning phase have been resolved through comprehensive design documentation (Documents 01-09) and user clarifications.

---

## Decision 1: MCTS Layout Optimization Algorithm

**Decision**: Use Monte Carlo Tree Search (MCTS) with VLM-guided evaluation for card element placement optimization

**Rationale**:
- **Problem Complexity**: MTG card layout has ~10²⁰ possible configurations due to:
  - Continuous 2D positioning (750×1050 pixel space)
  - Font size variations (8-20pt)
  - Alignment choices (left/center/right)
  - Variable element combinations (1-3 abilities, optional flavor text)

- **Sequential Dependencies**: Layout decisions have natural ordering:
  1. Name → 2. Mana cost → 3. Type line → 4. Abilities → 5. P/T → 6. Flavor

- **Delayed Evaluation**: Layout quality can only be assessed when complete (VLM evaluates entire card, not partial placements)

- **Academic Rigor**: Follows canonical MCTS from:
  - Browne et al. (2012) "A Survey of Monte Carlo Tree Search Methods"
  - Kocsis & Szepesvári (2006) "Bandit based Monte-Carlo Planning" (UCB1 algorithm)

**Alternatives Considered**:
1. **Simple Heuristics** (top-to-bottom placement with fixed positions)
   - **Rejected**: Fails on edge cases (long text, unusual ability combinations)
   - Example failure: 3 long abilities may overflow fixed text_box_1 position

2. **Genetic Algorithms**
   - **Rejected**: Poor fit for sequential decision problems (population-based, not tree-based)
   - Mutation/crossover don't leverage sequential structure

3. **Deep Reinforcement Learning** (PPO, DQN)
   - **Rejected**: Requires 10,000+ training examples (overhead not justified for 200-card dataset)
   - No existing MTG layout dataset available

4. **Simulated Annealing**
   - **Rejected**: Less sample-efficient than MCTS for discrete action spaces
   - No exploitation/exploration balance mechanism

**Source**: Document 01 (Problem-And-Design-Rationale.md)

---

## Decision 2: VLM Evaluation Strategy

**Decision**: Call VLM to evaluate layout quality on **every MCTS rollout** (100-300 VLM calls per card)

**Rationale**:
- **User-Driven**: User explicitly chose this strategy in clarification (Session 2025-11-16)
- **Quality Priority**: Prioritizes maximum layout quality over processing speed
- **UCB1 Gradient**: Provides accurate reward signal for MCTS tree exploration
- **Performance**: 0.2s per VLM call × 300 calls = 60s per card → 1-3 hours for 200 cards (acceptable)

**Alternatives Considered**:
1. **Two-Phase Evaluation** (heuristic MCTS + VLM top-5 validation)
   - **Rejected by user**: Would reduce to 1.1s per card (5 VLM calls only)
   - Trades quality for speed - user chose quality

2. **Heuristic-Only Scoring** (no VLM)
   - **Rejected**: Cannot assess aesthetic balance or MTG convention compliance
   - Heuristics (overlap detection, region bounds) insufficient for professional output

3. **VLM Every Nth Rollout** (e.g., N=10, reducing calls by 90%)
   - **Rejected**: Sparse rewards degrade UCB1 tree exploration quality

**Performance Impact**:
- Per card: 20-60 seconds (depending on convergence)
- 200-card batch: 1-3 hours total
- Zero API costs (local Ollama VLM)

**Source**: Documents 05 (Critical-Issues-Resolution.md), Clarification Session 2025-11-16

---

## Decision 3: Action Space Reduction via Strategic Sampling

**Decision**: Use strategic position sampling (8 positions) + element-specific constraints to reduce action space from ~49,140 to ~24 actions per element

**Rationale**:
- **Tractability**: Full enumeration creates combinatorial explosion:
  - Example text_box region (650×360px):
    - Positions: (650/10) × (360/10) = 65 × 36 = 2,340 grid points
    - Font sizes: 7 options [8, 10, 12, 14, 16, 18, 20]
    - Alignments: 3 options [left, center, right]
    - **Total**: 2,340 × 7 × 3 = **49,140 actions**
  - 8 elements × 49,140 actions = ~400,000 total actions → 50M node MCTS trees (intractable)

- **Strategic Sampling**: 8 positions per region:
  - 4 corners: (x, y), (x+w, y), (x, y+h), (x+w, y+h)
  - 4 midpoints: top-center, bottom-center, left-center, right-center
  - Optional: 1-2 random positions for exploration

- **Element-Specific Constraints**:
  - Name: center alignment only, 1-2 font sizes [14, 16]
  - Mana cost: right alignment only, fixed font [14]
  - Type line: center alignment only, 1 font size [12]
  - Abilities: left alignment only, 2-3 font sizes [10, 11, 12]
  - P/T: right alignment only, fixed font [14]
  - Flavor: left alignment only, 1 font size [10]

- **Result**: 8 positions × 3 font sizes × 1 alignment = **24 actions per element** (2,275× reduction)

**Alternatives Considered**:
1. **Full 10px Grid Enumeration**
   - **Rejected**: Intractable (49,140 actions/element)

2. **Coarse 50px Grid** (300 actions/element)
   - **Rejected**: Loses precision for fine-tuning text placement

3. **Adaptive Refinement** (start coarse, refine promising regions)
   - **Rejected**: Adds complexity, unclear benefit vs strategic sampling

**Source**: Document 05 (Critical-Issues-Resolution.md), Clarification Session 2025-11-16

---

## Decision 4: VLM Backend and Integration

**Decision**: Use Ollama (local) + llava-1.5 model for VLM backend, integrated via instructor framework

**Rationale**:
- **Zero API Costs**: Local inference eliminates cloud API expenses
- **Privacy**: Card data stays local (no external API calls)
- **Fast Inference**: 0.2s per VLM call (acceptable for 100-300 calls/card)
- **Proven Integration**: Existing monorepo already uses instructor + Ollama backend

**Setup Requirements**:
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Download model: `ollama pull llava:13b` (~4GB)
3. Run server: `ollama serve` (runs on localhost:11434)

**Integration Pattern**:
```python
# Template region detection (one-time per template)
regions = instructor.generate_structured(
    prompt="Detect MTG card template regions...",
    response_model=TemplateRegions,
    image_path=template_path
)

# Layout quality scoring (per rollout)
quality = instructor.generate_structured(
    prompt="Evaluate MTG card layout quality...",
    response_model=LayoutQuality,
    image_data=rendered_layout
)
```

**Alternatives Considered**:
1. **Claude Code MCP** (cloud API)
   - **Rejected**: API costs ($$$), slower inference (1-2s vs 0.2s)

2. **GPT-4 Vision** (OpenAI API)
   - **Rejected**: Similar issues to Claude (cost, latency, privacy)

3. **Custom CNN** (trained template detector)
   - **Rejected**: Requires training data, no flexibility for layout scoring

**Source**: Documents 07 (Phase-0-Validation.md), 09 (Card-Template-Analysis.md)

---

## Decision 5: Excel Parsing Strategy

**Decision**: Multi-column vertical parsing with dynamic adjacency detection for field label→value matching

**Rationale**:
- **Real Data Structure** (from actual Hellcube AJ.xlsx):
  - 4 cards per row (columns C, D, E, F)
  - Vertical field labels in Column A: "name bULK", "pic", "Types", "text", "flavor", "Stats"
  - "AJ" markers indicate card start
  - Field values in cells adjacent to labels (with potential positional offset)

- **Dynamic Adjacency**: Field values don't have fixed row offsets from labels
  - Example: "Types" label in A15 → value in C15 (same row)
  - Example: "text" label in A16 → value in C16, C17, C18 (multiple rows)

- **Mana Cost Parsing**: Extract from parenthetical notation in card name
  - Example: "Batman Blue (Bu,Bu)(1)" → name="Batman Blue", mana_cost=[(Bu, 2), (Generic, 1)]
  - Symbol mapping: Bu→Blue, Rd→Red, Gn→Green, Wt→White, Bk→Black, Cl→Colorless

**Implementation**:
```python
class HellcubeExcelParser:
    def _extract_card(self, col_idx, start_row):
        # Use Column A labels to identify fields
        for row_idx in range(start_row, next_aj_marker):
            label = str(worksheet.cell(row_idx, 1).value).strip()
            value = worksheet.cell(row_idx, col_idx).value

            if label == "Types":
                card['types'] = str(value).strip()
            elif label == "text":
                if pd.notna(value):
                    card['abilities'].append(str(value).strip())
            # ... etc
```

**Alternatives Considered**:
1. **Fixed Row Offsets** (name always at row N, types at N+3, etc.)
   - **Rejected**: Actual spreadsheet has variable spacing between fields

2. **Semantic Keywords in Values** (search for "Creature-" to find type line)
   - **Rejected**: Unreliable for cards with unusual text (e.g., "text" field containing "Creature")

**Source**: Document 08 (Hellcube-Spreadsheet-Analysis.md)

---

## Decision 6: Template Caching Strategy

**Decision**: SHA-256 hash-based caching for VLM-detected template regions

**Rationale**:
- **Deduplication**: Hellcube has ~200 cards but only ~10-15 unique templates
  - Without caching: 200 cards × 1 VLM detection = 200 VLM calls
  - With caching: ~15 unique templates × 1 VLM detection = 15 VLM calls
  - **Savings**: 92.5% reduction in template detection VLM calls

- **Cache Key**: SHA-256 hash of template image file
  - Ensures different templates (even with same filename) get separate cache entries
  - Detects template modifications (hash changes trigger re-detection)

- **Persistence**: Save cache to `.cache/template_regions.json`
  - Survives across runs
  - Format: `{ "template_hash": { "name_box": {...}, "mana_cost_box": {...}, ... } }`

**Implementation**:
```python
def detect_regions(self, template_path: str) -> TemplateRegions:
    # Compute hash
    with open(template_path, 'rb') as f:
        template_hash = hashlib.sha256(f.read()).hexdigest()

    # Check cache
    if template_hash in self.cache:
        return self.cache[template_hash]

    # VLM detection (cache miss)
    regions = self.instructor.generate_structured(...)

    # Save to cache
    self.cache[template_hash] = regions
    self.save_cache()
    return regions
```

**Alternatives Considered**:
1. **Filename-Based Caching**
   - **Rejected**: Doesn't detect template modifications, vulnerable to filename collisions

2. **No Caching** (detect every time)
   - **Rejected**: Wastes VLM calls (200 instead of 15)

**Source**: Document 09 (Card-Template-Analysis.md)

---

## Decision 7: Ground Truth Validation

**Decision**: Use Nala creature card as ground truth for VLM detection accuracy validation (Phase 0)

**Rationale**:
- **Real Template**: Actual MTG-style card template (750×1050px, 300 DPI)
- **Manual Measurements**: Pixel-precise bounding boxes for 6 regions:
  - name_box: (50, 30, 530, 35)
  - mana_cost_box: (650, 25, 80, 40)
  - type_line_box: (50, 500, 650, 30)
  - text_box: (50, 540, 650, 360)
  - pt_box: (650, 950, 70, 50)
  - artwork_region: (50, 80, 650, 400) - MUST NOT be detected as text region

- **Success Criteria**: VLM detection within ±10px of ground truth for all regions
  - Example passing result:
    - Ground truth name_box: (50, 30, 530, 35)
    - VLM detected: (48, 32, 532, 34)
    - Max error: 3px ✓

- **Failure Action**: If VLM detection exceeds ±10px, iterate on detection prompt

**Test Implementation**:
```python
def test_vlm_detection_accuracy_nala_template():
    detector = VLMTemplateDetector(instructor_client)
    detected = detector.detect_regions("templates/nala_example_creature.png")

    ground_truth = EXAMPLE_CARD_GROUND_TRUTH['regions']

    for region_name in ['name_box', 'mana_cost_box', 'type_line_box', 'text_box', 'pt_box']:
        detected_box = getattr(detected, region_name)
        gt_box = ground_truth[region_name]

        max_error = max(
            abs(detected_box.x - gt_box.x),
            abs(detected_box.y - gt_box.y),
            abs(detected_box.width - gt_box.width),
            abs(detected_box.height - gt_box.height)
        )

        assert max_error <= 10, f"{region_name}: max_error={max_error}px"
```

**Source**: Document 09 (Card-Template-Analysis.md)

---

## Decision 8: Monorepo Integration Pattern

**Decision**: Implement MCTS algorithm in `../monorepo/agentic/algorithms/mcts/` following BaseAlgorithm protocol and Reflexion template structure

**Rationale**:
- **Reusability**: MCTS layout optimization applies to any layout problem (not just MTG cards)
- **Consistency**: Follows established monorepo patterns:
  - Inherit from `BaseAlgorithm`
  - Set `SUPPORTS_ITERATION = False` (internal search, not trial-and-error)
  - Use unified parameters: `max_steps`, `max_depth`, `branching_factor`, `domain`
  - Stateless execution with optional `iteration_context`

- **Testing Pattern**: Mirror Reflexion algorithm structure:
  - Unit tests: `tests/unit/algorithms/mcts/test_mcts_layout.py`
  - BDD tests: `tests/components/algorithms/mcts_layout.feature`
  - Step definitions: `tests/components/algorithms/steps/mcts_layout_steps.py`

**Key Implementation Points**:
```python
class MCTSLayoutAlgorithm(BaseAlgorithm):
    SUPPORTS_ITERATION = False  # Internal search (not iterative refinement)

    def __init__(self, name="mcts_layout", **config):
        super().__init__(name, **config)
        self.max_rollouts = self.max_steps * 100  # max_steps=3 → 300 rollouts
        self.exploration_constant = config.get('exploration_constant', 1.414)  # √2
        self.convergence_threshold = config.get('convergence_threshold', 0.01)

    def execute(self, problem: str, card_data: Dict,
                template_regions: Dict, **kwargs) -> Dict:
        # Returns Result(success, data, metadata) per monorepo protocol
        ...
```

**Alternatives Considered**:
1. **Implement in Hellcube repo** (not monorepo)
   - **Rejected**: MCTS layout is domain-agnostic, should be reusable

2. **New algorithm base class**
   - **Rejected**: BaseAlgorithm already provides needed protocol

**Source**: Documents 02 (Monorepo-Code-Structure.md), 07 (Phase-0-Validation.md)

---

## Decision 9: Incremental Validation Strategy

**Decision**: 5-phase validation to reduce risk of MCTS+VLM integration failures

**Phases**:
1. **VLM + Reflexion Integration Test**
   - Validate VLM + instructor framework works in existing algorithm context
   - Test: Reflexion algorithm with VLM backend completes without errors
   - **Exit Criteria**: Reflexion can call instructor.generate_structured() successfully

2. **MCTS Algorithm Implementation**
   - Write MCTSLayoutAlgorithm following Reflexion template
   - Unit tests for core operations (SELECT, EXPAND, SIMULATE, BACKPROPAGATE)
   - **Exit Criteria**: Unit tests >90% coverage, all passing

3. **BDD Tests for MCTS**
   - Write behave scenarios for simple/complex card convergence
   - **Exit Criteria**: All BDD scenarios pass

4. **Grid World Validation**
   - Test MCTS on known-good problem (2D grid navigation with obstacles)
   - Validates algorithm correctness before production use
   - **Exit Criteria**: MCTS finds optimal path in <100 rollouts with quality ≥0.9

5. **Hellcube Excel Integration**
   - Full end-to-end workflow (parse Excel → MCTS → generate proxies)
   - **Exit Criteria**: 95%+ cards with quality ≥0.8, batch completes in 1-3 hours

**Rationale**:
- **Fast Fail**: Catches VLM integration issues before writing MCTS algorithm
- **Incremental Complexity**: Each phase builds on previous validation
- **Known-Good Test**: Grid World provides algorithm correctness baseline

**Alternatives Considered**:
1. **Direct Production Integration** (skip Grid World)
   - **Rejected**: No way to distinguish MCTS bugs from domain-specific issues

2. **Unit Tests Only** (no BDD)
   - **Rejected**: Missing end-to-end scenario validation

**Source**: Documents 04 (Testing-Integration-Deployment.md), 07 (Phase-0-Validation.md), Clarification Session 2025-11-15

---

## Summary of Key Metrics

| Metric | Value | Source |
|--------|-------|--------|
| VLM calls per card | 100-300 | Clarification 2025-11-16 |
| VLM latency | 0.2s | Doc 09 |
| Per-card processing time | 20-60s | Plan.md |
| 200-card batch time | 1-3 hours | Plan.md |
| Action space per element | ~24 | Doc 05 |
| Unique templates (cache hits) | ~15 (vs 200 cards) | Doc 09 |
| Template detection accuracy | ±10px | Doc 09 |
| Target quality score | ≥0.8 for 95%+ cards | Spec.md |
| MCTS convergence rate | 70%+ | Doc 03 |
| Memory per card | <50MB | Plan.md |

---

## Unresolved Questions

**None.** All technical unknowns have been resolved through Documents 01-09 and clarification sessions.

---

## Next Phase

Phase 1: Design Artifacts
- Generate `data-model.md` (entities and schemas)
- Generate `contracts/` (Python module interfaces)
- Generate `quickstart.md` (setup and validation)
- Update agent context with MCTS/VLM patterns
