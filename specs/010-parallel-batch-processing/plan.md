# Implementation Plan: Parallel Batch Processing for A2A Orchestrator

**Branch**: `010-parallel-batch-processing` | **Date**: 2025-11-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-parallel-batch-processing/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add parallel batch processing capabilities to the A2A orchestrator to achieve 10x speedup (2 minutes vs 15+ minutes) for Commander deck proxy generation workflows. Implement configurable batch execution (batch_size + max_concurrent parameters), exponential backoff retry logic for API rate limits, and refactor commander_to_proxies workflow into reusable atomic skills (fetch-card-data, fetch-card-image, generate-slide) following single-responsibility principle. Support graceful partial failure handling and skill contract validation at workflow load time.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.9+ (existing codebase standard)
**Primary Dependencies**: asyncio (stdlib), aiohttp (async HTTP client for parallel requests), existing a2a_orchestrator modules (workflow_skill, message_cache, exceptions)
**Storage**: File-based (JSON manifests for execution logs, YAML workflows, skill markdown files in .claude/skills/)
**Testing**: pytest (existing), pytest-asyncio (async test support), unittest.mock for API simulation
**Target Platform**: Linux/macOS/Windows (cross-platform Python CLI)
**Project Type**: Single project (command-line orchestrator)
**Performance Goals**: ≤2 minutes for 100-card proxy generation (10x speedup from 15+ minute baseline), ≥95% batch success rate, preserve 25x message caching performance (±5%)
**Constraints**: Preserve backward compatibility with existing 17 workflows, respect Scryfall API fair use (exponential backoff for rate limits), zero cache invalidation side effects
**Scale/Scope**: 100+ card batch processing, 3-10 concurrent batches, 26+ skills, 17+ workflows, atomic skill decomposition (3-5 new skills from refactored commander_to_proxies)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS (No project-specific constitution defined - template only exists)

**Analysis**: No project-specific principles are defined in `.specify/memory/constitution.md` (file contains template placeholders). This feature follows existing codebase patterns:
- Extends existing a2a_orchestrator library (established pattern)
- Maintains backward compatibility (17 existing workflows must continue working)
- Uses pytest for testing (existing pattern)
- File-based storage (existing pattern: JSON manifests, YAML workflows)

**Recommendation**: Consider defining constitution post-feature to codify principles like:
- Backward compatibility requirement (100% existing workflows must work)
- Performance preservation (message caching 25x speedup non-negotiable)
- Graceful degradation (partial success preferred over all-or-nothing failure)

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

```text
a2a_orchestrator/              # Core orchestration engine
├── orchestrator.py            # MODIFIED: Add batch processing + contract validation
├── batch_processor.py         # NEW: Batch execution with concurrency control
├── retry_policy.py            # NEW: Exponential backoff retry logic
├── skill_contract.py          # NEW: Skill input/output contract validation
├── execution_manifest.py      # NEW: Structured logging for batch execution
├── exceptions.py              # MODIFIED: Add BatchProcessingError, ContractValidationError
├── workflow_skill.py          # MODIFIED: Support batch config in YAML
├── message_cache.py           # EXISTING: Preserve 25x performance (no changes)
├── cli/
│   └── __init__.py
└── skills/                    # Existing skill implementations
    └── __init__.py

.claude/skills/                # Skill definitions
├── fetch-card-data/           # NEW: Atomic skill (Scryfall metadata fetch)
│   └── SKILL.md               # Contract: input {card_name: str}, output {card_json: dict}
├── fetch-card-image/          # NEW: Atomic skill (image download)
│   ├── SKILL.md               # Contract: input {image_url: str, card_name: str}, output {image_path: str}
│   └── scripts/
│       └── fetch_image.py     # Python executor for image download
├── generate-slide/            # NEW: Atomic skill (PPTX slide creation)
│   ├── SKILL.md
│   └── scripts/
│       └── generate_slide.py
└── [26 existing skills...]

workflows/                     # YAML workflow definitions
├── commander_to_proxies.yaml  # MODIFIED: Refactored to use atomic skills + batch config
└── [17 existing workflows...]

tests/
├── unit/
│   ├── test_batch_processor.py      # NEW: Batch execution logic tests
│   ├── test_retry_policy.py         # NEW: Exponential backoff tests
│   ├── test_skill_contract.py       # NEW: Contract validation tests
│   └── test_execution_manifest.py   # NEW: Manifest logging tests
├── integration/
│   ├── test_parallel_workflows.py   # NEW: End-to-end batch workflow tests
│   └── test_atomic_skills.py        # NEW: Skill composition tests
└── fixtures/
    ├── mock_scryfall_responses.json # NEW: API response fixtures
    └── test_workflows/               # NEW: Test workflow YAML files
        └── test_batch_processing.yaml
```

**Structure Decision**: Single project structure (Option 1). This is a Python CLI application extending the existing a2a_orchestrator framework. The feature adds batch processing capabilities to the orchestrator core while preserving backward compatibility with 17 existing workflows. New atomic skills follow the Anthropic skills format (SKILL.md + optional scripts/) established in feature 011.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations detected** - Constitution template only, no project-specific gates defined.
