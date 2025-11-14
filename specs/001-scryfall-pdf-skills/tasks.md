# Tasks: Scryfall Card Fetcher and PDF Template Filler Skills

**Input**: Design documents from `/specs/001-scryfall-pdf-skills/`
**Prerequisites**: plan.md ✅, spec.md ✅, clarifications complete ✅

**Tests**: Tests are NOT included in Phase 1 (MVP). Phase 2 adds unit tests, Phase 3 adds BDD integration tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize Claude Code skills structure and validation framework

- [ ] T001 Create `.claude/skills/` directory structure
- [ ] T002 Create `.claude/state/` directory for manifest storage
- [ ] T003 [P] Create `tests/` directory for validation script
- [ ] T004 [P] Create `test_decks/` directory for sample decklists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract working functions from existing scripts - MUST complete before user story implementation

**⚠️ CRITICAL**: Phase 1 skills depend on these extracted functions

- [ ] T005 Read and analyze `download_scryfall_cards.py` to identify `download_card_image()` function boundaries (lines 26-103)
- [ ] T006 Read and analyze `use_template_for_all_cards.py` to identify `create_presentation_with_template_pattern()` and `get_template_slot_positions()` functions
- [ ] T007 [P] Create sample decklist `test_decks/phase1_sample.txt` with 10 known Magic cards (e.g., Lightning Bolt, Sol Ring, Command Tower)

**Checkpoint**: Functions identified, ready for skill wrapper creation

---

## Phase 3: User Story 1 - Fetch Card Images from Decklist (Priority: P1) 🎯 MVP

**Goal**: Create Claude Code skill that downloads card images from Scryfall API with retry logic and manifest generation

**Independent Test**: Provide a decklist text file and verify all card images download to images/ with JSON manifest created

### Implementation for User Story 1

- [ ] T008 [US1] Create fetch-cards skill manifest at `.claude/skills/fetch-cards.md` with skill metadata (name, description, usage)
- [ ] T009 [US1] Write fetch-cards skill implementation that:
  - Accepts decklist file path as parameter
  - Reads card names from file (one per line)
  - Calls extracted download_card_image() for each card
  - Implements retry logic: 3 attempts with exponential backoff (100ms, 200ms, 400ms) per FR-013
  - Handles double-faced cards: downloads both front and back faces to separate files per FR-002
  - Fails workflow on unfound cards with clear error message per FR-014
  - Validates downloaded images (check file header/size) per FR-016
  - Sanitizes filenames per FR-011
  - Implements rate limiting (100ms between requests) per FR-004
- [ ] T010 [US1] Generate JSON manifest at `.claude/state/fetch_manifest.json` with schema:
  - timestamp, decklist_path, total_cards, successful, failed counts
  - cards array with name, path, status, reason fields
- [ ] T011 [US1] Add error handling for common failure scenarios:
  - Decklist file not found
  - Network failures (with retry)
  - API rate limit exceeded
  - Invalid card names
  - Corrupted image downloads
- [ ] T012 [US1] Test fetch-cards skill execution through Claude Code with phase1_sample.txt

**Checkpoint**: fetch-cards skill functional, downloads cards, generates valid manifest

---

## Phase 4: User Story 2 - Generate Presentation from Template (Priority: P2)

**Goal**: Create Claude Code skill that fills PowerPoint template with card images using slot-based layout

**Independent Test**: Provide images directory and template file, verify output presentation has cards correctly positioned in slots

### Implementation for User Story 2

- [ ] T013 [US2] Create fill-template skill manifest at `.claude/skills/fill-template.md` with skill metadata
- [ ] T014 [US2] Write fill-template skill implementation that:
  - Accepts template file path (decks.pptx), images directory, output path
  - Calls extracted get_template_slot_positions() to analyze template slots
  - Reads JSON manifest from `.claude/state/fetch_manifest.json`
  - Iterates through successfully downloaded cards from manifest
  - Calls extracted create_presentation_with_template_pattern() to place cards
  - Handles slot/card count mismatch per FR-015: fill sequentially, create slides as needed, leave empties blank
  - Preserves card aspect ratios per FR-005
  - Handles vertical/horizontal orientations per FR-007
  - Rotates cards 90° for horizontal slots based on slot dimensions
