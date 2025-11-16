# Implementation Tasks: Hellcube Proxy Generator

**Branch**: `012-hellcube-proxy-generator`
**Date**: 2025-11-16
**Status**: Ready for Implementation

---

## Task Organization

Tasks are organized into **6 phases**:
1. **Phase 1**: Project Setup & Dependencies (Tasks 1-5)
2. **Phase 2**: Foundational MCTS Algorithm (Tasks 6-15) - **BLOCKS US3**
3. **Phase 3**: User Story 1 - Semantic Spreadsheet Parser (Tasks 16-25)
4. **Phase 4**: User Story 2 - Template Research & Download (Tasks 26-30)
5. **Phase 5**: User Story 3 - Proxy Card Generation (Tasks 31-45)
6. **Phase 6**: Polish & Cross-Cutting Concerns (Tasks 46-52)

**Total**: 52 tasks across 6 phases

---

## Dependency Graph

```
Phase 1 (Setup)
├─ T1: Project initialization
├─ T2: Ollama installation
├─ T3: Python dependencies
├─ T4: Test framework setup
└─ T5: Cache directory structure
   ↓
Phase 2 (MCTS Foundation) ─── BLOCKS US3 ───┐
├─ T6-T10: Data structures                   │
├─ T11-T14: MCTS core algorithm              │
└─ T15: MCTS unit tests                      │
   ↓                                          │
Phase 3 (US1: Excel Parser) ─ Parallel ──┐   │
├─ T16-T20: Card model & parsing         │   │
└─ T21-T25: Parser tests                 │   │
                                         │   │
Phase 4 (US2: Template Download) ─ Parallel ┘│
├─ T26-T28: Template matching                │
└─ T29-T30: Template tests                   │
   ↓                                          │
Phase 5 (US3: MCTS Integration) ◄────────────┘
├─ T31-T35: VLM evaluators
├─ T36-T40: MCTS-Hellcube integration
└─ T41-T45: Batch processor & tests
   ↓
Phase 6 (Polish)
├─ T46-T48: Documentation
├─ T49-T50: Performance validation
└─ T51-T52: Final integration
```

**Parallel Execution Opportunities**:
- After Phase 2: **US1 (T16-T25) and US2 (T26-T30) can run in parallel**
- Within Phase 5: T31-T35 (VLM) can partially overlap with T36-T40 (integration)

---

## Phase 1: Project Setup & Dependencies

### T1: Initialize project structure
**Priority**: P0 (Blocker)
**Estimate**: 15 minutes
**Dependencies**: None
**User Story**: Setup

**Description**:
Create directory structure for Hellcube-specific code and monorepo MCTS algorithm.

**Acceptance Criteria**:
- [ ] `magic-cards-edh-deck/src/` directory exists
- [ ] `magic-cards-edh-deck/tests/unit/` directory exists
- [ ] `magic-cards-edh-deck/tests/integration/` directory exists
- [ ] `../monorepo/agentic/algorithms/mcts/` directory exists
- [ ] `../monorepo/agentic/tests/unit/algorithms/mcts/` directory exists
- [ ] `../monorepo/agentic/tests/components/algorithms/` directory exists for BDD tests

**Files Created**:
- Directory structure only (no code files yet)

---

### T2: Install and configure Ollama VLM backend
**Priority**: P0 (Blocker)
**Estimate**: 20 minutes
**Dependencies**: None
**User Story**: Setup

**Description**:
Set up local Ollama server with llava-1.5 model for VLM template detection and layout scoring.

**Acceptance Criteria**:
- [ ] Ollama installed via `curl -fsSL https://ollama.com/install.sh | sh`
- [ ] llava:13b model downloaded via `ollama pull llava:13b` (~4GB)
- [ ] Ollama server running on localhost:11434
- [ ] Test VLM call succeeds: `curl http://localhost:11434/api/generate -d '{"model":"llava:13b","prompt":"test"}'`

**Validation**:
```bash
ollama list  # Should show llava:13b
curl http://localhost:11434/api/generate -d '{"model":"llava:13b","prompt":"Describe this image","stream":false}'
```

---

### T3: Install Python dependencies
**Priority**: P0 (Blocker)
**Estimate**: 10 minutes
**Dependencies**: T1
**User Story**: Setup

**Description**:
Install all required Python packages for Excel parsing, VLM integration, MCTS algorithm, and testing.

**Acceptance Criteria**:
- [ ] Create `requirements.txt` with:
  - pandas, openpyxl (Excel)
  - Pillow (image composition)
  - requests (HTTP)
  - Pydantic (validation)
  - instructor (VLM structured output)
  - pytest, pytest-cov (unit tests)
  - behave (BDD tests)
- [ ] Run `pip install -r requirements.txt` successfully
- [ ] Verify imports: `python -c "import pandas, openpyxl, PIL, instructor, pydantic"`

**Files Created**:
- `requirements.txt`

---

### T4: Set up test framework and fixtures
**Priority**: P0 (Blocker)
**Estimate**: 20 minutes
**Dependencies**: T3
**User Story**: Setup

**Description**:
Configure pytest and behave testing frameworks with test data fixtures.

**Acceptance Criteria**:
- [ ] Create `pytest.ini` with coverage configuration
- [ ] Create `behave.ini` for BDD tests
- [ ] Create `tests/fixtures/nala_ground_truth.json` with manual template measurements
- [ ] Create `tests/fixtures/test_cards.json` with 3 example cards (simple, medium, complex)
- [ ] Test frameworks run: `pytest --version`, `behave --version`

**Files Created**:
- `pytest.ini`
- `behave.ini`
- `tests/fixtures/nala_ground_truth.json`
- `tests/fixtures/test_cards.json`

---

### T5: Create cache directory structure
**Priority**: P1
**Estimate**: 5 minutes
**Dependencies**: T1
**User Story**: Setup

