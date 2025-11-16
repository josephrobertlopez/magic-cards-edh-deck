# Implementation Plan: Hellcube Proxy Generator

**Branch**: `012-hellcube-proxy-generator` | **Date**: 2025-11-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-hellcube-proxy-generator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Parse unstructured Hellcube spreadsheet using semantic pattern recognition, research and download MTG card templates, and generate print-ready proxy cards at 300 DPI. Uses existing domain-agnostic skills (html/extract-css, http/fetch-json, http/download-file, document/grid-layout) plus new spreadsheet parsing skill and MCTS algorithm (imported from ../monorepo/agentic/algorithms/) for optimal text layout positioning.

## Technical Context

**Language/Version**: Python 3.9+ (existing codebase standard)
**Primary Dependencies**: pandas (Excel parsing), openpyxl (xlsx backend), Pillow (image composition), requests (HTTP), beautifulsoup4 (template research), python-pptx (grid layout), MCTS algorithm (import from ../monorepo/agentic/algorithms/mcts/), instructor (LLM structured output for behave tests), Ollama (VLM backend for image analysis compute offloading), existing domain-agnostic skills (http/, html/, document/)
**Storage**: File-based (Hellcube AJ.xlsx input, JSON card data cache, downloaded templates, generated proxy PNGs)
**Testing**: pytest (unit), behave (BDD integration with instructor patterns from monorepo), existing skill test infrastructure
**Target Platform**: Linux/macOS (LibreOffice dependency for PPTX→PDF conversion)
**Project Type**: Single project (CLI workflow using A2A orchestrator)
**Performance Goals**: Parse 200+ cards in <30s, download 15+ templates concurrently, generate 200+ proxies in <5min, MCTS layout optimization <2s per card
**Constraints**: Print-ready quality (300 DPI, 750x1050px), semantic parsing accuracy (95%+ success rate), batch processing support, MCTS must converge to optimal layout within 100 rollouts
**Scale/Scope**: 200+ cards in Hellcube, 6 MTG colors + multicolor/artifact/land variants, extensible to other cube formats, variable card elements (1-3 text boxes, optional P/T, flavor text)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
