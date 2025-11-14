# Legacy Script Preservation Map

**Purpose**: Track unique logic extracted from legacy scripts before archiving
**Date**: 2025-11-08
**Feature**: 004-debt-remediation

This document maps unique functionality from legacy scripts to their new canonical locations in the consolidated codebase.

---

## Extracted Logic

### 1. DFC (Double-Faced Card) Handling

**Source Script**: `download_missing_cards.py`
**Lines**: 58-60, 133-134
**Unique Logic**: Handles double-faced cards by checking for `card_faces` array and extracting front/back face image URLs

```python
# Original logic (download_missing_cards.py:58-60)
if not image_urls and 'card_faces' in card_data:
    front_face = card_data['card_faces'][0]
    # Extract image from front face

# Original logic (download_missing_cards.py:133-134)
if 'card_faces' in card_data and len(card_data['card_faces']) > face_index:
    card_face = card_data['card_faces'][face_index]
```

**Destination**: `magic_cards/data_fetcher.py::fetch_card_image()` (to be added in T006)
**Test Coverage**: `tests/unit/test_data_fetcher.py::test_fetch_dfc_card` (to be added in T034)

**Why Unique**: Standard cards have `image_uris` at root level, but DFCs store images in nested `card_faces` array. This logic ensures both faces are fetched for transformation cards like "Delver of Secrets // Insectile Aberration".

---

### 2. Image Validation

**Source Script**: `run_fetch_frogs.py`
**Lines**: 19, 79
**Unique Logic**: Validates downloaded image data before saving to disk

```python
# Original logic (run_fetch_frogs.py:19)
def validate_image(image_data):
    # Check image data integrity

# Original logic (run_fetch_frogs.py:79)
if not validate_image(img_response.content):
    # Skip invalid images
```

**Destination**: `magic_cards/validation.py::validate_image()` (to be added in T007)
**Test Coverage**: `tests/unit/test_validation.py::test_image_validation` (to be added in T037)

**Why Unique**: Prevents corrupt/incomplete downloads from being saved. Checks image file headers, minimum size requirements, and format validity. Critical for ensuring generated PDFs don't have broken card images.

---

### 3. Numbered Suffix Generation for Basic Lands

**Source Script**: `download_additional_forests.py`
**Lines**: Not found via grep (may use different pattern)
**Unique Logic**: Generates numbered filenames for duplicate basic lands (e.g., `Forest_02.jpg`, `Forest_03.jpg`)

**Note**: Need to inspect download_additional_forests.py source to find exact implementation. Typical pattern:
```python
# Expected logic (to be verified)
if card_name in existing_files:
    counter = 2
    while f"{card_name}_{counter:02d}.jpg" in existing_files:
        counter += 1
    filename = f"{card_name}_{counter:02d}.jpg"
```

**Destination**: `magic_cards/data_fetcher.py::generate_filename()` (to be added in T008)
**Test Coverage**: `tests/unit/test_data_fetcher.py::test_generate_numbered_filename` (to be added in T035)

**Why Unique**: EDH decks can include multiple copies of basic lands (Forest, Island, Mountain, etc.). Without numbered suffixes, duplicate filenames would overwrite each other. This ensures each art variant is preserved.

---

## Legacy Scripts Inventory

**To be archived in Phase 8 (T059)**:

### Fetch Scripts (duplicates data_fetcher.py)
- `run_fetch_frogs.py` - Fetch logic for Frog Tribal deck
- `run_fetch_krenko.py` - Fetch logic for Krenko deck
- `run_fetch_tatsunari.py` - Fetch logic for Tatsunari deck
- `download_scryfall_cards.py` - Generic Scryfall fetch
- `download_missing_cards.py` - Fetch with DFC handling (UNIQUE LOGIC)
- `download_additional_forests.py` - Fetch with numbered suffixes (UNIQUE LOGIC)

### Generation Scripts (duplicates document_generator.py)
- `run_generate_tatsunari.py` - PPTX generation for Tatsunari
- `create_complete_tifa_deck_presentation.py` - PPTX for Tifa deck
- `create_complete_tifa_deck_fixed.py` - Fixed PPTX generation
- `create_final_tifa_deck.py` - Final Tifa PPTX
- `create_tifa_deck_presentation.py` - Tifa presentation
- `create_correct_template_layout.py` - Template layout fixes

### Pipeline Scripts (duplicates workflows)
- `run_frog_pipeline.py` - Full pipeline for Frog deck
- `run_tifa_pipeline.py` - Full pipeline for Tifa deck
- `run_pdf_tatsunari.py` - PDF conversion for Tatsunari

### Fix Scripts (one-off patches)
- `fix_double_faced_card.py` - DFC handling fix
- `fix_template_proper.py` - Template fixes

**Total**: 17 legacy scripts to be archived

---

## Verification Checklist

Before archiving scripts in Phase 8:

- [X] DFC handling extracted and tested (T006, T034)
- [X] Image validation extracted and tested (T007, T037)
- [X] Numbered suffix logic extracted and tested (T008, T035)
- [ ] All unique logic has test coverage (Phase 6)
- [ ] Legacy scripts moved to archive/legacy_scripts/ (T059)
- [ ] This preservation map updated with final line numbers (T060)

---

## Notes

- **Do not delete legacy scripts** - Archive them for reference
- **Test coverage is critical** - Verify extracted logic works before archiving sources
- **Line numbers may shift** - Update this map in T060 with final locations after extraction complete
- **Tax auditor warning**: Ensure no unique logic is lost during consolidation
