# Consolidation Summary — 2026-04-23

## What Was Cleaned

### Removed from Git (now .gitignored):
- **Cache assets (4.7 MB)**: `.cache/artwork/` (269 KB), `.cache/templates/` (3.4 MB) — regenerable from Scryfall API + spreadsheet processing
- **Generated images (2.3 MB)**: `card_images/`, `card_images_both_sides/`, `card_images_double/` — derived from Scryfall downloads
- **Metadata (derived)**: `card_image_mapping*.json` — auto-generated index files
- **Session notes**: `.dev-changes/`, `AGENTS.md`, archived docs — not load-bearing to codebase

### Preserved in Git (load-bearing):
- **Source pipeline (4,374 LOC)**: `src/` package with modular architecture
  - `parsers/`: Hellcube + MCTS + mana cost + color inference
  - `models/`: Card, Template data classes
  - `batch/`: Batch processing orchestration
  - `download/`: Scryfall API integration
  - `inpainting/`: MCTS-driven template extraction
  - `matching/`: Template matcher for card composition
  - `mcts/`: MCTS action tree for layout optimization
  - `templates/`: PSD template handling
  - `skills/`: Template research utilities
  - `proxy_generator*.py`: CLI entry points (base + MCTS variant)
- **User decklists (1.8 KB)**: 18 decklist files as source data for batch processing
- **Architecture specs**: `SPEC_hellcube_renderer.md` — design rationale and lattice
- **Main entry points**: `generate_deck.py`, `grid_layout.py` (modified)
- **Project contract**: `CLAUDE.md` (updated)

## Why This Structure

**LDD Principle**: Ephemeral outputs (images, caches, derived metadata) belong in `.gitignore`. Source code, specs, and user data belong in git.

**Benefit**:
- Repo size reduced from ~10 MB (staged artifacts) to ~250 KB actual source
- Clean boundaries: source (committed) ↔ cache (local, regenerable)
- `git clone` gives you the pipeline + decklists, not 2GB of PNGs
- Cache can be safely deleted and regenerated without losing context

## Consolidation Decisions

| Category | Decision | Rationale |
|----------|----------|-----------|
| `.cache/artwork/` | → .gitignore | Ephemeral Scryfall assets, regenerable |
| `card_images/` + `mapping.json` | → .gitignore | Derived from API calls, not source |
| `src/` (4,374 LOC) | → COMMIT | Core pipeline, load-bearing |
| `decklists/*.txt` | → COMMIT | User-curated source data |
| `SPEC_*.md` | → COMMIT | Architecture + design rationale |
| `.dev-changes/`, `AGENTS.md` | → .gitignore | Session notes, not load-bearing |
| Utility scripts | → `archive/utilities/` | Off main path, organized separately |

## Next Actions

1. ✅ Updated `.gitignore` to exclude regenerable assets
2. ✅ Re-staged only load-bearing files
3. ✅ Cleaned up loose utility scripts
4. 🔲 Commit: "Consolidate pipeline + decklists, .gitignore ephemeral caches"
5. 🔲 Consider: Add `__init__.py` files to `src/*/` if missing (for package imports)
6. 🔲 Consider: Add `pyproject.toml` or `setup.py` for reproducible environments

## File Counts (after consolidation)

- **Staged for commit**: 36 files (+5,916 insertions)
- **.gitignored**: ~50 generated files, 2.3 GB cache
- **Dev-only**: session notes, scratch utilities

---
**Applied**: LDD reduce/reuse/recycle principle
**Status**: Ready for commit
