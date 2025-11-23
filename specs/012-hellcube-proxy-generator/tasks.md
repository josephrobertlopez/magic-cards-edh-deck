# Tasks: Hellcube Proxy Generator

**Input**: Design documents from `/specs/012-hellcube-proxy-generator/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

**Organization**: Tasks organized using **backwards-working methodology** (NFR-005):
- **Stream 1**: End-to-end pipeline (Excel → Template → Heuristic Compositor → Milestone 1)
- **Stream 2**: MCTS algorithm development (parallel with Stream 1)
- **Convergence**: MCTS integration after both streams complete

**Tests**: Optional - only included if explicitly requested (not requested in spec)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and environment configuration

- [x] T001 Create project structure (src/, tests/unit/, tests/integration/) at repository root
- [x] T002 Configure git submodule for monorepo access: `git submodule add <monorepo-url> monorepo && git submodule update --init --recursive`
- [x] T003 Verify monorepo imports work: `python -c "from monorepo.agentic.algorithms.base_algorithm import BaseAlgorithm"`
- [x] T004 Install Ollama VLM backend: `curl -fsSL https://ollama.com/install.sh | sh`
- [x] T005 Download llava:13b model: `ollama pull llama:13b` (~4GB)
- [x] T006 [P] Install Python dependencies (pandas, openpyxl, Pillow, requests, pydantic, instructor) via pip
- [x] T007 [P] Create cache directory structure (.cache/template_regions.json, .cache/templates/)
- [x] T008 [P] Setup pytest framework in tests/ with behave for BDD integration tests

**Checkpoint**: Environment ready - parallel streams can begin

---

## Stream 1: End-to-End Pipeline (Backwards from Goal)

**Goal**: Generate ONE complete proxy card from ONE Hellcube spreadsheet row using simple heuristic positioning (NO MCTS yet)

**Runs in parallel with Stream 2 after Phase 1 completes**

---

### Phase 2a: User Story 1 - Semantic Spreadsheet Parser (Priority: P1) [STREAM 1]

**Goal**: Extract structured card data from one row of Hellcube AJ.xlsx

**Independent Test**: Parse first card row from spreadsheet, verify all fields extracted correctly (name, types, abilities, mana cost, P/T, author)

#### Implementation for User Story 1

- [ ] T009 [P] [US1] Create Card data model in src/models/card.py (name, mana_cost, color, type, legendary, subtypes, abilities, flavor, power_toughness, author, artwork_url)
- [ ] T010 [P] [US1] Create ManaCost parser in src/parsers/mana_cost_parser.py (parse parenthetical notation: "(Bu,Bu)(1)" → {blue: 2, generic: 1})
- [ ] T011 [P] [US1] Create color inference logic in src/parsers/color_inference.py (Bu→blue, Rd→red, Gn→green, Wt→white, Bk→black, mixed→multicolor)
- [ ] T012 [US1] Create HellcubeExcelParser in src/parsers/hellcube_parser.py with dynamic adjacency detection (FR-001: detect field labels in columns 2-9, group by "AJ" markers)
- [ ] T013 [US1] Implement type extraction logic in hellcube_parser.py (FR-004a: extract primary type from "Types" field, FR-004b: detect "Legendary" keyword)
- [ ] T014 [US1] Implement P/T extraction in hellcube_parser.py (FR-004: parse "Stats" field, handle datetime format "2025-02-04" → "2/4")
- [ ] T015 [US1] Implement multi-text-row combination in hellcube_parser.py (FR-003: merge multiple "text" rows into ordered abilities list)
- [ ] T016 [US1] Add validation for required fields (FR-013: name, type required; warn on missing optional fields)

**Checkpoint**: Parser extracts one card from Hellcube AJ.xlsx with all fields

---

### Phase 2b: User Story 2 - Template Research & Download (Priority: P2) [STREAM 1]

