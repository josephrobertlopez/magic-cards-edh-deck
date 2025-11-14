# Feature Specification: Scryfall Card Fetcher and PDF Template Filler Skills

**Feature Branch**: `001-scryfall-pdf-skills`
**Created**: 2025-11-06
**Status**: Planning - Hybrid Approach Approved
**Input**: User description: "skill to also get card images via scryfall for single and double sided cards then another skill to read and or place images onto templated format for 6 per page"

## Clarifications

### Session 2025-11-06

- Q: How should double-sided cards be handled in the presentation? → A: Double-sided cards should be 2 separate images placed in 2 separate template slots (both front and back faces displayed)
- Q: Which template file should be used as the canonical reference? → A: decks.pptx (contains 2 slides: blank template with black outlines + filled example)
- Q: What image sources should be used? → A: Use whatever images are available from downloads
- Q: What should happen when Scryfall API is unavailable or returns rate-limit errors? → A: Retry failed requests up to 3 times with exponential backoff (100ms, 200ms, 400ms), then continue with failures logged
- Q: How should the system handle card names that don't exist or can't be matched even with fuzzy search? → A: Fail entire workflow and require user to fix decklist before continuing
- Q: What should happen when the template has more/fewer slots than available cards? → A: Fill available slots on current slide, create additional slides as needed from template pattern, leave empty slots blank if cards run out
- Q: What should happen when image files are corrupted or incomplete downloads occur? → A: Validate image files after download (check header/size), retry corrupted downloads up to 3 times, skip and log if still corrupted

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fetch Card Images from Decklist (Priority: P1)

A user provides a list of Magic: The Gathering card names and wants to retrieve high-quality card images for all cards, including double-faced cards.

**Why this priority**: This is the foundation - without card images, no presentation can be created. This delivers immediate value by automating the tedious manual download process.

**Independent Test**: Can be fully tested by providing a decklist text file and verifying that all card images are downloaded to the correct location with proper naming and quality.

**Acceptance Scenarios**:

1. **Given** a text file containing card names (one per line), **When** the user invokes the card fetcher skill, **Then** all card images are downloaded to the images directory
2. **Given** a decklist containing double-faced cards (e.g., "Walk-In Closet // Forgotten Cellar"), **When** the fetcher runs, **Then** both faces of the card are retrieved correctly
3. **Given** a card name with special characters or variations, **When** fuzzy search is used, **Then** the correct card is identified and downloaded
4. **Given** 100 cards in a decklist, **When** the fetcher runs, **Then** all downloads complete within 30 seconds with appropriate rate limiting

---

### User Story 2 - Generate Presentation from Template (Priority: P2)

A user has downloaded card images and wants to automatically generate a professionally formatted presentation using a predefined template layout.

**Why this priority**: This completes the end-to-end workflow, turning raw images into a usable presentation format. Depends on P1 but delivers the final user-facing value.

**Independent Test**: Can be tested by providing a folder of card images and a template file, then verifying the output presentation matches the expected layout with cards correctly positioned.

**Acceptance Scenarios**:

1. **Given** a directory of card images and a template file (decks.pptx), **When** the template filler skill runs, **Then** a new presentation is created with cards placed in template positions
2. **Given** a template with specific card slot dimensions, **When** cards are inserted, **Then** aspect ratios are preserved and cards fit within designated areas
3. **Given** 100 cards to place, **When** the skill runs, **Then** cards are distributed across multiple slides following the template pattern
4. **Given** both vertical and horizontal card orientations in the template, **When** cards are placed, **Then** orientation is handled correctly for each slot

---

### User Story 3 - End-to-End Deck Presentation Creation (Priority: P3)

A user wants to go from a simple decklist text file to a finished presentation in one step, without manual intervention.

**Why this priority**: This provides maximum convenience by chaining P1 and P2 together, but each individual skill still works independently.

**Independent Test**: Can be tested by providing only a decklist file and template, then verifying the complete presentation is generated without errors.

**Acceptance Scenarios**:

1. **Given** a decklist file and template file, **When** the user invokes the combined workflow, **Then** a complete presentation is generated with all cards fetched and placed
2. **Given** an incomplete download (some cards fail), **When** the workflow continues, **Then** the user is notified of missing cards and the presentation uses available images
3. **Given** a decklist with duplicate card entries, **When** the workflow runs, **Then** duplicates are handled appropriately (downloaded once, placed multiple times)

---

### Edge Cases

- How does the system handle different card image qualities (normal, large, small)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch card images from Scryfall using card names as input
- **FR-002**: System MUST support both single-faced and double-faced Magic cards, downloading both front and back face images for double-faced cards and placing them in separate template slots
- **FR-003**: System MUST handle fuzzy name matching to accommodate minor spelling variations
- **FR-004**: System MUST respect Scryfall API rate limits (minimum 100ms delay between requests)
- **FR-005**: System MUST preserve card aspect ratios when resizing for template slots
- **FR-006**: System MUST support template-based card positioning using a provided template file
- **FR-007**: System MUST handle both vertical and horizontal card orientations based on template slots
- **FR-008**: System MUST distribute cards across multiple slides when card count exceeds template capacity per slide
- **FR-009**: System MUST provide clear error messages when cards cannot be found or downloaded
- **FR-010**: Skills MUST be invokable through Claude Code's skill system
- **FR-011**: System MUST sanitize filenames to remove special characters that cause file system errors
- **FR-012**: System MUST support batch processing of entire decklists (up to 100+ cards)
- **FR-013**: System MUST retry failed Scryfall API requests up to 3 times with exponential backoff (100ms, 200ms, 400ms), then log failures and continue processing remaining cards
- **FR-014**: System MUST fail the entire fetch workflow when a card name cannot be found via fuzzy or exact search, displaying the problematic card name and requiring user to fix the decklist
- **FR-015**: System MUST fill available template slots sequentially, create additional slides from template pattern when card count exceeds slots per slide, and leave empty slots blank when cards are exhausted
- **FR-016**: System MUST validate downloaded image files for integrity (checking file header and size), retry corrupted downloads up to 3 times, and skip with logged warning if validation still fails