**Description**:
Set up cache directories for VLM-detected template regions and mana cost symbol images.

**Acceptance Criteria**:
- [ ] Create `.cache/` directory (gitignored)
- [ ] Create `.cache/template_regions.json` (empty initially)
- [ ] Create `.cache/mana_symbols/` for downloaded symbols
- [ ] Update `.gitignore` to exclude `.cache/`

**Files Created**:
- `.cache/` directory
- `.cache/template_regions.json` (empty dict: `{}`)
- Updated `.gitignore`

---

## Phase 2: Foundational MCTS Algorithm (BLOCKS US3)

### T6: Implement BoundingBox data structure
**Priority**: P0 (Foundation for Phase 2)
**Estimate**: 15 minutes
**Dependencies**: T3
**User Story**: US3 (Proxy Card Generation)

**Description**:
Create BoundingBox dataclass for template regions and overlap detection.

**Acceptance Criteria**:
- [ ] File: `../monorepo/agentic/algorithms/mcts/data_structures.py`
- [ ] `BoundingBox` dataclass with `x, y, width, height` attributes
- [ ] Method `contains_point(px, py) -> bool`
- [ ] Method `overlaps(other: BoundingBox) -> bool`
- [ ] Docstrings for all methods

**Files Created**:
- `../monorepo/agentic/algorithms/mcts/data_structures.py`

**Tests Required**: T15 (unit tests for data structures)

---

### T7: Implement CardElement and PlacedElement
**Priority**: P0
**Estimate**: 20 minutes
**Dependencies**: T6
**User Story**: US3

**Description**:
Create element representation classes for unpositional and positioned card elements.

**Acceptance Criteria**:
- [ ] Add to `data_structures.py`:
  - `CardElement` dataclass (`element_type, text_content, required`)
  - `PlacedElement` dataclass (`element_type, text_content, position, size, font_size, alignment`)
  - Method `PlacedElement.get_bounding_box() -> BoundingBox`

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/data_structures.py`

---

### T8: Implement LayoutAction
**Priority**: P0
**Estimate**: 25 minutes
**Dependencies**: T7
**User Story**: US3

**Description**:
Create action representation with `apply_to_state()` method.

**Acceptance Criteria**:
- [ ] `LayoutAction` dataclass (`element, region, position, font_size, alignment`)
- [ ] Method `apply_to_state(state: LayoutState) -> LayoutState`
- [ ] Validation: font_size in [8, 20], alignment in ["left", "center", "right"]
- [ ] Integration with text width estimation (placeholder for now)

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/data_structures.py`

---

### T9: Implement LayoutState
**Priority**: P0
**Estimate**: 30 minutes
**Dependencies**: T7
**User Story**: US3

**Description**:
Create MCTS search state representation.

**Acceptance Criteria**:
- [ ] `LayoutState` dataclass (`placed_elements, remaining_elements, template_regions, quality_score`)
- [ ] Method `is_terminal() -> bool`
- [ ] Method `has_overlap() -> bool`
- [ ] Method `copy() -> LayoutState` (deep copy for simulation)
- [ ] Validation: placed + remaining = total elements

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/data_structures.py`

---

### T10: Implement MCTSNode
**Priority**: P0
**Estimate**: 35 minutes
**Dependencies**: T9
**User Story**: US3

**Description**:
Create MCTS tree node with UCB1 scoring.

**Acceptance Criteria**:
- [ ] `MCTSNode` dataclass (`state, parent, children, visits, total_reward, untried_actions`)
- [ ] Method `is_fully_expanded() -> bool`
- [ ] Method `is_terminal() -> bool`
- [ ] Method `get_average_reward() -> float`
- [ ] Method `get_ucb1_score(exploration_constant=1.414) -> float`
- [ ] UCB1 formula: `Q(node) + C × sqrt(ln(N_parent) / N_node)`
- [ ] Unvisited nodes return `float('inf')`

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/data_structures.py`

---

### T11: Implement MCTS SELECT phase
**Priority**: P0
**Estimate**: 20 minutes
**Dependencies**: T10
**User Story**: US3

**Description**:
Implement UCB1 tree traversal for selection phase.

**Acceptance Criteria**:
- [ ] File: `../monorepo/agentic/algorithms/mcts/mcts_layout.py`
- [ ] Class `MCTSLayoutAlgorithm(BaseAlgorithm)`
- [ ] `SUPPORTS_ITERATION = False`
- [ ] Method `_select(node: MCTSNode) -> MCTSNode`
- [ ] Algorithm: traverse tree using highest UCB1 score until reaching unexpanded or terminal node

**Files Created**:
- `../monorepo/agentic/algorithms/mcts/mcts_layout.py`

---

### T12: Implement MCTS EXPAND phase
**Priority**: P0
**Estimate**: 25 minutes
**Dependencies**: T11
**User Story**: US3

**Description**:
Implement node expansion by adding one child for an untried action.

**Acceptance Criteria**:
- [ ] Method `_expand(node: MCTSNode) -> MCTSNode`
- [ ] Pop one untried action from node
- [ ] Apply action to create new state
- [ ] Create child node, link to parent
- [ ] Return new child node

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/mcts_layout.py`

---

### T13: Implement MCTS SIMULATE phase (with VLM placeholder)
**Priority**: P0
**Estimate**: 30 minutes
**Dependencies**: T12
**User Story**: US3

**Description**:
Implement random rollout simulation. Use placeholder VLM scoring for now (T31 adds real VLM).

**Acceptance Criteria**:
- [ ] Method `_simulate(node: MCTSNode, vlm_evaluator=None) -> float`
- [ ] Random rollout: apply random actions until terminal state
- [ ] If `vlm_evaluator` provided: call `vlm_evaluator.score_layout(terminal_state)`
- [ ] Else (placeholder): return `0.5 + random.uniform(-0.1, 0.1)`
- [ ] Return score in [0.0, 1.0]

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/mcts_layout.py`

