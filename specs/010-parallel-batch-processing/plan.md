# Implementation Plan: Parallel Batch Processing for A2A Orchestrator

**Branch**: `010-parallel-batch-processing` | **Date**: 2025-11-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-parallel-batch-processing/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add parallel batch processing capabilities to the A2A orchestrator to achieve 10x speedup when fetching card images for Commander deck proxy generation. The feature supports configurable batch_size (1-50 cards per batch), max_concurrent execution (simultaneous batches), and exponential backoff rate limiting to handle API throttling. Commander deck proxy generation will complete in ≤2 minutes (down from ≥15 minutes baseline). Refactor commander_to_proxies workflow into reusable atomic skills (fetch-card-data, fetch-card-image, generate-slide) following single-responsibility principle to enable future workflow compositions.

## Technical Context

**Language/Version**: Python 3.9+ (existing codebase standard)
**Primary Dependencies**: asyncio (stdlib), aiohttp (async HTTP client for parallel requests), existing a2a_orchestrator modules (workflow_skill, message_cache, exceptions)
**Storage**: File-based (JSON manifests for execution logs, YAML workflows, skill markdown files in .claude/skills/)
**Testing**: pytest (existing test framework), pytest-asyncio (for async tests), pytest-aiohttp (HTTP mocking)
**Target Platform**: Linux/macOS CLI (existing deployment target)
**Project Type**: single (CLI library with workflow orchestrator)
**Performance Goals**: ≤2 minutes for 100-card deck proxy generation (≥10x speedup vs ≥15min baseline), ≥95% batch success rate under normal API conditions
**Constraints**: Scryfall API rate limits (must handle 429 responses), per-request timeout 30s (99% requests complete under normal conditions), max_concurrent default=3 (API fair use), batch_size default=10 (throughput vs failure blast radius balance)
**Scale/Scope**: 100-card decks (typical Commander format), 10 batches of 10 cards with 3 concurrent batches, ≥90% transient error recovery via exponential backoff

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS (no project constitution defined - proceeding with standard best practices)

**Notes**: Project constitution file exists but uses template format. Applying standard Python best practices:
- Test-first development (pytest with async support)
- Clear separation of concerns (batch processor, retry policy, skill contracts as separate modules)
- Integration testing for API interactions and workflow execution
- Fail-fast validation (contract validation at load time, not runtime)
- Observable execution (structured JSONL manifests for debugging)

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
a2a_orchestrator/
├── batch_processor.py         # NEW: Parallel batch execution engine
├── retry_policy.py             # NEW: Exponential backoff retry logic
├── skill_contract.py           # NEW: Input/output contract validation
├── execution_manifest.py       # NEW: Structured JSONL logging
├── workflow_skill.py           # MODIFIED: Add batch processing support
└── exceptions.py               # MODIFIED: Add batch-specific exceptions

.claude/skills/
├── fetch-card-data.md          # NEW: Atomic skill (Scryfall metadata fetch)
├── fetch-card-image.md         # NEW: Atomic skill (image download)
├── generate-slide.md           # NEW: Atomic skill (PPTX slide generation)
└── commander-to-proxies.md     # MODIFIED: Refactored to use atomic skills

tests/
├── integration/
│   ├── test_batch_processing_e2e.py        # NEW: Full workflow tests
│   └── test_scryfall_rate_limiting.py      # NEW: API interaction tests
└── unit/
    ├── test_batch_processor.py             # NEW: Batch logic unit tests
    ├── test_retry_policy.py                # NEW: Retry logic unit tests
    ├── test_skill_contract.py              # NEW: Contract validation tests
    └── test_execution_manifest.py          # NEW: Manifest logging tests

requirements.txt                # MODIFIED: Add aiohttp, pytest-asyncio
```

**Structure Decision**: Single project structure (Option 1) - CLI library with orchestrator core in `a2a_orchestrator/` and workflow skill definitions in `.claude/skills/`. Tests follow existing pattern with integration/ and unit/ separation. New modules (batch_processor, retry_policy, skill_contract, execution_manifest) added as peer modules to existing workflow_skill.py.

## Complexity Tracking

N/A - No constitutional violations to justify.