### Key Entities

- **Card**: Represents a Magic: The Gathering card with name, image URL, face count (single/double), and local file path
- **Decklist**: Collection of card names representing a complete deck (typically 100 cards for EDH format)
- **Template**: PowerPoint presentation file defining card slot positions, sizes, and orientations
- **Card Slot**: Specific position within a template slide with defined dimensions and orientation
- **Skill**: Executable command within Claude Code that performs a specific task (fetch or fill)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can fetch all cards from a 100-card decklist in under 30 seconds
- **SC-002**: Card image quality is sufficient for printing (minimum 300 DPI equivalent at card dimensions)
- **SC-003**: Template filling completes for 100 cards in under 60 seconds
- **SC-004**: 95% of card name queries successfully match the intended card using fuzzy search
- **SC-005**: Generated presentations match the reference example (example_output.pptx) in layout and quality
- **SC-006**: Skills execute successfully through Claude Code without requiring manual Python script execution
- **SC-007**: Error messages clearly identify which cards failed and why, allowing users to correct issues

## Assumptions

- Scryfall API remains accessible and maintains current endpoint structure
- Template files follow PowerPoint (.pptx) format standards
- Users have internet connectivity for API requests
- Card images are publicly available through Scryfall's image CDN
- Target output format is PowerPoint presentations, not PDF (despite "PDF" in feature name)
- The "6 per page" mentioned refers to the template pattern, which may actually vary (exploration found 8-card patterns)
- Users will provide decklists as plain text files with one card name per line
- Skills will leverage existing Python codebase rather than reimplementing from scratch

## Dependencies

- Access to Scryfall API (https://api.scryfall.com)
- Existing Python scripts in the repository (download_scryfall_cards.py, create_correct_template_layout.py, etc.)
- Template file (decks.pptx) as reference for slot positions
- Claude Code skill execution environment with Python support

## Out of Scope

- Creating new template layouts from scratch
- Supporting card games other than Magic: The Gathering
- Real-time API without rate limiting
- Editing or modifying card images (filters, effects, cropping)
- Managing multiple deck versions or deck history
- Integration with deck-building websites beyond Scryfall
- Exporting to formats other than PowerPoint (PDF export is a separate concern)
- Automatic card legality validation or deck optimization

## Implementation Strategy

**Approach**: 3-Phase Protocol-First Consolidation (Hybrid)

After multi-agent debate (backwards-thinker, spec-driven-dev, inquisitor judge), a hybrid approach was determined to balance fast value delivery with quality requirements.

### Phase 1: Fast Value (Hours - MVP)
**Goal**: Get Claude Code skills working with minimal changes

- Create `.claude/skills/` directory structure
- Extract working functions from existing scripts (use_template_for_all_cards.py, download_scryfall_cards.py)
- Create two skills:
  - `fetch-cards`: Wraps Scryfall download logic with batch processing
  - `fill-template`: Wraps presentation generation with template pattern
- Add basic error handling (file existence checks, try/catch)
- Validate skills execute through Claude Code
- **Deliverable**: Working skills satisfying FR-010 and SC-006

### Phase 2: Consolidation (Days - Technical Debt Reduction)
**Goal**: Turn 17 scripts into tested library

- Create shared modules:
  - `scryfall_utils.py`: Consolidated download logic
  - `template_utils.py`: Consolidated presentation logic
- Update skills to import from shared modules
- Add unit tests (pytest) for shared modules
- Delete deprecated scripts (magic_cards_template_fixer.py, *_final_fix.py, etc.)
- **Deliverable**: Maintainable codebase with test coverage

### Phase 3: Spec Alignment (Week - Quality)
**Goal**: Satisfy all spec requirements

- Implement fuzzy matching error recovery (FR-003, FR-009)
- Add rate limit handling (FR-004)
- Add integration tests (behave .feature files)
- Validate against all Success Criteria (SC-001 through SC-007)
- Mark spec Status: Complete
- **Deliverable**: Production-ready skills meeting all requirements

### Rationale

This approach:
- Leverages existing working code patterns (backwards-thinker insight)
- Satisfies Claude Code skills requirement (spec-driven insight)
- Delivers value incrementally without analysis paralysis
- Prevents creating "script #18" without consolidation
- Adds quality gates after MVP validation

**Forbidden Actions**:
- Wrapping scripts without creating `.claude/skills/`
- Writing 40 tests before skills execute once
- Creating new scripts without deleting deprecated ones
- Ignoring FR-010/SC-006 Claude Code requirement
- Spec-driven rewrite that discards working patterns
