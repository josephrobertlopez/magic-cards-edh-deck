# Feature Specification: Hellcube Proxy Generator

**Feature Branch**: `008-hellcube-proxy-generator`
**Created**: 2025-11-15
**Status**: Draft
**Input**: User description: "Use our domain-agnostic skills to research and download various MTG card templates for proxying purposes. Convert the unstructured Hellcube spreadsheet data into structured card information using semantic reasoning to recognize cell patterns and group for labeling, then generate proxy cards."

## Clarifications

### Session 2025-11-15

- Q: How should the parser infer card attributes not explicitly labeled (color, legendary status, primary type)? → A: Full inference using heuristics (color from mana cost symbols, legendary status from "Legendary" keyword in Types field, primary card type from first word after dash in Types field, supertypes/subtypes from Types parsing)

- Q: Which template frame styles should be downloaded for multicolor cards and card variety? → A: Download all frames for all card types possible, focusing on most common styles (historic frames, creatures, standard layouts) - exclude full art and fancy specialty variants

- Q: How should text positioning work when compositing card data onto templates? → A: Use image analysis/OCR to dynamically detect text box boundaries in each template, combined with fuzzy filename matching for template selection (e.g., match "blue_creature" pattern variations)

- Q: What should happen when card artwork URLs (pic field) are invalid, unreachable, or return non-image content? → A: Fail proxy generation for that specific card, log error with card name and URL, continue processing remaining cards (all cards are custom, no fallback artwork sources available)

- Q: How should batch organization of generated proxies prioritize folder grouping (color vs type)? → A: Use multi-strategy voting to dynamically determine optimal grouping: generate candidate strategies (color/type, type/color, etc.), score each card's fit to each strategy, select most-supported strategy (e.g., if 80% creatures vote for color-first, use that; if evenly distributed, use type/color)

- Q: How should the parser handle spatial relationships between field labels and values in cells? → A: Use dynamic cell matching with adjacency detection - field values are in literally adjacent/neighboring cells to their labels but may have positional offset, requiring proximity-based matching rather than fixed row/column assumptions

- Q: What architectural pattern should MCTS implementation follow for consistency with existing monorepo algorithms? → A: Follow Reflexion algorithm template structure (BaseAlgorithm inheritance, instructor-based, similar behave testing patterns, stateless execution with iteration_context support)

- Q: Which backend should be used for template image analysis and MCTS layout optimization to minimize compute costs? → A: Use VLM (Vision Language Model) with Ollama for compute offloading (template region detection, text box boundary analysis, layout quality scoring), leveraging existing monorepo utilities (PerceptInterface, Instructor framework)

- Q: What is the ideal testing pattern for fast feedback on tractability of VLM + MCTS integration? → A: Incremental validation: (1) Test VLM integration with Reflexion algorithm first (validate VLM+instructor works), (2) Write MCTS algorithm following Reflexion template, (3) Write behave tests for MCTS to audit correctness, (4) Test MCTS on grid world domain (known good test case with simple layout constraints), (5) Apply to Hellcube Excel use case (production problem)

### Session 2025-11-16

- Q: The implementation reference shows VLM called on every rollout during simulation (potentially 100-300 calls per card), but Document 05 specifies a two-phase evaluation (heuristic MCTS + VLM top-5 only). Which VLM evaluation strategy should be implemented? → A: VLM every rollout - call VLM to score layout quality during each MCTS simulation phase (100-300 VLM evaluations per card for highest quality optimization)

- Q: The implementation reference generates actions using a 10px position grid across entire regions, 7 font sizes, and 3 alignments, creating ~49,140 actions per element (intractable for MCTS). How should action space be constrained? → A: Strategic sampling (8 strategic positions: 4 corners + 4 midpoints) with element-specific constraints (name=center only, abilities=left only, mana_cost=right only, 1-3 font size options per element type) reducing to ~24 actions per element for computational tractability

- Q: Does the MCTS algorithm implementation follow proper academic standards from canonical MCTS literature? → A: Yes - follows canonical MCTS from Browne et al. (2012) "A Survey of Monte Carlo Tree Search Methods" and Kocsis & Szepesvári (2006) UCB1 bandit algorithm. Four phases: (1) Selection via UCB1 formula [Q(node) + C√(ln(N_parent)/N_node)] with C=1.414 and unvisited nodes priority=∞, (2) Expansion adding one unexplored child, (3) Simulation via random rollout to terminal state + VLM evaluation, (4) Backpropagation updating visit counts and total rewards from leaf to root