**Goal**: Download ONE template matching first card's attributes (e.g., blue creature legendary)

**Independent Test**: Given card attributes (color=blue, type=Creature, legendary=True), download appropriate template file

**Runs in parallel with Phase 2a (US1) - different files**

#### Implementation for User Story 2

- [ ] T017 [P] [US2] Create TemplateMetadata model in src/models/template.py (color, card_type, legendary, file_path, sha256_hash)
- [ ] T018 [P] [US2] Implement fuzzy template matcher in src/matching/template_matcher.py (FR-008a: match "blue*creature*legend*.png" patterns with tolerance)
- [ ] T019 [US2] Create template research skill wrapper in src/skills/template_research.py (calls .claude/skills/html/ to search "MTG card template")
- [ ] T020 [US2] Create template download skill wrapper in src/skills/template_download.py (calls .claude/skills/http/download-file.md, filter ≥300 DPI, 750×1050px per FR-005)
- [ ] T021 [US2] Implement template caching logic in src/cache/template_cache.py (SHA-256 indexed, avoid re-downloads per FR-007)
- [ ] T022 [US2] Add concurrent batch download support (NFR-002: 10+ templates in parallel using asyncio/aiohttp)

**Checkpoint**: One template downloaded and cached for first card

---

### Phase 2c: Simple Heuristic Compositor (Priority: P3 Partial) [STREAM 1]

**Goal**: Composite first card onto template using HARDCODED/HEURISTIC positioning (NO MCTS)

**Independent Test**: Visual inspection - "Does this look like a Magic card?" with readable text

**Depends on T009-T016 (parser) and T017-T022 (templates)**

#### Implementation for Simple Compositor

- [ ] T023 [US3] Create SimpleLayoutEngine in src/layout/simple_heuristic.py with hardcoded positioning:
  - Name: centered at top (x=375, y=50)
  - Mana cost: top-right (x=650, y=50)
  - Type line: below name (x=50, y=150)
  - Abilities: left-aligned in text box (x=50, y=250)
  - P/T: bottom-right (x=650, y=950)
  - Flavor: bottom text box (x=50, y=850)
- [ ] T024 [US3] Create ProxyCompositor in src/compositor/proxy_compositor.py using Pillow for image composition (FR-011: 300 DPI, 750×1050px output)
- [ ] T025 [US3] Implement mana symbol rendering in src/rendering/mana_symbols.py (FR-010: Bu→blue icon, Rd→red icon, etc.)
- [ ] T026 [US3] Implement artwork download in src/download/artwork_downloader.py (FR-009: fetch from "pic" field URL, fail card on invalid URL, continue batch)
- [ ] T027 [US3] Create end-to-end orchestration script in src/proxy_generator.py (parse one row → download template → download artwork → composite → save PNG)

**🎯 MILESTONE 1: Single Proxy Card (Stream 1 Complete)**

**Acceptance Criteria**:
- [ ] T028 Run proxy_generator.py on FIRST ROW of Hellcube AJ.xlsx
- [ ] T029 Verify output PNG exists (750×1050px, 300 DPI)
- [ ] T030 Visual inspection: Name readable? Mana cost positioned correctly? Type line present? Abilities visible? P/T shown? (human validation)
- [ ] T031 Time measurement: Single card generation <5 seconds (heuristic positioning, no MCTS overhead)

**Expected Duration**: 8-12 hours (T001-T031)

---

## Stream 2: MCTS Algorithm Development (Parallel with Stream 1)

**Goal**: Implement and validate MCTS layout optimizer on Grid World problem, ready for integration

**Runs in parallel with Stream 1 (Phases 2a, 2b, 2c) after Phase 1 completes**

---

### Phase 3: Foundational MCTS Components (Priority: P0 - BLOCKS US3 MCTS Integration)

**Purpose**: Core MCTS algorithm infrastructure following academic standards