- [ ] T015 [US2] Add template validation:
  - Verify decks.pptx exists and is readable
  - Extract slot positions successfully
  - Handle malformed templates with clear error
- [ ] T016 [US2] Add error handling for:
  - Missing images directory
  - Images not matching manifest
  - PowerPoint write failures
  - Invalid template structure
- [ ] T017 [US2] Test fill-template skill execution through Claude Code with output from T012

**Checkpoint**: fill-template skill functional, generates presentations with correct card placement

---

## Phase 5: User Story 3 - End-to-End Workflow Validation (Priority: P3)

**Goal**: Create validation script that tests both skills together and verifies Phase 1 exit criteria

**Independent Test**: Run validation script and confirm all 6 exit criteria pass

### Implementation for User Story 3

- [ ] T018 [US3] Create validation script at `tests/validate_phase1.py` that:
  - Invokes fetch-cards skill with test_decks/phase1_sample.txt
  - Validates JSON manifest structure matches schema
  - Checks at least 80% cards downloaded successfully
  - Invokes fill-template skill with template decks.pptx
  - Verifies output presentation file created
  - Reports PASS/FAIL with detailed error messages
- [ ] T019 [US3] Add validation checks for:
  - Both skills execute without crashes
  - Manifest has correct schema (timestamp, counts, cards array)
  - Card status values are 'success' or 'failed'
  - Output .pptx file size > 0 and readable by python-pptx
  - Number of slides matches expected (cards / slots_per_slide)
- [ ] T020 [US3] Run validation script and verify Phase 1 exit criteria:
  - Exit criterion 1: Both skills execute without crashes
  - Exit criterion 2: 80%+ cards download successfully
  - Exit criterion 3: Presentation matches template pattern
  - Exit criterion 4: Manifest consumable by fill-template
  - Exit criterion 5: Manual user validation (requires user)
  - Exit criterion 6: Validation script reports PASS

**Checkpoint**: All Phase 1 deliverables complete, exit criteria satisfied (except manual user validation)

---

## Phase 6: Polish & Documentation

**Purpose**: Document skills and prepare for Phase 2

- [ ] T021 [P] Document fetch-cards skill usage in skill manifest .claude/skills/fetch-cards.md (parameters, examples, error codes)
- [ ] T022 [P] Document fill-template skill usage in skill manifest .claude/skills/fill-template.md (parameters, examples, template requirements)
- [ ] T023 Update plan.md status from "Phase 1: Fast Value ⏳ CURRENT" to "Phase 1: COMPLETE ✅"
- [ ] T024 Request user validation of output quality for proxy printing (Exit criterion 5)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - Can start after T007 complete
- **User Story 2 (Phase 4)**: Depends on Foundational - Can start after T007 complete (parallel with US1)
- **User Story 3 (Phase 5)**: Depends on US1 AND US2 complete - Validation requires both skills
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Foundational complete
- **User Story 2 (P2)**: Independent after Foundational complete (can run parallel with US1)
- **User Story 3 (P3)**: Depends on US1 + US2 (validates integration)

### Within Each User Story

**US1 (fetch-cards)**:
- T008 (manifest) → T009 (implementation) → T010 (JSON) → T011 (errors) → T012 (test)

**US2 (fill-template)**:
- T013 (manifest) → T014 (implementation) → T015 (validation) → T016 (errors) → T017 (test)

**US3 (validation)**:
- T018 (script) → T019 (checks) → T020 (criteria)

### Parallel Opportunities

**Setup Phase**: T003 and T004 can run in parallel (different directories)

**Foundational Phase**: T007 can run in parallel with T005-T006 (sample decklist independent of code analysis)

**User Stories**: US1 (Phase 3) and US2 (Phase 4) can be implemented in parallel after Foundational complete (different skills, different files)

**Polish Phase**: T021 and T022 can run in parallel (different skill documentation files)

---

## Parallel Example: After Foundational Phase