- Q: How should MCTSLayoutAlgorithm.execute() signature conform to BaseAlgorithm protocol requirements (on_trial, iteration_context parameters)? → A: Add on_trial and iteration_context parameters to execute() signature matching Reflexion pattern, extract card_data and template_regions from kwargs. MCTS ignores these parameters (SUPPORTS_ITERATION=False) but must accept them for protocol conformance. Signature: execute(problem, on_trial=None, iteration_context=None, **kwargs) where kwargs contains card_data and template_regions

- Q: How should VLM evaluators pass images to instructor framework for template detection and layout scoring? → A: Use standard OpenAI multimodal message pattern with base64-encoded images in messages[].content array. Load image file, encode to base64, pass as {"type": "image_url", "image_url": {"url": "data:image/png;base64,{base64_data}"}} alongside text prompt. Works with existing instructor.from_openai() without modifying monorepo InstructorFramework

- Q: Should the Excel parser spec specify exact columns (C, E, G, I) or use imprecise range (columns 2-9) and let implementation discover pattern? → A: Keep current "columns 2-9" description - implementation will discover that cards are in columns C, E, G, I with empty spacing columns between them through dynamic adjacency detection. Parser should iterate columns and skip empty ones rather than hardcoding specific column indices

- Q: How should FR-012 folder organization voting work - what does "Markov tree voting algorithm" mean concretely? → A: Generate multiple candidate folder organization strategies (color/type, type/color, multicolor-separate, etc.), then for each card vote which strategy it fits best. Select the most-filled/supported strategy as winner. Optionally present top 2-3 strategies to user for final refinement. Remove "Markov tree" terminology - use multi-strategy voting with card-level fit scoring instead

### Session 2025-11-22

- Q: For Feature 012's Pydantic data structures (LayoutState, MCTSNode, TemplateRegions, LayoutQuality), should the implementation reuse validation infrastructure from branch 013 (update-presentations)? → A: **REVISED AFTER AUDIT** - No, implement Pydantic models natively in Feature 012 (de-coupled from branch 013). Branch 013's validation files do not exist yet, creating phantom dependency that blocks Phase 5 implementation.

- Q: Option A (directly import branch 013's validation infrastructure) creates a dependency on branch 013. How should Feature 012 obtain these files? → A: **SUPERSEDED** - Not applicable, Feature 012 implements its own Pydantic validation models following defense-in-depth pattern (Layer 1: Python self-validation, Layer 2: bash wrapper re-validation) inspired by branch 013's design but independent implementation

- Q: The spec states MCTS implementation goes in `../monorepo/agentic/algorithms/mcts/`. This creates a cross-repository dependency (Feature 012 in magic-cards-edh-deck repo modifying monorepo). Should MCTS actually live in the monorepo? → A: Implement MCTS code in monorepo first (../monorepo/agentic/algorithms/mcts/), then copy the implementation to magic-cards-edh-deck repo for Feature 012 to use independently (monorepo has canonical version, Feature 012 has local copy without cross-repo dependency)

- Q: MCTS depends on monorepo's instructor framework and BaseAlgorithm. If MCTS is copied locally, should these dependencies also be copied? → A: Use git submodule for monorepo (keeps live link to monorepo utilities like instructor.py and base_algorithm.py without full duplication, while MCTS code lives locally in src/mcts/)

- Q: Feature 012 needs to research and download MTG templates. Should it use existing domain-agnostic skills from .claude/skills/ (http/, html/, document/ folders)? → A: Yes - reuse existing skills from .claude/skills/http/ and .claude/skills/html/ for template research/download (proven, tested, consistent with feature description)

- Q: The previous session cherry-picked branch 013's validation files. Should Feature 012 also analyze branch 013's skill orchestration pipeline code to understand execution patterns? → A: **REVISED AFTER AUDIT** - Yes, analyze branch 013's orchestration patterns via git worktree for inspiration, but implement Feature 012-specific orchestration independently (avoids dependency on branch 013's incomplete work)

