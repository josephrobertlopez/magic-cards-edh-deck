# Implementation Plan: Scryfall Card Fetcher and PDF Template Filler Skills

**Branch**: `001-scryfall-pdf-skills` | **Date**: 2025-11-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-scryfall-pdf-skills/spec.md`

## Summary

Create two Claude Code skills that wrap existing Python functionality for fetching Magic: The Gathering card images from Scryfall API and placing them into PowerPoint template presentations. Implementation follows a 3-phase hybrid approach: (1) Fast Value MVP creating working skills, (2) Consolidation reducing technical debt from 17+ scripts, (3) Spec Alignment adding quality requirements.

**Approach**: Protocol-First Consolidation (backwards-thinker + spec-driven hybrid)
**Timeline**: Phase 1 (hours) → Phase 2 (days) → Phase 3 (week)

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: python-pptx (PowerPoint manipulation), Pillow (image processing), requests (Scryfall API)
**Storage**: Local filesystem (images/ directory for downloaded cards)
**Testing**: pytest (unit), behave (BDD integration - Phase 3)
**Target Platform**: Claude Code skill execution environment
**Project Type**: Single project (CLI tools wrapped as skills)
**Performance Goals**:
- 100-card fetch in <30 seconds (SC-001)
- Template fill for 100 cards in <60 seconds (SC-003)
- 95% fuzzy match accuracy (SC-004)
**Constraints**:
- Scryfall API rate limit (100ms minimum between requests)
- Claude Code skill interface requirements (FR-010)
**Scale/Scope**: 100-card EDH decklists, 17 existing scripts to consolidate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ⚠️ No constitution file exists yet

Multi-agent debate (backwards-thinker, spec-driven-dev, inquisitor judge) established provisional principles:
- **Reuse over rewrite**: Leverage existing working code patterns
- **Skills first**: Claude Code skills are mandatory (FR-010, SC-006), not CLI wrappers
- **Fast fail virtuous**: Basic error handling in Phase 1, comprehensive in Phase 3
- **Protocol-first**: Template-as-contract architecture (slots define layout protocol)
- **Incremental value**: Working skills before perfect architecture

**Recommended**: Create minimal constitution after Phase 1 validation

## Project Structure

### Documentation (this feature)

```text
specs/001-scryfall-pdf-skills/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file - implementation strategy
├── checklists/
│   └── requirements.md  # Spec validation (passed)
└── tasks.md             # To be created by /speckit.tasks
```

### Source Code (repository root)

```text
.claude/
└── skills/               # [NEW - Phase 1]
    ├── fetch-cards.md    # Skill: Download cards from Scryfall
    └── fill-template.md  # Skill: Generate presentation from template

lib/                      # [NEW - Phase 2]
├── scryfall_utils.py     # Consolidated API/download logic
└── template_utils.py     # Consolidated presentation logic

images/                   # [EXISTING]
└── *.jpg                 # Downloaded card images (102 existing)

tests/                    # [NEW - Phase 2/3]
├── unit/
│   ├── test_scryfall_utils.py
│   └── test_template_utils.py
└── integration/
    └── features/         # [Phase 3]
        ├── fetch_cards.feature
        └── fill_template.feature