**⚠️ CRITICAL**: This phase enables MCTS integration in Phase 4 (replaces simple heuristics)

#### MCTS Data Structures & Algorithm

- [ ] T032 [P] Create Pydantic validation models in .claude/skills/helpers/pydantic_models.py:
  - LayoutState (placed_elements, remaining_elements, template_regions, quality_score)
  - MCTSNode (state, parent, children, visits, total_reward, untried_actions)
  - BoundingBox (x, y, width, height)
- [ ] T033 [P] Create TemplateRegions Pydantic model in .claude/skills/helpers/pydantic_models.py (name_box, mana_cost_box, type_line_box, text_boxes, pt_box, flavor_box)
- [ ] T034 [P] Create LayoutQuality Pydantic model in .claude/skills/helpers/pydantic_models.py (readability_score, convention_compliance, aesthetic_balance, overall_score, issues)
- [ ] T035 Create MCTSLayoutAlgorithm in src/mcts/mcts_algorithm.py inheriting BaseAlgorithm with execute(problem, on_trial=None, iteration_context=None, **kwargs) signature (extracts card_data, template_regions from kwargs)
- [ ] T036 Implement UCB1 selection in src/mcts/selection.py (formula: Q(node) + C√(ln(N_parent)/N_node), C=√2≈1.414, unvisited priority=∞)
- [ ] T037 Implement expansion phase in src/mcts/expansion.py (add one unexplored child per expansion)
- [ ] T038 Implement strategic action sampling in src/mcts/actions.py (8 positions: 4 corners + 4 midpoints, element-specific constraints, ~24 actions per element per FR-008)
- [ ] T039 Implement simulation/rollout in src/mcts/simulation.py (random policy to terminal state)
- [ ] T040 Implement backpropagation in src/mcts/backpropagation.py (update visits and rewards from leaf to root)
- [ ] T041 Add convergence criteria in src/mcts/convergence.py (max rollouts budget, score plateau detection, timeout)

#### VLM Integration for MCTS

- [ ] T042 [P] Create VLMTemplateDetector in src/vlm/template_detector.py using instructor.from_openai() with Ollama backend (detect template regions from image, output TemplateRegions Pydantic model)
- [ ] T043 [P] Create VLMLayoutEvaluator in src/vlm/layout_evaluator.py using instructor.from_openai() (score layout quality per rollout, output LayoutQuality Pydantic model with overall_score 0.0-1.0)
- [ ] T044 Implement base64 image encoding for VLM in src/vlm/image_encoding.py (OpenAI multimodal message pattern: {"type": "image_url", "image_url": {"url": "data:image/png;base64,{data}"}})
- [ ] T045 Add VLM caching for template regions in src/cache/template_cache.py (SHA-256 indexed, 92.5% call reduction: 15 templates vs 200 cards)
- [ ] T046 Configure Ollama backend switching in src/vlm/backend_config.py (BACKEND=ollama for production, BACKEND=test for fast iteration)

**Checkpoint**: MCTS algorithm complete, VLM integration ready

---

### Phase 3.5: Grid World Validation (Priority: P0 - VALIDATES MCTS)

**Goal**: Prove MCTS works on known-good test problem before applying to Hellcube

**Independent Test**: MCTS solves grid world pathfinding/layout problem with convergence

#### Grid World Test Problem

- [ ] T047 Create GridWorldProblem in tests/integration/grid_world/problem.py (simple 2D layout constraints, known optimal solution)
- [ ] T048 Implement grid world state representation in tests/integration/grid_world/state.py (compatible with LayoutState interface)
- [ ] T049 Create mock VLM evaluator for grid world in tests/integration/grid_world/evaluator.py (deterministic scoring, no actual VLM calls)
- [ ] T050 Write behave feature tests/integration/grid_world.feature (Given grid world problem, When MCTS runs, Then converges to optimal layout within N rollouts)
- [ ] T051 Run MCTS on grid world problem and verify convergence (≥70% convergence rate per plan.md performance goals)