- Q: After analyzing branch 013's skill orchestration pipeline via git worktree, how should Feature 012 orchestrate its own domain-agnostic skills (template research, download, caching)? → A: **REVISED AFTER AUDIT** - Implement lightweight bash orchestration for Feature 012's skills (simple sequential execution with error handling), inspired by branch 013 patterns but independent. Defer complex orchestration framework until proven necessary.

### Session 2025-11-22 (Audit Corrections)

- Q: **AUDIT FINDING** - Branch 013's validation files (.claude/skills/helpers/*.py) do not exist yet. How should Feature 012 implement Pydantic validation? → A: Implement Pydantic models natively in Feature 012 (de-coupled). Add ~2 hours to Phase 2 for validation infrastructure development following defense-in-depth pattern.

- Q: **AUDIT FINDING** - MCTS algorithm doesn't exist in monorepo yet (/monorepo/agentic/algorithms/mcts/ is missing). Should Feature 012 wait for monorepo implementation? → A: Implement MCTS directly in Feature 012 (src/mcts/) without monorepo dependency. If monorepo MCTS is needed later, extract from Feature 012 after validation.

- Q: **AUDIT FINDING** - Git submodule setup steps missing from tasks.md. How should Feature 012 access monorepo utilities (BaseAlgorithm, instructor)? → A: Use git submodule with explicit setup documentation. Add T0 (environment smoke test) and update T1 (configure submodule) to tasks.md with clear instructions.

- Q: **DEVELOPMENT STRATEGY** - Should Feature 012 development work forwards (Excel parse → templates → MCTS → proxies) or backwards from end goal? → A: Work backwards from single Hellcube row as end goal while developing MCTS in parallel. Target: Generate one proxy card from one spreadsheet row, then identify what MCTS components are needed to achieve that goal. Enables parallel work streams: (1) End-to-end pipeline development, (2) MCTS algorithm development, converging when MCTS integration point is reached.

### Session 2025-11-22 (Implementation)

- Q: How should the parser discover card group boundaries when vertical spacing varies (9-12 rows between groups in Hellcube AJ.xlsx)? → A: **IMPLEMENTATION INNOVATION** - Parser uses Monte Carlo Tree Search (MCTS) for card group boundary discovery, treating parsing as a search problem. State: current row position + discovered card groups. Actions: skip N rows or extract card at current position. Greedy heuristic: 20-row look-ahead to find next "name" row, prioritize extraction when at name row. Achieves 100% discovery rate (17/17 groups) on Hellcube dataset with variable spacing. Boundary detection: stop parsing when encountering second "name" row (indicates next card group start). Implementation in `src/parsers/mcts_parser.py` with integration in `src/parsers/hellcube_parser.py`. Performance: 59/60 cards extracted (98.3% success, 1 failure due to source data missing Types field).

- Q: How should the system verify NFRs (NFR-001 parsing time <30s, NFR-003 per-card time 20-60s) are met during batch processing? → A: Implement progress reporting with timing metrics logged to stdout and optionally to file. Log: (1) Parsing phase duration for NFR-001 validation, (2) Per-card processing time for NFR-003 validation, (3) Total batch duration, (4) MCTS convergence metrics (rollouts used, final quality score). Output format: timestamped progress lines (e.g., "[2025-11-22 14:30:15] Card 42/200: Batman Blue - 45.2s, quality=0.85, converged after 127 rollouts"). Enables post-run NFR validation via log analysis without separate monitoring infrastructure.

- Q: Should the codebase use centralized logging infrastructure (logger.py module, Python logging library) or simple print() statements for progress reporting? → A: KISS principle - use simple print() statements directly in each module (parser, MCTS, compositor). No centralized logging infrastructure. Each component prints timestamped progress to stdout when significant milestones occur. Redirect stdout to file if needed using shell redirection (`python proxy_generator.py > run.log`). Avoid premature abstraction.

- Q: Where should Feature 012 code live - entirely in `magic-cards-edh-deck/src/`, split between repos, or migrated to monorepo? → A: All Feature 012 code lives in `magic-cards-edh-deck/src/` (parsers, models, MCTS, VLM, compositor, batch processing). Import shared monorepo utilities via git submodule at `monorepo/` for BaseAlgorithm interface and instructor framework only - no code duplication. Feature 012 remains self-contained and independently runnable in its own repository. Aligns with backwards-working methodology and audit-corrected architecture (MCTS implemented directly in Feature 012, not in monorepo).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Semantic Spreadsheet Parser (Priority: P1)