[TO DELETE IN PHASE 2]
├── download_scryfall_cards.py
├── use_template_for_all_cards.py
├── magic_cards_template_fixer.py
├── magic_cards_template_final_fix.py
├── magic_cards_template_orientation_fix.py
└── [12 other deprecated scripts]
```

**Structure Decision**: Single project structure. Existing codebase has 17+ standalone scripts scattered in root directory. Phase 2 consolidates into `lib/` modules with skills as thin wrappers. Tests follow standard pytest + behave structure.

## Phase Breakdown

### Phase 0: Debate & Planning ✅ COMPLETE

**Outcome**: Multi-agent debate resolved hybrid approach
- Backwards-thinker: Advocated minimal wrapping of existing code
- Spec-driven-dev: Advocated full spec requirements and testing
- Inquisitor judge: Ruled hybrid 3-phase approach balances both

**Key Decisions**:
1. Two skills architecture (fetch + fill) - not one combined
2. Error recovery: Continue with warnings (manifest of failures)
3. State management: JSON manifest file between skills
4. Double-faced cards: Both faces downloaded and placed in separate slots (user override 2025-11-06)
5. Refactoring: Minimal in Phase 1, moderate in Phase 2
6. Template source: decks.pptx (2 slides: blank outline + filled example)

### Phase 1: Fast Value (MVP) ✅ COMPLETE

**Goal**: Working Claude Code skills in hours

**Tasks**:
1. Create `.claude/skills/` directory
2. Extract `download_card_image()` from `download_scryfall_cards.py`
3. Extract `create_presentation_with_template_pattern()` from `use_template_for_all_cards.py`
4. Create `fetch-cards.md` skill:
   - Input: Decklist file path
   - Output: JSON manifest (card names, image paths, failures)
   - Error handling: Try/catch, file existence checks
   - **Manifest Schema**:
     ```json
     {
       "timestamp": "2025-11-06T10:30:00Z",
       "decklist_path": "tifa_deck.txt",
       "total_cards": 100,
       "successful": 98,
       "failed": 2,
       "cards": [
         {
           "name": "Tifa Lockhart",
           "path": "images/tifa_lockhart.jpg",
           "status": "success"
         },
         {
           "name": "Misspelled Card",
           "status": "failed",
           "reason": "Not found on Scryfall"
         }
       ]
     }
     ```
   - Manifest saved to: `.claude/state/fetch_manifest.json`
5. Create `fill-template.md` skill:
   - Input: Template file, images directory, output path
   - Output: Generated presentation file
   - Error handling: Template validation, slot extraction errors
6. Create validation script `tests/validate_phase1.py`:
   - Run both skills on 10-card sample decklist
   - Validate JSON manifest structure matches schema
   - Compare output presentation to expected template pattern
   - Output: PASS/FAIL + detailed errors
   - Sample decklist: Create `test_decks/phase1_sample.txt` with 10 known cards
7. Test both skills through Claude Code execution using validation script

**Deliverables**:
- Working `/fetch-cards` skill (satisfies P1 user story)
- Working `/fill-template` skill (satisfies P2 user story)
- Basic error messages for common failures
- JSON manifest for skill coordination
- Validation script (`tests/validate_phase1.py`)
- Sample test decklist (`test_decks/phase1_sample.txt`)

**Success Criteria**: SC-006 satisfied (skills execute through Claude Code)

**Phase 1 Exit Criteria** (must all pass before proceeding to Phase 2):
- ✅ Both skills execute via `/fetch-cards` and `/fill-template` without crashes
- ✅ At least 80% of test decklist cards successfully download from Scryfall
- ✅ Generated presentation visually matches template pattern (slots filled correctly)
- ✅ JSON manifest produced by `fetch-cards` is consumable by `fill-template`
- ✅ User validates output quality meets proxy printing needs
- ✅ Validation script (`tests/validate_phase1.py`) reports PASS

**Note**: Phase 1 is MVP only. Error handling is basic, fuzzy matching is missing, and no comprehensive tests exist. User must explicitly acknowledge this before considering Phase 1 "complete."

### Phase 2: Consolidation (Technical Debt Reduction)

**Goal**: Replace 17 scripts with tested library

**Tasks**:
1. Create `lib/scryfall_utils.py`:
   - `fetch_card_from_api(card_name, fuzzy=True)`
   - `batch_download_cards(decklist, output_dir)`
   - `sanitize_filename(card_name)`
   - Rate limiting logic
2. Create `lib/template_utils.py`:
   - `extract_template_slots(template_file)`
   - `resize_card_for_slot(image_path, slot_dimensions, orientation)`
   - `place_cards_in_template(cards, template, output)`
3. Refactor skills to import from `lib/`
4. Add unit tests:
   - `tests/unit/test_scryfall_utils.py` (API mocking, rate limits)
   - `tests/unit/test_template_utils.py` (slot extraction, aspect ratios)
5. Delete 17 deprecated scripts after validation
6. Run pytest suite to verify consolidation

**Deliverables**:
- `lib/` modules with tested, reusable code
- Pytest suite with >80% coverage
- Cleaned repository (17 scripts → 2 modules)
- Skills using shared library

**Success Criteria**: Technical debt reduced, no functionality lost

### Phase 3: Spec Alignment (Quality)

**Goal**: Satisfy all spec requirements

**Tasks**:
1. Implement FR-003: Fuzzy matching with error recovery
   - Multiple search attempts (fuzzy → exact → partial)
   - Clear messaging for unmatched cards
2. Implement FR-004: Rate limit handling
   - Exponential backoff on 429 errors
   - User feedback during waits
3. Implement FR-009: Enhanced error messages
   - Structured error reporting (which card, why failed, suggested fix)
4. Add integration tests (behave):
   - `tests/integration/features/fetch_cards.feature`
   - `tests/integration/features/fill_template.feature`
   - Given/When/Then scenarios from spec acceptance criteria
5. Validate against all Success Criteria:
   - SC-001: 100 cards in <30s (benchmark test)
   - SC-002: Image quality validation
   - SC-003: Template fill in <60s (benchmark test)
   - SC-004: 95% match rate (test with intentional typos)
   - SC-005: Compare output to example_output.pptx
   - SC-007: Error message quality review
6. Update spec Status: Complete

**Deliverables**:
- Full BDD test suite (behave)
- All FR-001 through FR-012 implemented
- All SC-001 through SC-007 validated
- Production-ready skills

**Success Criteria**: All spec requirements met, spec marked complete

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scryfall API changes break skills | High | Phase 3 adds error handling and fallbacks; tests validate expected behavior |
| 17 scripts have hidden dependencies | Medium | Phase 2 consolidation exposes coupling through tests; incremental refactoring |
| Phase 1 "working" doesn't mean "complete" | Medium | Judge's ruling explicitly forbids stopping at Phase 1; spec defines complete |
| Skills interface unclear | Low | Phase 1 creates concrete example; adjust in Phase 2 based on usage |
| Template format variations break slot extraction | Medium | Phase 3 adds template validation; error messages guide user to fix template |

## Complexity Tracking

**No constitution violations**: Multi-agent debate established provisional principles sufficient for this feature. Complexity is managed through phased approach rather than upfront architecture.

**Note**: If 3D/4D methodology from CLAUDE.md is required, user should run `/speckit.constitution` before Phase 2.

## Forbidden Actions (Judge's Ruling)

❌ Wrapping scripts without creating `.claude/skills/` structure
❌ Writing 40 tests before skills execute once (analysis paralysis)
❌ Creating script #18 without deleting deprecated scripts #1-17
❌ Ignoring FR-010/SC-006 Claude Code skills requirement
❌ Spec-driven rewrite that discards working patterns
❌ Stopping after Phase 1 without user validation

## Next Steps

1. **User Decision**: Approve Phase 1 start (y/n)
2. **Execute Phase 1**: Create skills structure and extract functions
3. **User Validation**: Test skills and confirm value before Phase 2
4. **Iterate**: Phases 2-3 based on user feedback

**Estimated Timeline**:
- Phase 1: 2-4 hours
- Phase 2: 1-2 days
- Phase 3: 3-5 days

**Total**: ~1 week to production-ready skills
