# Implementation Plan: Hellcube Proxy Generator

**Branch**: `012-hellcube-proxy-generator` | **Date**: 2025-11-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-hellcube-proxy-generator/spec.md`

**Note**: This plan reflects the comprehensive design in Documents 01-09, incorporating MCTS layout optimization with VLM evaluation, strategic action sampling, and monorepo integration patterns.

## Summary

Generate print-ready MTG proxy cards from unstructured Hellcube spreadsheet data using:
1. **Semantic Excel Parser**: Extract card data (name, type, abilities, mana cost) from unstructured spreadsheet cells using dynamic adjacency detection
2. **Template Research & Download**: Fetch MTG card templates for all color/type combinations using domain-agnostic HTTP skills
3. **MCTS Layout Optimization**: Position card elements optimally using Monte Carlo Tree Search with VLM-guided evaluation (academic standard MCTS from Browne et al. 2012, Kocsis & Szepesvári 2006 UCB1)
4. **Batch Processing**: Generate 200+ proxies at 300 DPI with dynamic folder organization

**Key Innovation**: First application of MCTS+VLM hybrid for layout optimization, eliminating manual template coordinate measurement via dynamic region detection.

## Technical Context

**Language/Version**: Python 3.9+ (existing codebase standard, from CLAUDE.md)
**Primary Dependencies**:
- pandas, openpyxl (Excel parsing)
- Pillow/PIL (image compositing, text rendering)
- requests (HTTP template downloads)
- Ollama + llava-1.5 model (local VLM backend, ~4GB)
- python-pptx (existing, for grid layouts if needed)
- Pydantic (structured output validation)
- instructor (VLM structured generation framework)
- Existing monorepo: `../monorepo/agentic/` (BaseAlgorithm, PerceptInterface, Instructor)

**Storage**: File-based
- Input: `Hellcube AJ.xlsx` (200+ cards)
- Templates: Downloaded PNG files (750×1050px, 300 DPI)
- Cache: `.cache/template_regions.json` (VLM-detected regions, SHA-256 indexed)
- Output: Organized PNG proxies (`blue/creatures/`, `planeswalkers/red/`, etc.)

**Testing**: pytest (unit), behave (BDD integration)
- Unit: MCTS algorithm components, VLM evaluators, Excel parser
- BDD: End-to-end scenarios (simple card convergence, complex card, batch processing)
- Grid World validation (known-good MCTS test problem)
- Phase 0 validation: VLM accuracy (±10px vs ground truth Nala card)

**Target Platform**: Linux (primary), macOS (development)
**Project Type**: CLI batch processor + library modules
**Performance Goals**:
- **Per Card**: 20-60 seconds (100-300 VLM calls × 0.2s each + MCTS overhead)
- **Batch 200 cards**: 1-3 hours total
- **Quality**: ≥0.8 VLM score for 95%+ of cards
- **Convergence**: 70%+ of cards converge before max rollout budget

**Constraints**:
- **VLM Latency**: 0.2s per evaluation (Ollama local inference)
- **Action Space**: ~24 actions per element (strategic sampling: 8 positions × 3 font sizes × 1 alignment)
- **Memory**: <50MB MCTS tree per card, <200MB total for batch processing
- **Zero API Costs**: Local Ollama VLM (no cloud dependency)

**Scale/Scope**:
- 200+ cards (Hellcube dataset)
- 8-15 unique templates (creature, planeswalker, artifact, etc. × colors)
- 5-8 elements per card (name, mana_cost, type_line, abilities, P/T, flavor)
- ~20,000 total VLM evaluations per 200-card batch

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution file found at `.specify/memory/constitution.md`. Proceeding with standard software engineering principles:

✅ **Simplicity**: MCTS chosen over simpler heuristics because:
- Problem has 10²⁰ state space (heuristics fail on edge cases)
- Sequential dependencies (name → mana → type → abilities → P/T → flavor)
- Variable structure (1-3 abilities, optional flavor)
- Delayed evaluation (quality only assessable when complete)

✅ **Necessity**: VLM every rollout (not two-phase) justified because:
- User explicitly chose Option A (VLM every rollout) in clarification
- Prioritizes layout quality over speed (1-3hr acceptable for 200 cards)
- Enables accurate gradient for UCB1 tree exploration

✅ **Testability**: Incremental validation strategy (Phase 0 → Grid World → Production)

✅ **Maintainability**: Follows existing monorepo patterns (BaseAlgorithm, Reflexion template)

## Project Structure

### Documentation (this feature)

```text
specs/012-hellcube-proxy-generator/
├── spec.md                                    # Feature specification (COMPLETE)
├── plan.md                                    # This file (IN PROGRESS)
├── 01-Problem-And-Design-Rationale.md        # MCTS justification (COMPLETE)
├── 02-Monorepo-Code-Structure.md             # Integration patterns (COMPLETE)
├── 03-MCTS-Implementation-Spec.md            # Algorithm details (COMPLETE)
├── 04-Testing-Integration-Deployment.md      # Test strategy (COMPLETE)
├── 05-Critical-Issues-Resolution.md          # Blocker resolutions (COMPLETE)
├── 06-Adversarial-Review-And-Final-Spec.md   # Red team analysis (COMPLETE)
├── 07-Phase-0-Validation-And-Go-Decision.md  # Grounded validation plan (COMPLETE)
├── 08-Hellcube-Spreadsheet-Analysis.md       # Real Excel structure (COMPLETE)
├── 09-Card-Template-Analysis.md              # Real template measurements (COMPLETE)
├── research.md                                # Phase 0 output (TO BE GENERATED)
├── data-model.md                              # Phase 1 output (TO BE GENERATED)
├── quickstart.md                              # Phase 1 output (TO BE GENERATED)
├── contracts/                                 # Phase 1 output (TO BE GENERATED)
└── tasks.md                                   # Phase 2 output (/speckit.tasks - NOT YET)
```

### Source Code (repository root)

```text
# This feature lives in the magic-cards-edh-deck repo (current repo)
# BUT references monorepo at ../monorepo/agentic/