As a cube curator, I want the system to automatically understand and extract card data from my unstructured Hellcube spreadsheet, so that I don't have to manually restructure hundreds of card entries into a specific format.

**Why this priority**: This is the foundational capability - without parsing the spreadsheet, we can't generate any proxies. This delivers immediate value by converting messy human-readable data into machine-processable structures.

**Independent Test**: Can be fully tested by providing the Hellcube AJ.xlsx file and verifying that the system extracts all cards with their name, types, text abilities, flavor text, mana cost, power/toughness, and author information correctly grouped by card.

**Acceptance Scenarios**:

1. **Given** a spreadsheet with card data spread across multiple rows with field labels (name, Types, text, flavor, Stats, Author), **When** the parser processes it, **Then** each card is extracted as a structured object with all fields correctly associated
2. **Given** a card with multiple "text" rows containing different abilities, **When** parsing occurs, **Then** all ability texts are combined into a single ordered list for that card
3. **Given** a card name containing mana symbols in parentheses like "Batman Blue (Bu,Bu)(1)", **When** parsing occurs, **Then** the mana cost is extracted separately from the card name

---

### User Story 2 - MTG Template Research & Download (Priority: P2)

As a proxy generator, I want to automatically research and download professional-quality MTG card templates from online sources, so that my proxies look authentic and printable.

**Why this priority**: High-quality templates make the difference between amateur-looking proxies and professional print-ready cards. This can run independently after we know what card types we need (creatures, planeswalkers, artifacts, lands).

**Independent Test**: Can be tested independently by providing a list of required card frame types (e.g., "blue creature", "legendary planeswalker", "artifact land") and verifying that the system downloads appropriate templates for each type.

**Acceptance Scenarios**:

1. **Given** a need for creature card templates, **When** the system researches MTG templates online, **Then** it downloads high-resolution creature frames for all color combinations found in the Hellcube
2. **Given** special card types like "Legendary Planeswalker" or "Artifact Land", **When** template research occurs, **Then** the correct specialty frames are identified and downloaded
3. **Given** templates already exist locally, **When** the download process runs, **Then** existing templates are reused without re-downloading

---

### User Story 3 - Proxy Card Generation (Priority: P3)

As a cube owner, I want to generate print-ready proxy cards by combining my card data with professional templates, so that I can print physical copies for gameplay.

**Why this priority**: This is the final output step that delivers the tangible product. It depends on having both parsed card data (US1) and templates (US2), so it comes last in priority.

**Independent Test**: Can be tested by providing structured card data and templates, then verifying that generated proxy images have correctly positioned text, images, mana symbols, and are print-ready at 300 DPI.

**Acceptance Scenarios**:

1. **Given** a parsed card with name, type, abilities, and stats, **When** proxy generation runs, **Then** a print-ready image is created with all card elements properly positioned on the template
2. **Given** a card with custom artwork URLs in the "pic" field, **When** generating proxies, **Then** the artwork is downloaded and composited onto the card template
3. **Given** 200+ cards in the Hellcube, **When** batch proxy generation runs, **Then** all cards are generated and organized by color/type for easy printing

---

### Edge Cases

- **What happens when a spreadsheet cell contains merged data or formatting?**
  - Parser extracts raw text values, ignoring Excel formatting, and uses semantic heuristics (keywords like "name:", "text:", field position patterns) combined with dynamic adjacency detection to group related cells (field values are in neighboring cells with potential positional offset)

- **How does the system handle cards with incomplete data (missing flavor text, missing power/toughness)?**
  - Required fields (name, type) cause validation warnings; optional fields (flavor, author) are left blank on the proxy card template

- **What happens when template URLs are broken or images are unavailable?**
  - System falls back to local template library if available; if unavailable, generates placeholder frames with solid color backgrounds matching card colors

- **What happens when card artwork URLs (pic field) are invalid or unreachable?**
  - Proxy generation fails for that specific card with logged error (card name + URL), but processing continues for remaining cards since all artwork is custom with no fallback sources

- **How does the system handle unusual mana costs or hybrid mana symbols?**
  - Mana cost parser recognizes standard notation (Bu, Rd, Gn, Wt, Bk, Cl) and converts to standard MTG symbols; unrecognized symbols are rendered as text