**🎯 MILESTONE 2: MCTS Validated on Grid World (Stream 2 Complete)**

**Acceptance Criteria**:
- [ ] T052 Grid world problem solved by MCTS with ≥0.9 quality score
- [ ] T053 Convergence within 100 rollouts (much faster than Hellcube's 100-300 due to simpler state space)
- [ ] T054 UCB1 formula verified (proper exploration-exploitation balance)
- [ ] T055 Memory usage <10MB for grid world tree (validates tree pruning works)

**Expected Duration**: 10-15 hours (T032-T055)

---

## Convergence: MCTS Integration (After Both Streams Complete)

**Depends on**: Milestone 1 (Stream 1) AND Milestone 2 (Stream 2)

---

### Phase 4: User Story 3 - MCTS-Optimized Proxy Generation (Priority: P3 Full)

**Goal**: Replace simple heuristics with MCTS optimizer for production-quality layout

**Independent Test**: Generate proxy for first card with MCTS optimization, verify quality score ≥0.8

#### MCTS Integration Tasks

- [ ] T056 [US3] Integrate VLMTemplateDetector into template_cache.py (detect regions on first template load, cache by SHA-256)
- [ ] T057 [US3] Replace SimpleLayoutEngine with MCTSLayoutEngine in src/layout/mcts_layout_engine.py (calls MCTSLayoutAlgorithm.execute() with card_data and template_regions)
- [ ] T058 [US3] Update ProxyCompositor to use MCTS-optimized positions from MCTSLayoutEngine output
- [ ] T059 [US3] Add VLM layout quality validation in proxy_generator.py (verify final layout ≥0.8 score before saving)
- [ ] T060 [US3] Implement batch processing with progress reporting in src/batch/batch_processor.py (NFR-003: 200+ cards, show ETA based on 20-60s per card)
- [ ] T061 [US3] Create folder organization voting system in src/batch/folder_organizer.py (FR-012: multi-strategy voting - color/type vs type/color, select most-supported strategy)
- [ ] T062 [US3] Add error handling for invalid artwork URLs (FR-009: log error with card name + URL, fail card, continue batch)

**Checkpoint**: MCTS integration complete, single card optimized

---

### Phase 4.5: Batch Processing & Organization

**Goal**: Process full Hellcube (200+ cards) with dynamic folder organization

#### Batch Processing Tasks

- [ ] T063 [US3] Run batch processor on full Hellcube AJ.xlsx (200+ cards)
- [ ] T064 [US3] Verify folder organization strategy (validate multi-strategy voting selects optimal grouping)
- [ ] T065 [US3] Performance validation: Batch completes in 1-3 hours (200 cards × 20-60s avg, NFR-003)
- [ ] T066 [US3] Quality validation: ≥95% of cards have quality score ≥0.8 (SC-004, plan.md performance goals)
- [ ] T067 [US3] Convergence validation: ≥70% of cards converge before max rollout budget (plan.md performance goals)

**🎯 MILESTONE 3: Full Batch Processing Complete**

**Acceptance Criteria**:
- [ ] T068 200+ proxy PNGs generated in organized folders (blue/creatures/, planeswalkers/red/, etc.)
- [ ] T069 All images 750×1050px, 300 DPI, lossless PNG (NFR-004)
- [ ] T070 Total batch time 1-3 hours (within expected range)
- [ ] T071 Manual spot check: 10 random proxies visually inspected for quality

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and production readiness

- [ ] T072 [P] Update quickstart.md with final setup instructions (Ollama installation, model download, dependency install)
- [ ] T073 [P] Create usage documentation in docs/usage.md (CLI arguments, folder organization options, troubleshooting)
- [ ] T074 [P] Add performance profiling in src/profiling/profiler.py (identify MCTS bottlenecks, VLM call overhead)
- [ ] T075 Run quickstart.md validation (verify setup instructions work on fresh environment)
- [ ] T076 Security review: Sanitize user input (spreadsheet paths, artwork URLs to prevent injection)
- [ ] T077 Code cleanup: Remove debug logging, add proper error messages
- [ ] T078 Final validation: Re-run full Hellcube batch, verify ≥95% success rate (SC-001, SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Stream 1 (Phases 2a, 2b, 2c)**: Depends on Phase 1 completion → Milestone 1 (single proxy with heuristics)
- **Stream 2 (Phase 3, 3.5)**: Depends on Phase 1 completion → Milestone 2 (MCTS validated on grid world)
- **Convergence (Phase 4, 4.5)**: Depends on BOTH Milestone 1 AND Milestone 2 → Milestone 3 (full MCTS batch)
- **Phase 5 (Polish)**: Depends on Milestone 3

### Parallel Stream Coordination

```
Phase 1 (Setup)
     ├──────────────────┬──────────────────┐
     │                  │                  │
Stream 1            Stream 2          (PARALLEL)
Phase 2a (US1)      Phase 3 (MCTS)
Phase 2b (US2)      Phase 3.5 (Grid)
Phase 2c (Simple)
     │                  │
Milestone 1        Milestone 2
     │                  │
     └──────┬───────────┘
            │
      Phase 4 (MCTS Integration)
      Phase 4.5 (Batch)
            │
      Milestone 3
            │
      Phase 5 (Polish)
```

### User Story Dependencies

- **US1 (Parser)**: Can start after Phase 1 - NO dependencies on other stories
- **US2 (Templates)**: Can start after Phase 1 - Parallel with US1 (different files)
- **US3 (Proxy Gen)**: Depends on US1 (parser) AND US2 (templates) for Milestone 1, then depends on Milestone 2 (MCTS) for full implementation

### Within Each Phase

**Stream 1 (End-to-End)**:
- T009-T016 (US1 Parser): Sequential within parser, but T009-T011 can run in parallel (different files)
- T017-T022 (US2 Templates): T017-T018 parallel, then T019-T022 sequential
- T023-T027 (Simple Compositor): Sequential (depends on parser + templates)

**Stream 2 (MCTS)**:
- T032-T034 (Pydantic models): All parallel (different model files)
- T035-T041 (MCTS algorithm): Sequential (tree dependencies)
- T042-T046 (VLM integration): T042-T043 parallel, then T044-T046 sequential

### Parallel Opportunities

**Phase 1 (Setup)**:
- T006, T007, T008 can run in parallel

**Stream 1 - Phase 2a (US1)**:
- T009, T010, T011 can run in parallel (Card model, ManaCost parser, color inference - different files)

**Stream 1 - Phase 2b (US2)**:
- T017, T018 can run in parallel (TemplateMetadata model, fuzzy matcher - different files)

**Stream 2 - Phase 3 (MCTS)**:
- T032, T033, T034 can run in parallel (all Pydantic models - different classes)
- T042, T043 can run in parallel (VLMTemplateDetector, VLMLayoutEvaluator - different files)

**Phase 5 (Polish)**:
- T072, T073, T074 can run in parallel (documentation, profiling - different files)

**Cross-Stream Parallelization**:
- **ALL of Stream 1 (T009-T031) can run in parallel with ALL of Stream 2 (T032-T055)** after Phase 1 completes

---

## Parallel Example: Stream 1 + Stream 2 Simultaneous

```bash
# After Phase 1 completes, launch BOTH streams:

# Developer A (Stream 1 - End-to-End):
Task T009: "Create Card data model in src/models/card.py"
Task T010: "Create ManaCost parser in src/parsers/mana_cost_parser.py"
Task T011: "Create color inference in src/parsers/color_inference.py"
# ... continue through T031 (Milestone 1)

# Developer B (Stream 2 - MCTS):
Task T032: "Create LayoutState Pydantic model"
Task T033: "Create TemplateRegions Pydantic model"
Task T034: "Create LayoutQuality Pydantic model"
# ... continue through T055 (Milestone 2)

# When BOTH milestones complete, converge:
Task T056: "Integrate VLMTemplateDetector into template_cache.py"
# ... continue through Milestone 3
```

---

## Implementation Strategy

### Backwards-Working Methodology (NFR-005)

**Target**: Generate ONE proxy from ONE row, then work backwards to identify MCTS needs

**Stream 1 Strategy (Work Backwards from Goal)**:
1. **End Goal**: Print-ready proxy PNG (750×1050px, 300 DPI)
2. **← Work backwards**: Composite card data onto template (simple hardcoded positions)
3. **← Work backwards**: Load card template (blue creature legendary)
4. **← Work backwards**: Parse one spreadsheet row into Card object
5. **← Work backwards**: Load Hellcube AJ.xlsx, read single row

**Milestone 1 Deliverable**: End-to-end smoke test passing with hardcoded positioning (NO MCTS)

**Stream 2 Strategy (Forward Development in Parallel)**:
1. MCTS data structures (LayoutState, MCTSNode, BoundingBox)
2. VLM evaluators (template detection, layout quality scoring)
3. MCTS algorithm (selection, expansion, simulation, backpropagation)
4. Grid world validation (prove MCTS works on simple problem)
5. Integration point: Ready to replace hardcoded positioning

**Milestone 2 Deliverable**: MCTS validated on grid world, ready to drop into Stream 1

**Convergence Strategy**:
- When Stream 1 reaches "Composite with simple positioning"
- When Stream 2 reaches "MCTS validated on grid world"
- **Integration**: Replace `SimpleLayoutEngine` with `MCTSLayoutEngine` (T056-T059)

### MVP First (Milestone 1 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Stream 1: End-to-End (T009-T031)
3. **STOP and VALIDATE**: Milestone 1 - One proxy generated (human visual inspection)
4. Demo single-card output (proves pipeline works before MCTS investment)

**Time to MVP**: 8-12 hours

### Full Feature (All Milestones)

1. Complete Phase 1: Setup
2. **Parallel Launch**: Stream 1 + Stream 2 simultaneously
3. Validate Milestone 1: Single proxy with heuristics (8-12 hours)
4. Validate Milestone 2: MCTS on grid world (10-15 hours)
5. Converge: MCTS Integration (T056-T071) → Milestone 3
6. Polish: Documentation and validation (T072-T078)

**Total Time**: 30-40 hours

### Parallel Team Strategy

With two developers:

1. **Both**: Complete Phase 1 together (2-3 hours)
2. **Split streams**:
   - **Developer A**: Stream 1 (US1 Parser + US2 Templates + Simple Compositor) → Milestone 1
   - **Developer B**: Stream 2 (MCTS + VLM + Grid World) → Milestone 2
3. **Both**: Converge at Phase 4 (MCTS Integration) → Milestone 3
4. **Both**: Phase 5 (Polish and validation)

---

## Notes

- **[P] markers**: Different files, no dependencies - can run in parallel
- **[Story] labels**: Map tasks to user stories (US1=Parser, US2=Templates, US3=Proxy Generation)
- **Backwards-working (NFR-005)**: Stream 1 works backwards from end goal (one proxy), Stream 2 develops MCTS in parallel
- **Early validation**: Milestone 1 proves pipeline viability BEFORE investing 10-15 hours in MCTS
- **Risk reduction**: If MCTS proves too complex, fall back to heuristic positioning (Milestone 1 is functional output)
- **Independent milestones**: Each milestone has concrete deliverable and acceptance criteria
- **No test tasks**: Tests not explicitly requested in spec.md, following template guidance
- **Commit frequently**: After each task or logical group
- **Stop at checkpoints**: Validate independently before proceeding