magic-cards-edh-deck/
├── .claude/
│   └── skills/                          # Domain-agnostic skills (existing)
│       ├── http/                        # Template downloads
│       ├── html/                        # Template research
│       └── document/                    # Presentation generation
├── src/
│   ├── hellcube_parser.py              # NEW: Excel parsing with adjacency detection
│   ├── mana_cost_parser.py             # NEW: Mana notation → symbols
│   ├── template_matcher.py             # NEW: Fuzzy filename matching
│   ├── proxy_compositor.py             # NEW: PIL-based image composition
│   └── batch_organizer.py              # NEW: Multi-strategy voting for folder structure
├── tests/
│   ├── unit/
│   │   ├── test_hellcube_parser.py     # NEW: Excel parsing tests
│   │   ├── test_mana_cost_parser.py    # NEW: Mana notation tests
│   │   └── test_template_matcher.py    # NEW: Fuzzy matching tests
│   └── integration/
│       ├── hellcube_parsing.feature    # NEW: BDD for end-to-end parsing
│       └── proxy_generation.feature    # NEW: BDD for full workflow
└── Hellcube AJ.xlsx                     # Input data (existing)

../monorepo/agentic/                     # Referenced monorepo (accessed via git submodule)
├── algorithms/
│   ├── base_algorithm.py                # IMPORTED: BaseAlgorithm interface
│   └── (other algorithms)               # EXISTING: chain_of_thought, react, reflexion, tree_of_thought
├── core/
│   ├── interfaces/
│   │   └── percept_interface.py         # EXISTING: VLM backend integration (optional)
│   └── utils/
│       └── instructor.py                # IMPORTED: Structured output framework
└── (tests in monorepo not shown)
```

**Structure Decision** (**REVISED AFTER AUDIT**):
- **MCTS Implementation Location**: MCTS implemented **directly in Feature 012** (`magic-cards-edh-deck/src/mcts/`), NOT in monorepo
- **Monorepo Access**: Via git submodule - imports BaseAlgorithm interface and instructor framework only
- **Rationale**: Audit revealed monorepo MCTS doesn't exist (phantom dependency). Feature 012 implements MCTS natively to avoid blocking. If monorepo MCTS needed later, extract from Feature 012 after validation.
- **Integration**: MCTS imports `BaseAlgorithm` from `monorepo.agentic.algorithms.base_algorithm` (via git submodule)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| VLM every rollout (100-300 calls/card, 1-3hr for 200 cards) | User explicitly chose this in clarification for maximum layout quality | Two-phase evaluation (heuristic MCTS + VLM top-5) rejected - user prioritizes quality over speed |
| MCTS algorithm (complex tree search) | Problem has 10²⁰ state space, sequential dependencies, delayed evaluation | Simple heuristics fail on edge cases (long text, unusual combinations); GA/DRL require training data |
| Strategic action sampling (8 positions vs full grid) | Reduces action space from 49,140 to 24 per element for tractability | Full 10px grid enumeration causes combinatorial explosion (50M node trees) |

---

## Phase 0: Research & Unknowns Resolution

**Status**: TO BE GENERATED

**Research Tasks** (all NEEDS CLARIFICATION items resolved via existing Documents 01-09):

1. ✅ **MCTS Algorithm Design** → Document 03 (MCTS-Implementation-Spec.md)
   - UCB1 formula, four phases, convergence criteria
   - Academic standards: Browne et al. 2012, Kocsis & Szepesvári 2006

2. ✅ **VLM Integration Pattern** → Documents 05, 07, 09
   - Template region detection (one-time, SHA-256 cached)
   - Layout quality scoring (per rollout)
   - Ollama backend setup, instructor framework integration

3. ✅ **Action Space Reduction** → Document 05 (Critical-Issues-Resolution.md)
   - Strategic sampling: 8 positions (4 corners + 4 midpoints)
   - Element-specific constraints (name=center only, abilities=left only)
   - Reduces from 49,140 → 24 actions per element

4. ✅ **Excel Parsing Strategy** → Document 08 (Hellcube-Spreadsheet-Analysis.md)
   - Multi-column vertical layout with "AJ" markers
   - Column A labels define field boundaries
   - Embedded image extraction, mana cost parsing

5. ✅ **Template Ground Truth** → Document 09 (Card-Template-Analysis.md)
   - Nala card measurements (750×1050px, 6 regions)
   - VLM detection tolerance: ±10px
   - Template caching: 92.5% VLM call reduction (15 unique templates vs 200 cards)

6. ✅ **Monorepo Integration** → Document 02, 07 (Monorepo-Code-Structure, Phase-0-Validation)
   - BaseAlgorithm pattern (SUPPORTS_ITERATION=False)
   - Reflexion template structure
   - Behave testing with iteration_context

**Output**: `research.md` (will consolidate above findings with decisions/rationale/alternatives)

---

## Phase 1: Design Artifacts

**Status**: TO BE GENERATED

### Data Model (`data-model.md`)

Key entities from spec:
- **Card**: name, mana_cost, color (inferred), type, legendary, subtypes, abilities[], flavor, power_toughness, author, artwork_url
- **LayoutState**: placed_elements[], remaining_elements[], template_regions{}, quality_score
- **MCTSNode**: state, parent, children[], visits, total_reward, untried_actions[]
- **TemplateRegions**: name_box, mana_cost_box, type_line_box, text_boxes[], pt_box, flavor_box (Pydantic BaseModel)
- **LayoutQuality**: readability_score, convention_compliance, aesthetic_balance, overall_score, issues[] (Pydantic BaseModel)

### API Contracts (`contracts/`)

This is a CLI batch processor, not a web API. Contracts will define:
- **Python module interfaces** (not REST endpoints):
  - `HellcubeExcelParser.parse_excel(path) → List[Card]`
  - `MCTSLayoutAlgorithm.execute(problem, card_data, template_regions) → Result`
  - `VLMTemplateDetector.detect_regions(template_path) → TemplateRegions`
  - `VLMLayoutEvaluator.score_layout(layout_state) → float`

- **Pydantic schemas** for structured validation

### Quickstart (`quickstart.md`)

- **Setup**: Install Ollama, download llava-1.5 model, install Python dependencies
- **Run**: `python -m src.proxy_generator Hellcube\ AJ.xlsx`
- **Validate**: Phase 0 tests (VLM accuracy on Nala card, Grid World MCTS convergence)
- **Debug**: BACKEND=test for fast iteration without VLM

### Agent Context Update

Will run `.specify/scripts/bash/update-agent-context.sh claude` to add:
- Python 3.9+ MCTS implementation patterns
- Ollama VLM integration
- Behave BDD testing for algorithms
- instructor framework structured output

---

## Next Steps

1. ✅ **Phase 0 Complete** (via Documents 01-09): All technical unknowns researched
2. 🔄 **Generate research.md**: Consolidate findings from Documents 01-09
3. 🔄 **Generate data-model.md**: Extract entities and schemas
4. 🔄 **Generate contracts/**: Define Python module interfaces and Pydantic schemas
5. 🔄 **Generate quickstart.md**: Setup and validation instructions
6. ⏭️ **Phase 2** (separate command): `/speckit.tasks` to generate tasks.md

**Command ends here** - implementation planning complete through Phase 1 design.