- **What happens when card text contains special MTG keywords like "Deathtouch", "Flash", "Kicker"?**
  - Text is rendered as-is on the card; optionally, keyword abilities can be bolded or icon-decorated if template supports it

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse unstructured Excel spreadsheet data by detecting semantic patterns (field labels like "name", "Types", "text", "flavor", "Stats", "Author") and grouping related rows into card objects, using hybrid horizontal-vertical detection (4 cards per row across columns 2-9, with vertical field label grouping) combined with dynamic adjacency-based cell matching (field values in neighboring cells to labels with potential positional offset)

- **FR-002**: System MUST extract mana costs from card names by parsing parenthetical notation (e.g., "(Bu,Bu)(1)" means two blue mana plus one generic mana) and infer card color from mana symbols (Bu→blue, Rd→red, Gn→green, Wt→white, Bk→black, Cl→colorless, mixed symbols→multicolor)

- **FR-003**: System MUST combine multiple "text" field rows for a single card into an ordered list of abilities

- **FR-004**: System MUST extract power/toughness from "Stats" fields formatted as datetime objects or text (e.g., "2/4", or parse from dates like "2025-02-04" as "2/4")

- **FR-004a**: System MUST infer primary card type (Creature, Planeswalker, Artifact, Enchantment, Instant, Sorcery, Land) from the Types field by extracting the first word after the dash (e.g., "Creature- Human, Batman" → primary_type="Creature", subtypes=["Human", "Batman"])

- **FR-004b**: System MUST detect legendary status by checking for the "Legendary" keyword prefix in the Types field (e.g., "Legendary Planeswalker" → legendary=True)

- **FR-005**: System MUST research and identify MTG card template sources by searching for "MTG card template", "Magic card blank", or "MTG proxy template" and filtering for high-resolution images (minimum 300 DPI, 750x1050 pixels)

- **FR-006**: System MUST download card templates for all color combinations present in the Hellcube (blue, black, green, red, white, colorless, multicolor) plus all dual-color pairs (WU, UB, BR, RG, GW, WB, UR, BG, RW, GU)

- **FR-007**: System MUST download templates for all standard card types (creatures, planeswalkers, artifacts, enchantments, lands, instants, sorceries) and specialty variants (legendary creatures, legendary planeswalkers, artifact creatures, enchantment creatures), prioritizing historic/standard frame styles and excluding full-art or showcase variants

- **FR-008**: System MUST generate proxy card images by compositing card data onto templates with proper text positioning (name, type line, rules text box, flavor text, power/toughness), using VLM (Vision Language Model) via Ollama to detect template regions, then Monte Carlo Tree Search (MCTS) with VLM-guided evaluation on every rollout (100-300 VLM calls per card) and strategic action sampling (8 strategic positions per region: 4 corners + 4 midpoints, element-specific font/alignment constraints reducing to ~24 actions per element) to optimize element placement within detected boundaries for maximum readability and MTG convention compliance

- **FR-008a**: System MUST use fuzzy filename matching to select appropriate templates based on card attributes (e.g., match card with color="blue", type="Creature", legendary=True to templates matching patterns like "blue*creature*legend*.png" with tolerance for naming variations)

- **FR-009**: System MUST download custom card artwork from URLs specified in the spreadsheet's "pic" field when provided; if artwork URL is invalid/unreachable or returns non-image content, proxy generation MUST fail for that card with logged error (card name + URL) while continuing to process remaining cards

- **FR-010**: System MUST render mana symbols using standard MTG iconography (converting Bu→blue mana, Rd→red mana, Wt→white, Gn→green, Bk→black, Cl→colorless)

- **FR-011**: System MUST generate output images at print-ready resolution (300 DPI minimum, poker card size 2.5" x 3.5" = 750x1050 pixels)

- **FR-012**: System MUST organize generated proxies using dynamic folder grouping strategy determined by multi-strategy voting: generate candidate organization strategies (color/type, type/color, multicolor-separate, etc.), score each card's fit to each strategy, select the most-supported strategy as winner (e.g., if 80%+ creatures vote for color-first → use blue/creatures/, red/creatures/; if evenly distributed → use type/color). Optionally present top strategies to user for refinement

- **FR-013**: System MUST validate that each extracted card has required fields (name, type) and warn about missing data before proxy generation

### Non-Functional Requirements