```bash
# Two developers can work simultaneously:

Developer A:
- Task T008: Create fetch-cards skill manifest
- Task T009: Implement fetch-cards logic
- Task T010: Add JSON manifest generation
- Task T011: Add error handling
- Task T012: Test fetch-cards skill

Developer B (parallel):
- Task T013: Create fill-template skill manifest
- Task T014: Implement fill-template logic
- Task T015: Add template validation
- Task T016: Add error handling
- Task T017: Test fill-template skill

# Once both complete:
- Task T018-T020: Validation (requires both skills)
```

---

## Implementation Strategy

### MVP First (Phase 1 Only - This Task List)

1. Complete Phase 1: Setup (T001-T004) - ~5 minutes
2. Complete Phase 2: Foundational (T005-T007) - ~15 minutes
3. Complete Phase 3: User Story 1 (T008-T012) - ~45 minutes
4. Complete Phase 4: User Story 2 (T013-T017) - ~45 minutes
5. Complete Phase 5: User Story 3 (T018-T020) - ~30 minutes
6. Complete Phase 6: Polish (T021-T024) - ~15 minutes
7. **Total Phase 1 Time: ~2.5 hours**

### Phase 1 Exit Criteria Validation

After T020 completes:
- ✅ T012 confirms fetch-cards executes without crashes
- ✅ T017 confirms fill-template executes without crashes
- ✅ T019 validates 80%+ download success rate
- ✅ T019 validates presentation structure matches template
- ✅ T019 validates manifest is valid JSON with correct schema
- ⏳ T024 awaits manual user validation of output quality

**STOP at T024**: Get user approval before proceeding to Phase 2 (Consolidation)

### Incremental Delivery

1. Phase 1 (Setup + Foundational) → Infrastructure ready
2. Phase 3 (User Story 1) → fetch-cards skill working independently
3. Phase 4 (User Story 2) → fill-template skill working independently
4. Phase 5 (User Story 3) → Both skills working together (MVP complete!)
5. Phase 6 (Polish) → Documented and ready for user validation

### Next Phases (Not in This Task List)

**Phase 2 (Consolidation)** - Separate task list, ~1-2 days:
- Extract functions to lib/scryfall_utils.py and lib/template_utils.py
- Add pytest unit tests
- Delete 17 deprecated scripts
- Refactor skills to use shared libraries

**Phase 3 (Spec Alignment)** - Separate task list, ~3-5 days:
- Implement fuzzy matching with retry (FR-003, FR-009)
- Add comprehensive error recovery
- Create behave BDD tests
- Validate all Success Criteria (SC-001 through SC-007)

---

## Notes

- [P] = tasks can run in parallel (different files/directories)
- [US1]/[US2]/[US3] = user story mapping for traceability
- Each phase has a checkpoint to validate independent functionality
- Phase 1 delivers working MVP in ~2.5 hours
- Extract functions by WRAPPING existing code, not rewriting
- Manifest schema is protocol contract between skills
- Validation script (T018-T020) is critical gate for Phase 1 → Phase 2
- User must explicitly approve Phase 1 output before Phase 2 consolidation begins
- All file paths are relative to repository root: `/home/joey/Documents/GitHub/magic-cards-edh-deck/`

---

## Task Summary

**Total Tasks**: 24
- **Setup**: 4 tasks (T001-T004)
- **Foundational**: 3 tasks (T005-T007)
- **User Story 1**: 5 tasks (T008-T012)
- **User Story 2**: 5 tasks (T013-T017)
- **User Story 3**: 3 tasks (T018-T020)
- **Polish**: 4 tasks (T021-T024)

**Parallel Opportunities**: 6 tasks can run in parallel (marked with [P])
- T003, T004 (Setup)
- T007 (Foundational)
- T021, T022 (Polish)
- US1 and US2 entire phases (10 tasks total if 2 developers)

**Critical Path**: T001 → T002 → T005 → T006 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T024

**Estimated Time**: 2.5 hours for single developer, ~1.5 hours with 2 developers working in parallel

**MVP Scope**: Tasks T001-T024 deliver Phase 1 complete with both working skills and validation