---

### T14: Implement MCTS BACKPROPAGATE phase and main loop
**Priority**: P0
**Estimate**: 40 minutes
**Dependencies**: T13
**User Story**: US3

**Description**:
Implement backpropagation and main MCTS loop with convergence detection.

**Acceptance Criteria**:
- [ ] Method `_backpropagate(node: MCTSNode, reward: float)`
- [ ] Update visits and total_reward for all ancestors
- [ ] Method `execute(problem, card_data, template_regions, **kwargs) -> Dict[str, Any]`
- [ ] Main MCTS loop: SELECT → EXPAND → SIMULATE → BACKPROPAGATE
- [ ] Convergence detection: stop when score stable within 0.01 for 10 rollouts
- [ ] Return `Result(success, data, metadata)` per BaseAlgorithm protocol
- [ ] Max rollouts: `max_steps × 100`

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/mcts_layout.py`

---

### T15: Write MCTS unit tests
**Priority**: P0
**Estimate**: 60 minutes
**Dependencies**: T14
**User Story**: US3

**Description**:
Comprehensive unit tests for MCTS algorithm components.

**Acceptance Criteria**:
- [ ] File: `../monorepo/agentic/tests/unit/algorithms/mcts/test_mcts_layout.py`
- [ ] Test: `test_ucb1_score_calculation()` - verify UCB1 formula
- [ ] Test: `test_action_generation_strategic_sampling()` - verify ~24 actions per element
- [ ] Test: `test_convergence_detection()` - verify early termination
- [ ] Test: `test_mcts_initialization()` - verify defaults
- [ ] Test: `test_select_phase()` - verify highest UCB1 selection
- [ ] Test: `test_expand_phase()` - verify child creation
- [ ] Test: `test_simulate_phase()` - verify random rollout
- [ ] Test: `test_backpropagate_phase()` - verify ancestor updates
- [ ] Coverage: >90%

**Files Created**:
- `../monorepo/agentic/tests/unit/algorithms/mcts/test_mcts_layout.py`
- `../monorepo/agentic/tests/unit/algorithms/mcts/test_data_structures.py`

---

## Phase 3: User Story 1 - Semantic Spreadsheet Parser

### T16: Implement ManaCost model and parser
**Priority**: P1
**Estimate**: 30 minutes
**Dependencies**: T5
**User Story**: US1 (Semantic Spreadsheet Parser)

**Description**:
Parse mana cost notation `(Bu,Bu)(1)` → structured ManaCost object.

**Acceptance Criteria**:
- [ ] File: `src/mana_cost_parser.py`
- [ ] `ManaCost` dataclass (`symbols: List[Tuple[str, int]], cmc: int`)
- [ ] Function `parse_mana_cost(cost_string: str) -> ManaCost`
- [ ] Symbol mapping: Wt→W, Bu→U, Bk→B, Rd→R, Gn→G, Cl→C
- [ ] Generic mana: `(1)` → `('Generic', 1)`
- [ ] Examples:
  - `"(Bu,Bu)(1)"` → `ManaCost([('U', 2), ('Generic', 1)], cmc=3)`
  - `"(Wt,Wt,Bu)"` → `ManaCost([('W', 2), ('U', 1)], cmc=3)`

**Files Created**:
- `src/mana_cost_parser.py`

---

### T17: Implement Card model with Pydantic validation
**Priority**: P1
**Estimate**: 40 minutes
**Dependencies**: T16
**User Story**: US1

**Description**:
Create Card data model with full validation rules from data-model.md.

**Acceptance Criteria**:
- [ ] File: `src/models.py`
- [ ] `Card` Pydantic BaseModel with fields: name, mana_cost, color, type, legendary, subtypes, abilities, flavor_text, power_toughness, author, artwork_url
- [ ] Validators:
  - name: min_length=1
  - color: pattern `^(W|U|B|R|G|C|Multicolor)$`
  - type: one of [Creature, Planeswalker, Artifact, Enchantment, Instant, Sorcery, Land]
  - power_toughness: pattern `^\d+/\d+$` if present
  - artwork_url: HttpUrl format
- [ ] Method `infer_color() -> str` (from mana_cost symbols)

**Files Created**:
- `src/models.py`

---

### T18: Implement HellcubeExcelParser core logic
**Priority**: P1
**Estimate**: 90 minutes
**Dependencies**: T17
**User Story**: US1

**Description**:
Parse Hellcube AJ.xlsx using dynamic adjacency detection for field labels.

**Acceptance Criteria**:
- [ ] File: `src/hellcube_parser.py`
- [ ] Class `HellcubeExcelParser`
- [ ] Method `parse_excel(file_path: str) -> List[Card]`
- [ ] Detect "AJ" markers in columns C, D, E, F
- [ ] Use Column A labels: "name bULK", "Types", "text", "flavor", "Stats", "Author"
- [ ] Extract card name and mana cost from combined string
- [ ] Parse Types field → (type, legendary, subtypes)
- [ ] Handle datetime quirk: `2025-02-04` → P/T `"2/4"`
- [ ] Collect multiple "text" rows into abilities list

**Files Created**:
- `src/hellcube_parser.py`

---

### T19: Implement Excel parser helper methods
**Priority**: P1
**Estimate**: 60 minutes
**Dependencies**: T18
**User Story**: US1

**Description**:
Private parsing methods for name/cost extraction, type parsing, and stats handling.

**Acceptance Criteria**:
- [ ] Method `_parse_name_and_cost(raw_value: str) -> Tuple[str, ManaCost]`
  - Extract name before last `(`, parse remaining as mana cost
- [ ] Method `_parse_types(types_value: str) -> Tuple[str, bool, List[str]]`
  - Detect "Legendary" keyword
  - Extract primary type and subtypes (split on `-`)
- [ ] Method `_parse_stats(stats_value: Any) -> Optional[str]`
  - Handle str "2/4" or datetime(2025, 2, 4) → "2/4"
- [ ] Custom exception `ParsingError(card_name, field, reason)`

**Files Modified**:
- `src/hellcube_parser.py`

---

### T20: Add Excel parser validation and warnings
**Priority**: P2
**Estimate**: 30 minutes
**Dependencies**: T19
**User Story**: US1

**Description**:
Post-processing validation and optional field warnings.

**Acceptance Criteria**:
- [ ] Validate all cards have non-empty `name` and `type`
- [ ] Validate `power_toughness` matches `\d+/\d+` pattern if present
- [ ] Infer `color` from `mana_cost` symbols
- [ ] Log warnings for missing optional fields (flavor_text, author, artwork_url)
- [ ] Detect duplicate card names within same author

**Files Modified**:
- `src/hellcube_parser.py`

---

### T21: Write unit tests for ManaCost parser
**Priority**: P1
**Estimate**: 30 minutes
**Dependencies**: T16
**User Story**: US1

**Description**:
Test all mana cost notation parsing cases.

**Acceptance Criteria**:
- [ ] File: `tests/unit/test_mana_cost_parser.py`
- [ ] Test: single color `"(Bu,Bu)"` → `[('U', 2)]`
- [ ] Test: mixed colors `"(Wt,Bu,Gn)"` → `[('W', 1), ('U', 1), ('G', 1)]`
- [ ] Test: generic + colored `"(Rd,Rd)(3)"` → `[('R', 2), ('Generic', 3)]`
- [ ] Test: no cost `""` → `ManaCost([], cmc=0)`
- [ ] Test: invalid notation raises ParsingError

**Files Created**:
- `tests/unit/test_mana_cost_parser.py`

---

### T22: Write unit tests for Card model
**Priority**: P1
**Estimate**: 40 minutes
**Dependencies**: T17
**User Story**: US1

**Description**:
Test Card Pydantic validation rules.

**Acceptance Criteria**:
- [ ] File: `tests/unit/test_models.py`
- [ ] Test: valid creature card passes validation
- [ ] Test: invalid card type raises ValidationError
- [ ] Test: invalid P/T pattern raises ValidationError
- [ ] Test: invalid color pattern raises ValidationError
- [ ] Test: infer_color() correctly maps mana symbols to colors
- [ ] Test: multicolor inference (2+ color symbols → "Multicolor")

**Files Created**:
- `tests/unit/test_models.py`

---

### T23: Write unit tests for HellcubeExcelParser
**Priority**: P1
**Estimate**: 60 minutes
**Dependencies**: T20
**User Story**: US1

**Description**:
Test Excel parsing logic with fixture data.

**Acceptance Criteria**:
- [ ] File: `tests/unit/test_hellcube_parser.py`
- [ ] Create test Excel file with 2 cards (one simple, one complex)
- [ ] Test: parse_excel() returns List[Card]
- [ ] Test: "AJ" marker detection
- [ ] Test: field adjacency detection (Types, text, flavor, Stats)
- [ ] Test: multiple abilities extraction
- [ ] Test: datetime P/T quirk handling
- [ ] Test: FileNotFoundError when file missing
- [ ] Test: ValueError when structure invalid

**Files Created**:
- `tests/unit/test_hellcube_parser.py`
- `tests/fixtures/test_hellcube_2cards.xlsx`

---

### T24: Write BDD tests for Hellcube parsing
**Priority**: P1
**Estimate**: 45 minutes
**Dependencies**: T23
**User Story**: US1

**Description**:
End-to-end BDD scenarios for Excel parsing workflow.

**Acceptance Criteria**:
- [ ] File: `tests/integration/hellcube_parsing.feature`
- [ ] Scenario: Parse simple card (vanilla creature)
- [ ] Scenario: Parse complex card (3 abilities, legendary)
- [ ] Scenario: Parse planeswalker card (no P/T)
- [ ] File: `tests/integration/steps/hellcube_parsing_steps.py`
- [ ] Steps: Given Excel file, When parse, Then card attributes correct

**Files Created**:
- `tests/integration/hellcube_parsing.feature`
- `tests/integration/steps/hellcube_parsing_steps.py`

---

### T25: Add Excel parser error handling tests
**Priority**: P2
**Estimate**: 30 minutes
**Dependencies**: T23
**User Story**: US1

**Description**:
Test error cases and edge conditions.

**Acceptance Criteria**:
- [ ] Test: malformed mana cost raises ParsingError
- [ ] Test: missing "AJ" marker raises ValueError
- [ ] Test: missing required field (name, type) raises ParsingError
- [ ] Test: invalid type value logged as warning
- [ ] Test: duplicate card names logged as warning

**Files Modified**:
- `tests/unit/test_hellcube_parser.py`

---

## Phase 4: User Story 2 - Template Research & Download

### T26: Implement template filename fuzzy matching
**Priority**: P1
**Estimate**: 45 minutes
**Dependencies**: T17 (Card model)
**User Story**: US2 (Template Research & Download)

**Description**:
Match Card type/color to template filenames with fuzzy matching.

**Acceptance Criteria**:
- [ ] File: `src/template_matcher.py`
- [ ] Function `infer_template_file(card: Card) -> str`
- [ ] Template naming convention: `{color}_{type}.png`
  - Examples: `blue_creature.png`, `red_planeswalker.png`, `artifact.png`
- [ ] Fuzzy matching for:
  - Color: W→white, U→blue, B→black, R→red, G→green, C→colorless
  - Multicolor → `multicolor_{type}.png`
  - Land cards → `land.png` (no color)
- [ ] Return default `generic_card.png` if no match

**Files Created**:
- `src/template_matcher.py`

---

### T27: Implement template download and caching
**Priority**: P1
**Estimate**: 60 minutes
**Dependencies**: T26, existing HTTP skills
**User Story**: US2

**Description**:
Download MTG card templates from URLs using existing `.claude/skills/http/` skills.

**Acceptance Criteria**:
- [ ] File: `src/template_downloader.py`
- [ ] Function `download_template(template_name: str, url: str, output_dir: str) -> str`
- [ ] Use requests library (not HTTP skill for now - HTTP skill integration in T28)
- [ ] Save to `output_dir/{template_name}`
- [ ] Skip if file already exists (cache check)
- [ ] Validate image dimensions (750×1050px expected)
- [ ] Return absolute path to downloaded template

**Files Created**:
- `src/template_downloader.py`

---

### T28: Integrate domain-agnostic HTTP skills for template fetching
**Priority**: P2
**Estimate**: 30 minutes
**Dependencies**: T27
**User Story**: US2

**Description**:
Replace requests calls with `.claude/skills/http/` skill invocations for consistency.

**Acceptance Criteria**:
- [ ] Refactor `template_downloader.py` to use HTTP skill if available
- [ ] Fallback to requests library if skill not present
- [ ] Test: template download works via skill invocation
- [ ] Document skill usage in docstrings

**Files Modified**:
- `src/template_downloader.py`

---

### T29: Write unit tests for template matcher
**Priority**: P1
**Estimate**: 30 minutes
**Dependencies**: T26
**User Story**: US2

**Description**:
Test template filename inference logic.

**Acceptance Criteria**:
- [ ] File: `tests/unit/test_template_matcher.py`
- [ ] Test: blue creature → `blue_creature.png`
- [ ] Test: red planeswalker → `red_planeswalker.png`
- [ ] Test: multicolor creature → `multicolor_creature.png`
- [ ] Test: colorless artifact → `colorless_artifact.png`
- [ ] Test: land → `land.png`
- [ ] Test: unknown type → `generic_card.png`

**Files Created**:
- `tests/unit/test_template_matcher.py`

---

### T30: Write integration tests for template download
**Priority**: P1
**Estimate**: 30 minutes
**Dependencies**: T28
**User Story**: US2

**Description**:
Test template download workflow with mock HTTP responses.

**Acceptance Criteria**:
- [ ] File: `tests/integration/test_template_download.py`
- [ ] Test: download template from URL (using test fixture URL)
- [ ] Test: cache hit (second call skips download)
- [ ] Test: invalid dimensions raise ValidationError
- [ ] Test: network error handling

**Files Created**:
- `tests/integration/test_template_download.py`

---

## Phase 5: User Story 3 - Proxy Card Generation (MCTS Integration)

### T31: Implement TemplateRegions Pydantic model
**Priority**: P0 (Unblocks VLM detector)
**Estimate**: 25 minutes
**Dependencies**: T6 (BoundingBox)
**User Story**: US3

**Description**:
Create Pydantic model for VLM-detected template regions.

**Acceptance Criteria**:
- [ ] File: `../monorepo/agentic/algorithms/mcts/vlm_evaluators.py`
- [ ] `TemplateRegions` Pydantic model:
  - Fields: template_hash, name_box, mana_cost_box, type_line_box, text_boxes (list), pt_box (optional), flavor_box (optional), artwork_detected (bool)
  - Validation: artwork_detected must be False (fail if artwork detected as text)
- [ ] Include example in schema_extra

**Files Created**:
- `../monorepo/agentic/algorithms/mcts/vlm_evaluators.py`

---

### T32: Implement VLMTemplateDetector
**Priority**: P0
**Estimate**: 75 minutes
**Dependencies**: T31, T2 (Ollama)
**User Story**: US3

**Description**:
VLM-based template region detection with SHA-256 caching.

**Acceptance Criteria**:
- [ ] Class `VLMTemplateDetector` in `vlm_evaluators.py`
- [ ] Method `detect_regions(template_path: str) -> TemplateRegions`
- [ ] SHA-256 hash computation for cache key
- [ ] Cache check before VLM call
- [ ] VLM prompt for template region detection (see contract)
- [ ] Validation: `_validate_regions()` checks artwork not detected
- [ ] Save cache to `.cache/template_regions.json`
- [ ] Integration with instructor framework

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/vlm_evaluators.py`

---

### T33: Implement LayoutQuality Pydantic model
**Priority**: P0
**Estimate**: 20 minutes
**Dependencies**: T31
**User Story**: US3

**Description**:
Create Pydantic model for VLM layout quality evaluation.

**Acceptance Criteria**:
- [ ] `LayoutQuality` Pydantic model in `vlm_evaluators.py`:
  - Fields: readability_score, convention_compliance, aesthetic_balance, overall_score, no_overflow, issues (list), reasoning
  - All scores: ge=0.0, le=1.0
  - reasoning: max_length=200
- [ ] Include example in schema_extra

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/vlm_evaluators.py`

---

### T34: Implement VLMLayoutEvaluator
**Priority**: P0
**Estimate**: 90 minutes
**Dependencies**: T33
**User Story**: US3

**Description**:
VLM-based layout quality scoring (called every MCTS rollout).

**Acceptance Criteria**:
- [ ] Class `VLMLayoutEvaluator` in `vlm_evaluators.py`
- [ ] Method `score_layout(layout_state: LayoutState, card_data: Dict) -> float`
- [ ] Validate `layout_state.is_terminal()` before scoring
- [ ] Render layout to PIL Image: `_render_layout(layout_state) -> PIL.Image`
- [ ] VLM prompt for layout quality scoring (see contract)
- [ ] Return `overall_score` from LayoutQuality
- [ ] Performance: ~0.2s per call

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/vlm_evaluators.py`

---

### T35: Implement action generation with strategic sampling
**Priority**: P0
**Estimate**: 60 minutes
**Dependencies**: T14 (MCTS main loop)
**User Story**: US3

**Description**:
Generate ~24 strategic actions per element (not 49,140 full enumeration).

**Acceptance Criteria**:
- [ ] Method `_generate_actions(state: LayoutState) -> List[LayoutAction]` in `mcts_layout.py`
- [ ] Strategic sampling: 8 positions per region (4 corners + 4 midpoints)
- [ ] Element-specific constraints:
  - name: center alignment, fonts [14, 16]
  - mana_cost: right alignment, font [14]
  - type_line: center alignment, font [12]
  - abilities: left alignment, fonts [10, 11, 12]
  - p_t: right alignment, font [14]
  - flavor: left alignment, font [10]
- [ ] Result: ~24 actions per element

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/mcts_layout.py`

---

### T36: Integrate VLMLayoutEvaluator into MCTS SIMULATE phase
**Priority**: P0
**Estimate**: 20 minutes
**Dependencies**: T34, T13 (SIMULATE placeholder)
**User Story**: US3

**Description**:
Replace placeholder VLM scoring with real VLMLayoutEvaluator.

**Acceptance Criteria**:
- [ ] Modify `_simulate()` in `mcts_layout.py` to accept `vlm_evaluator: VLMLayoutEvaluator`
- [ ] Call `vlm_evaluator.score_layout(terminal_state, card_data)`
- [ ] Remove placeholder random scoring
- [ ] Update `execute()` to instantiate VLMLayoutEvaluator

**Files Modified**:
- `../monorepo/agentic/algorithms/mcts/mcts_layout.py`

---

### T37: Write VLM evaluator unit tests (with mock VLM)
**Priority**: P1
**Estimate**: 60 minutes
**Dependencies**: T34
**User Story**: US3

**Description**:
Test VLM evaluators with mocked instructor calls.

**Acceptance Criteria**:
- [ ] File: `../monorepo/agentic/tests/unit/algorithms/mcts/test_vlm_evaluators.py`
- [ ] Test: `test_template_detection_caching()` - verify SHA-256 cache hit
- [ ] Test: `test_layout_scoring_non_terminal_fails()` - raises ValueError
- [ ] Test: `test_vlm_detection_validation()` - artwork_detected=True fails
- [ ] Use mocked instructor client (returns fixed TemplateRegions/LayoutQuality)

**Files Created**:
- `../monorepo/agentic/tests/unit/algorithms/mcts/test_vlm_evaluators.py`

---

### T38: Write Phase 0 validation test (VLM accuracy on Nala card)
**Priority**: P0 (Critical validation)
**Estimate**: 45 minutes
**Dependencies**: T32, T4 (nala_ground_truth.json)
**User Story**: US3

**Description**:
Validate VLM detection within ±10px of manual ground truth measurements.

**Acceptance Criteria**:
- [ ] File: `tests/integration/test_vlm_detection.py`
- [ ] Test: `test_vlm_detection_accuracy_nala_template()`
- [ ] Load ground truth from `tests/fixtures/nala_ground_truth.json`
- [ ] Detect regions on Nala template using VLMTemplateDetector
- [ ] Compare all regions (name_box, mana_cost_box, type_line_box, text_box, pt_box)
- [ ] Assert max error ≤ 10px for all regions
- [ ] **FAIL if artwork_detected=True**

**Files Created**:
- `tests/integration/test_vlm_detection.py`

**SUCCESS CRITERIA**: All regions within ±10px, artwork not detected

---

### T39: Write Grid World MCTS validation test
**Priority**: P0 (Algorithm correctness validation)
**Estimate**: 90 minutes
**Dependencies**: T14 (MCTS main loop)
**User Story**: US3

**Description**:
Test MCTS on known-good problem (2D grid navigation with obstacles).

**Acceptance Criteria**:
- [ ] File: `tests/integration/test_mcts_grid_world.py`
- [ ] Create Grid World problem: 5×5 grid, start=(0,0), goal=(4,4), 3 obstacles
- [ ] Adapt MCTS to grid navigation: states=positions, actions=moves, reward=1.0 if goal reached else 0.0
- [ ] Test: MCTS finds optimal path in <100 rollouts
- [ ] Test: Final quality score ≥ 0.9
- [ ] **PURPOSE**: Validate algorithm correctness before production use

**Files Created**:
- `tests/integration/test_mcts_grid_world.py`

**SUCCESS CRITERIA**: Optimal path found in <100 rollouts, quality ≥0.9

---

### T40: Write MCTS BDD tests for simple/complex cards
**Priority**: P1
**Estimate**: 60 minutes
**Dependencies**: T36 (VLM-integrated MCTS)
**User Story**: US3

**Description**:
End-to-end BDD scenarios for MCTS layout convergence.

**Acceptance Criteria**:
- [ ] File: `../monorepo/agentic/tests/components/algorithms/mcts_layout.feature`
- [ ] Scenario: MCTS converges on simple card (1 ability)
  - Given card with 1 ability, template regions, max_steps=1
  - When execute MCTS
  - Then quality ≥ 0.8, rollouts ≤ 100, converged=True
- [ ] Scenario: MCTS handles complex card (3 abilities)
  - Given card with 3 abilities, max_steps=3
  - Then quality ≥ 0.8, rollouts ≤ 300
- [ ] File: `../monorepo/agentic/tests/components/algorithms/steps/mcts_layout_steps.py`

**Files Created**:
- `../monorepo/agentic/tests/components/algorithms/mcts_layout.feature`
- `../monorepo/agentic/tests/components/algorithms/steps/mcts_layout_steps.py`

---

### T41: Implement PIL-based proxy compositor
**Priority**: P1
**Estimate**: 90 minutes
**Dependencies**: T36 (MCTS returns LayoutState)
**User Story**: US3

**Description**:
Render final card layout to PNG using PIL image composition.

**Acceptance Criteria**:
- [ ] File: `src/proxy_compositor.py`
- [ ] Class `ProxyCompositor`
- [ ] Method `render_card(card: Card, layout: LayoutState, template_path: str) -> PIL.Image`
- [ ] Load template image
- [ ] Composite text using PIL.ImageDraw
- [ ] Handle font sizes, alignment, multi-line text wrapping
- [ ] Render mana symbols as images (if available in cache)
- [ ] Return 750×1050px RGB image

**Files Created**:
- `src/proxy_compositor.py`

---

### T42: Implement batch processor with folder organization
**Priority**: P1
**Estimate**: 75 minutes
**Dependencies**: T41
**User Story**: US3

**Description**:
Process all cards from Excel, organize outputs by color/type.

**Acceptance Criteria**:
- [ ] File: `src/batch_organizer.py`
- [ ] Function `organize_proxies(cards: List[Card], output_dir: str)`
- [ ] Folder structure: `{output_dir}/{color}/{type}/`
  - Example: `blue/creatures/`, `planeswalkers/red/`
- [ ] Function `process_batch(excel_path: str, output_dir: str, max_steps=3)`
- [ ] Parse Excel → for each card → detect template → MCTS → render → save PNG
- [ ] Progress logging: "Card 42/200 (Batman Blue): 28 rollouts, quality 0.91, 5.6s"

**Files Created**:
- `src/batch_organizer.py`

---

### T43: Implement CLI entry point
**Priority**: P1
**Estimate**: 30 minutes
**Dependencies**: T42
**User Story**: US3

**Description**:
Command-line interface for proxy generation.

**Acceptance Criteria**:
- [ ] File: `src/proxy_generator.py`
- [ ] CLI arguments: `--input`, `--output`, `--max-steps`, `--limit`
- [ ] Usage: `python -m src.proxy_generator "Hellcube AJ.xlsx" --output proxies/ --max-steps 3`
- [ ] Optional `--limit N` for testing (process first N cards only)
- [ ] Display summary: total cards, avg rollouts, avg quality, total time

**Files Created**:
- `src/proxy_generator.py`

---

### T44: Write batch processing integration tests
**Priority**: P1
**Estimate**: 45 minutes
**Dependencies**: T42
**User Story**: US3

**Description**:
Test batch processing workflow with 10-card subset.

**Acceptance Criteria**:
- [ ] File: `tests/integration/test_batch_processing.py`
- [ ] Test: process 10 cards from test Excel file
- [ ] Validate output folder structure created
- [ ] Validate all PNG files generated (750×1050px)
- [ ] Check avg quality ≥ 0.8
- [ ] Check total time ≤ 60s (6s per card average)

**Files Created**:
- `tests/integration/test_batch_processing.py`

---

### T45: Write BDD tests for end-to-end proxy generation
**Priority**: P1
**Estimate**: 60 minutes
**Dependencies**: T43
**User Story**: US3

**Description**:
Full workflow BDD scenarios from Excel to PNG proxies.

**Acceptance Criteria**:
- [ ] File: `tests/integration/proxy_generation.feature`
- [ ] Scenario: Generate proxy for simple card (vanilla creature)
- [ ] Scenario: Generate proxy for complex card (3 abilities, legendary)
- [ ] Scenario: Generate proxy for planeswalker (no P/T)
- [ ] Scenario: Batch process 10 cards
- [ ] File: `tests/integration/steps/proxy_generation_steps.py`

**Files Created**:
- `tests/integration/proxy_generation.feature`
- `tests/integration/steps/proxy_generation_steps.py`

---

## Phase 6: Polish & Cross-Cutting Concerns

### T46: Generate comprehensive quickstart guide
**Priority**: P2
**Estimate**: 30 minutes
**Dependencies**: T43
**User Story**: Documentation

**Description**:
Update quickstart.md with complete setup and validation instructions.

**Acceptance Criteria**:
- [ ] Document: `specs/012-hellcube-proxy-generator/quickstart.md`
- [ ] Section 1: Prerequisites (Python 3.9+, Ollama)
- [ ] Section 2: Installation steps
- [ ] Section 3: 8 validation tests (Phase 0-4)
- [ ] Section 4: Usage examples
- [ ] Section 5: Troubleshooting common issues

**Files Modified**:
- `specs/012-hellcube-proxy-generator/quickstart.md` (already exists, update with final details)

---

### T47: Add inline documentation and docstrings
**Priority**: P2
**Estimate**: 60 minutes
**Dependencies**: All implementation tasks
**User Story**: Documentation

**Description**:
Ensure all modules have comprehensive docstrings.

**Acceptance Criteria**:
- [ ] All classes have class-level docstrings
- [ ] All public methods have docstrings with Args/Returns/Raises
- [ ] Complex algorithms (MCTS phases) have inline comments
- [ ] Data structures have attribute descriptions
- [ ] No TODOs or placeholder comments remain

**Files Modified**:
- All `src/*.py` and `../monorepo/agentic/algorithms/mcts/*.py` files

---

### T48: Create API reference documentation
**Priority**: P3 (Nice-to-have)
**Estimate**: 45 minutes
**Dependencies**: T47
**User Story**: Documentation

**Description**:
Generate API documentation from docstrings using Sphinx or pdoc.

**Acceptance Criteria**:
- [ ] Install pdoc: `pip install pdoc`
- [ ] Generate docs: `pdoc --html src/ ../monorepo/agentic/algorithms/mcts/`
- [ ] Output to `docs/api/`
- [ ] Include in repository (or .gitignore if too large)

**Files Created**:
- `docs/api/` directory (optional)

---

### T49: Run performance validation on 200-card batch
**Priority**: P1
**Estimate**: 3 hours (mostly waiting)
**Dependencies**: T43, T2 (Ollama)
**User Story**: Validation

**Description**:
Full performance test with complete Hellcube dataset.

**Acceptance Criteria**:
- [ ] Run: `python -m src.proxy_generator "Hellcube AJ.xlsx" --output proxies/ --max-steps 3`
- [ ] Record metrics:
  - Total time: 1-3 hours (target)
  - Avg rollouts per card: <100 (target)
  - Avg quality score: ≥0.8 for 95%+ cards
  - Convergence rate: 70%+
- [ ] Validate all 200 PNGs generated (750×1050px)
- [ ] Manually review 10 random cards for quality

**Validation Checklist**:
- [ ] Total time ≤ 3 hours
- [ ] ≥95% of cards have quality ≥0.8
- [ ] ≥70% of cards converged before max rollouts
- [ ] No crashes or exceptions

---

### T50: Add performance profiling and optimization
**Priority**: P3 (Optional)
**Estimate**: 90 minutes
**Dependencies**: T49
**User Story**: Performance

**Description**:
Profile batch processing to identify bottlenecks and optimize if needed.

**Acceptance Criteria**:
- [ ] Use cProfile to measure time spent in each component
- [ ] Identify top 5 time consumers (likely: VLM calls, PIL rendering, MCTS tree operations)
- [ ] Optional optimizations:
  - Cache text width estimates
  - Reuse PIL font objects
  - Parallelize independent VLM calls (if feasible)
- [ ] Document profiling results in `specs/012-hellcube-proxy-generator/performance.md`

**Files Created**:
- `specs/012-hellcube-proxy-generator/performance.md` (optional)

---

### T51: Final integration test with all components
**Priority**: P1
**Estimate**: 30 minutes
**Dependencies**: T49
**User Story**: Validation

**Description**:
Run complete test suite to ensure all components integrate correctly.

**Acceptance Criteria**:
- [ ] Run: `pytest tests/ -v --cov=src --cov=../monorepo/agentic/algorithms/mcts`
- [ ] Coverage: ≥90% for all modules
- [ ] Run: `behave tests/integration/ tests/../monorepo/agentic/tests/components/algorithms/`
- [ ] All BDD scenarios pass
- [ ] No warnings or deprecations

**Validation**:
```bash
pytest tests/ -v --cov=src --cov=../monorepo/agentic/algorithms/mcts --cov-report=html
behave tests/integration/
behave ../monorepo/agentic/tests/components/algorithms/
```

---

### T52: Update CLAUDE.md agent context
**Priority**: P2
**Estimate**: 10 minutes
**Dependencies**: T51
**User Story**: Documentation

**Description**:
Update project-level CLAUDE.md with completed feature technologies.

**Acceptance Criteria**:
- [ ] Run: `.specify/scripts/bash/update-agent-context.sh claude`
- [ ] Verify `CLAUDE.md` includes:
  - Python 3.9+ MCTS implementation
  - Ollama VLM integration patterns
  - Behave BDD testing for algorithms
  - instructor framework usage
- [ ] Commit updated CLAUDE.md

**Files Modified**:
- `CLAUDE.md`

---

## Execution Strategy

### Recommended Order

1. **Phase 1 (T1-T5)**: Complete setup first (critical path)
2. **Phase 2 (T6-T15)**: MCTS foundation (blocks US3)
3. **Parallel Execution**:
   - **Thread A**: Phase 3 (T16-T25) - Excel parser
   - **Thread B**: Phase 4 (T26-T30) - Template download
4. **Phase 5 (T31-T45)**: MCTS integration (requires Phase 2)
5. **Phase 6 (T46-T52)**: Polish and validation

### Critical Path

```
T1 → T2 → T3 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T31 → T32 → T33 → T34 → T35 → T36 → T38 → T39 → T41 → T42 → T43 → T49
```

**Critical Path Duration**: ~18 hours (excluding T49 wait time)

### Parallel Opportunities

- **After T14** (MCTS foundation complete):
  - US1 (T16-T25) can run independently
  - US2 (T26-T30) can run independently
- **Within Phase 5**:
  - T31-T35 (VLM evaluators) can partially overlap with T16-T30

---

## Risk Mitigation

### High-Risk Tasks

1. **T38: VLM accuracy validation** - May require prompt iteration if ±10px not met
   - **Mitigation**: Budget extra time for prompt engineering
2. **T39: Grid World validation** - Validates MCTS correctness before production
   - **Mitigation**: Catch algorithm bugs early before integrating with VLM
3. **T49: Performance validation** - 200-card batch may exceed 3-hour target
   - **Mitigation**: T50 profiling can identify optimizations

### Blockers

- **T2 (Ollama setup)**: Blocks all VLM-dependent tasks (T32, T34, T38, T49)
  - **Resolution**: Complete T2 early in Phase 1
- **Phase 2 (MCTS)**: Blocks entire Phase 5 (US3)
  - **Resolution**: Prioritize Phase 2, parallelize Phase 3/4

---

## Success Criteria Summary

**Feature Complete** when:
- [ ] All 52 tasks completed
- [ ] All unit tests passing (>90% coverage)
- [ ] All BDD scenarios passing
- [ ] Phase 0 validation (T38): VLM accuracy ±10px ✓
- [ ] Grid World validation (T39): Optimal path found ✓
- [ ] Performance validation (T49): 200 cards in 1-3 hours, ≥95% quality ≥0.8 ✓
- [ ] Final integration test (T51): All tests green ✓

**Ready for production** when all success criteria met.