- **NFR-001**: Spreadsheet parsing MUST complete within 30 seconds for files up to 500 cards

- **NFR-002**: Template downloads MUST support batch fetching of 10+ templates concurrently

- **NFR-003**: Proxy generation MUST support batch processing of 200+ cards with progress reporting (expected duration: 20-60 seconds per card with VLM-guided MCTS, leveraging Ollama local VLM for 0.2s evaluation time)

- **NFR-004**: Generated proxy images MUST be high-quality PNG files suitable for professional printing (lossless compression, 300 DPI)

- **NFR-005** (**DEVELOPMENT STRATEGY**): Implementation MUST use backwards-working methodology - start with end goal (generate single proxy card from single Hellcube row), then work backwards to identify required MCTS components. This enables parallel development: (Stream 1) End-to-end pipeline from Excel row to proxy image, (Stream 2) MCTS algorithm development, converging at MCTS integration point. First milestone: One complete proxy from one spreadsheet row without MCTS optimization, then add MCTS incrementally.

- **NFR-006** (**OBSERVABILITY**): System MUST log timestamped progress metrics to stdout (and optionally to file) for NFR validation: (1) Parsing phase duration (validates NFR-001 <30s target), (2) Per-card processing time (validates NFR-003 20-60s target), (3) Total batch duration, (4) MCTS convergence metrics per card (rollouts used, final quality score). Log format: `[YYYY-MM-DD HH:MM:SS] Card N/Total: <name> - <duration>s, quality=<score>, converged after <rollouts> rollouts`. Enables post-run performance analysis and bottleneck identification without separate monitoring infrastructure.

### Key Entities *(include if feature involves data)*

- **Card**: Represents a single MTG custom card with attributes including name, mana cost (parsed from name), inferred color (derived from mana symbols), primary card type (Creature/Planeswalker/Artifact/etc., extracted from Types field), legendary status (boolean, detected from "Legendary" keyword), subtypes (list extracted from Types field after dash), abilities (list of text entries), flavor text, power/toughness (for creatures), author, and optional artwork URL

- **Spreadsheet Cell Group**: Represents a collection of related spreadsheet cells that form a single card definition, identified by semantic field labels (name, Types, text, flavor, Stats, Author) and grouped by spatial proximity

- **Card Template**: Represents a visual frame/border for a card type and color combination, with text box boundaries detected dynamically via image analysis (rather than hardcoded coordinates), matched to cards using fuzzy filename pattern matching

- **Mana Cost**: Parsed representation of a card's casting cost, containing counts of each mana color (blue, black, green, red, white, colorless, generic) extracted from parenthetical notation

- **Template Source**: Online resource (URL) from which card templates can be downloaded, categorized by card type, color, and frame style

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully parses 95%+ of cards from the Hellcube AJ.xlsx file with all required fields (name, type) correctly extracted

- **SC-002**: Mana cost extraction correctly parses 100% of standard notation formats ((Bu), (Rd,Rd), (Wt)(2), etc.) into structured mana objects

- **SC-003**: Template research identifies and downloads templates for all 6 primary MTG colors, all 10 dual-color pairs, multicolor, and all standard card type variants (minimum 50+ distinct template types covering all color-type combinations)

- **SC-004**: Proxy generation produces print-ready images for all parsed cards with MCTS+VLM optimization (expected duration: 1-3 hours for 200+ card Hellcube at 20-60s per card, depending on card complexity and convergence behavior)

- **SC-005**: Generated proxies have all card elements properly positioned with readable text at print size (2.5" x 3.5" physical card dimensions)

- **SC-006**: System handles cards with missing optional fields (flavor text, author, custom artwork) by generating valid proxies with those fields blank

- **SC-007**: Batch processing organizes generated proxies using optimal folder structure determined by multi-strategy voting (grouping strategy adapts to card distribution - e.g., creature-heavy decks use color-first, balanced decks use type/color-first)

- **SC-008**: End-to-end workflow (spreadsheet parse → template download → proxy generation) completes without manual intervention for standard Hellcube format

## Assumptions

- The Hellcube spreadsheet follows the observed pattern: field labels in one cell/row, followed by field values, with cards separated by author rows (AJ, Joey, Chat GPT)

- Card names contain mana costs in parenthetical notation at the end (e.g., "Card Name (Rd,Rd)(1)")

- "Stats" field contains power/toughness information, potentially formatted as dates (e.g., "2025-02-04" meaning 2/4) or as text ratios

- MTG card templates are available from public sources (community resources, fan sites, or open design assets)

- Users want print-ready output suitable for home/professional printing on standard poker card stock

- The "pic" field in the spreadsheet contains either URLs to artwork or is blank (system doesn't need to generate original artwork)

- Standard MTG mana symbol fonts/icons are available or can be downloaded as part of template assets

## Dependencies

- **Excel file processing**: Python pandas library or similar for reading .xlsx files and extracting cell data

- **Image processing**: PIL/Pillow or similar for compositing card data onto templates, rendering text, and generating final images

- **Domain-Agnostic Skills**: Existing skills from .claude/skills/ directory for template research and download:
  - .claude/skills/http/download-file.md - HTTP file downloads
  - .claude/skills/http/fetch-json.md - JSON API requests
  - .claude/skills/html/ - HTML parsing for template source identification
  - .claude/skills/document/ - Document generation utilities

- **Semantic reasoning**: Pattern matching and heuristics for identifying field types from unstructured cell data (may use simple keyword matching or ML-based text classification)

- **Monorepo Git Submodule**: The monorepo repository added as git submodule at monorepo/ (relative path) to provide live access to shared utilities (instructor framework, BaseAlgorithm, PerceptInterface) without full code duplication. **Setup required in T0-T1**: `git submodule add <monorepo-url> monorepo && git submodule update --init --recursive`

- **MCTS Algorithm** (**REVISED AFTER AUDIT**): Monte Carlo Tree Search implementation developed **directly in Feature 012** (src/mcts/) without monorepo dependency. Imports BaseAlgorithm from monorepo/ (via git submodule). Follows Reflexion template pattern (BaseAlgorithm inheritance with execute(problem, on_trial=None, iteration_context=None, **kwargs) signature, instructor-based structured output, behave testing). MCTS extracts card_data and template_regions from kwargs, ignores on_trial and iteration_context (SUPPORTS_ITERATION=False). Algorithm follows academic standards from Browne et al. (2012) "A Survey of Monte Carlo Tree Search Methods" and Kocsis & Szepesvári (2006) UCB1 bandit formula with C=√2≈1.414 exploration constant. **Effort adjustment**: +5-8 hours added to Phase 2 tasks for MCTS implementation (not copied from monorepo).

- **VLM Backend**: Vision Language Model via Ollama for compute offloading (template image analysis, text box boundary detection, layout quality evaluation) - reduces cloud API costs by running locally. Uses monorepo/agentic/core/utils/instructor.py (via git submodule) for structured output generation.

- **Instructor Framework**: Existing monorepo/agentic/core/utils/instructor.py (accessed via git submodule) provides structured output generation, backend switching (claude_code/ollama/test), and BaseModel validation for MCTS and VLM integration

- **Validation Infrastructure** (**REVISED AFTER AUDIT - DE-COUPLED**): Pydantic models implemented natively in Feature 012 (.claude/skills/helpers/pydantic_models.py, .claude/skills/validation/). Defense-in-depth validation pattern (Layer 1: Python self-validation, Layer 2: bash wrapper re-validation) for MCTS data structures (LayoutState, MCTSNode, TemplateRegions, LayoutQuality). **Inspired by branch 013's design but independent implementation**. Optional: analyze branch 013 via git worktree for pattern inspiration. **Effort adjustment**: +2 hours added to Phase 2 for validation infrastructure development.

- **Skill Orchestration** (**REVISED AFTER AUDIT - SIMPLIFIED**): Lightweight bash orchestration scripts for coordinating domain-agnostic skills (template research, download, batch processing). Simple sequential execution with error handling and retry logic. Optional: analyze branch 013's orchestration via git worktree for advanced patterns, but implement independently. Defer complex orchestration framework until proven necessary.

## Out of Scope

- Generating original card artwork (system uses URLs provided in spreadsheet or leaves artwork blank)
- Automated card balance analysis or rules validation
- Integration with online printing services (output is local files; printing is manual)
- Support for non-English cards or alternative MTG languages
- Creating custom card frames or templates from scratch (uses existing template resources)
- Real-time collaboration or multi-user spreadsheet editing
- Automatic card legality checking for official MTG formats
