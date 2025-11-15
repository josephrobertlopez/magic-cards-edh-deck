# Feature 010: Parallel Batch Processing for A2A Orchestrator

> **Status**: 📋 Planning Complete | **Branch**: `010-parallel-batch-processing` | **Created**: 2025-11-15

## Overview

Add parallel batch processing capabilities to the A2A orchestrator to achieve **10x speedup** (2 minutes vs 15+ minutes) for Commander deck proxy generation workflows. This feature introduces configurable batch execution, exponential backoff retry logic, and refactors workflows into reusable atomic skills following single-responsibility principles.

## Quick Links

- **[Specification](./spec.md)** - User scenarios, requirements, success criteria
- **[Implementation Plan](./plan.md)** - Technical context, architecture, project structure
- **[Research](./research.md)** - Technology decisions and best practices
- **[Data Model](./data-model.md)** - Entity definitions and relationships
- **[API Contracts](./contracts/)** - JSON Schema validation files
- **[Quickstart Guide](./quickstart.md)** - Installation, usage, migration guide
- **[Quality Checklist](./checklists/requirements.md)** - Spec validation results

## Problem Statement

**Current Pain**: Generating Commander deck proxies for 100 cards takes **15+ minutes** due to sequential image fetching from Scryfall API. Users abandon workflows mid-execution, and workflows fail completely on single API errors.

**Solution**: Parallel batch processing with:
- **Batch execution**: Process 10 cards concurrently in batches of 10 (configurable)
- **Retry logic**: Exponential backoff for rate limits (1s → 2s → 4s)
- **Atomic skills**: Reusable single-responsibility components
- **Graceful degradation**: Partial success (95 cards) instead of all-or-nothing failure

## Key Features

### 1. Parallel Batch Execution (P1)
- Configure `batch_size` (cards per batch) and `max_concurrent` (simultaneous batches)
- Process 100 cards in **≤2 minutes** (10x faster than sequential)
- Preserve existing 25x message caching performance (±5%)

### 2. Exponential Backoff Retry Logic (P2)
- Auto-handle Scryfall API rate limits (HTTP 429)
- Smart retry: Only transient errors (rate limits, timeouts), not permanent (404, 401)
- Resolve ≥90% of transient errors without manual intervention

### 3. Reusable Atomic Skills (P3)
- Single-responsibility skills: `fetch-card-data`, `fetch-card-image`, `generate-slide`
- Contract validation at workflow load time (fail-fast on type mismatches)
- Enable future workflows: deck-analyzer, price-tracker, draft-simulator

## Architecture Highlights

### Technology Stack
- **Language**: Python 3.9+
- **Async**: Native `asyncio` + `asyncio.Semaphore` for concurrency control
- **Retry**: `tenacity` library for exponential backoff
- **Validation**: JSON Schema for skill contract validation
- **Logging**: JSONL (JSON Lines) for resumable execution manifests

### Core Components

```
a2a_orchestrator/
├── batch_processor.py         # NEW: Parallel batch execution engine
├── retry_policy.py            # NEW: Exponential backoff retry logic
├── skill_contract.py          # NEW: Contract validation at load time
├── execution_manifest.py      # NEW: JSONL structured logging
└── orchestrator.py            # MODIFIED: Integrate batch processing

.claude/skills/
├── fetch-card-data/           # NEW: Atomic skill (Scryfall metadata)
├── fetch-card-image/          # NEW: Atomic skill (image download)
└── generate-slide/            # NEW: Atomic skill (PPTX generation)
```

### Data Flow

```
User Input (commander name)
    ↓
fetch-card-data skill → DeckList (100 cards)
    ↓
BatchProcessor (batch_size=10, max_concurrent=3)
    ↓
    ├─ Batch 1 (cards 1-10)  ──┐
    ├─ Batch 2 (cards 11-20) ──┼─ Parallel execution
    └─ Batch 3 (cards 21-30) ──┘     (3 concurrent)
         ↓ (continue...)
ExecutionManifest (JSONL logs)
    ↓
generate-slide skill → PPTX output (9 cards per slide)
```

## Success Metrics

| Metric | Target | Baseline | Improvement |
|--------|--------|----------|-------------|
| **Execution Time** | ≤2 minutes | 15+ minutes | **10x faster** |
| **Batch Success Rate** | ≥95% | ~60% (all-or-nothing) | **+35% reliability** |
| **Rate Limit Recovery** | ≥90% auto-resolved | 0% (manual retry) | **Automation** |
| **Contract Validation** | 100% at load time | 0% (runtime errors) | **Fail-fast** |
| **Code Duplication** | -60% LOC | Monolithic workflows | **Maintainability** |

## User Stories (Prioritized)

### P1: Fast Commander Proxy Generation
**As a** Commander player
**I want** to generate proxies in under 2 minutes
**So that** I don't abandon workflows waiting 15+ minutes for downloads

**Test**: Run workflow for "Atraxa, Praetors' Voice" → Complete in ≤2 min with 100 cards

---

### P2: Reliable Rate Limit Handling
**As a** workflow operator
**I want** automatic API rate limit handling
**So that** workflows complete successfully even when Scryfall throttles requests

**Test**: Simulate 429 errors → System applies exponential backoff and recovers ≥90% cases

---

### P3: Reusable Atomic Skills
**As a** workflow developer
**I want** single-responsibility skills with contracts
**So that** I can build new workflows (deck-analyzer, price-tracker) without duplicating code

**Test**: Create new workflow using `fetch-card-image` skill → Executes without modifications

## Getting Started

### Prerequisites
```bash
# Install dependencies
pip install tenacity>=8.2.0 jsonschema>=4.17.0 aiohttp>=3.8.0

# Verify existing dependencies
python -c "import asyncio, yaml; print('✓ Ready')"
```

### Run Example Workflow

```bash
# Generate Commander proxies with parallel batch processing
python -m a2a_orchestrator workflows/commander_to_proxies.yaml \
  --input commander:"Atraxa, Praetors' Voice" \
  --config batch_size:10 max_concurrent:3
```

**Expected Output**:
```
✓ Loaded 100 cards from EDHREC
✓ Batch 1/10 complete (10 cards, 2.1s)
✓ Batch 2/10 complete (10 cards, 1.9s)
...
✓ Batch 10/10 complete (10 cards, 2.0s)
✓ Generated atraxa_proxies.pptx (12 slides, 100 cards)
⏱ Total time: 1m 47s (vs 15m baseline)
```

See **[quickstart.md](./quickstart.md)** for detailed examples and migration guide.

## Documentation

### For Users
- **[Quickstart Guide](./quickstart.md)** - Installation, usage, configuration, debugging
- **[Spec](./spec.md)** - User scenarios, acceptance criteria, edge cases

### For Developers
- **[Implementation Plan](./plan.md)** - Architecture, technical context, structure
- **[Research](./research.md)** - Technology decisions and alternatives
- **[Data Model](./data-model.md)** - Entity definitions, validation rules, relationships
- **[API Contracts](./contracts/)** - JSON Schema files for validation

### JSON Schema Contracts

| File | Purpose | Key Properties |
|------|---------|----------------|
| **batch-config.schema.json** | Batch execution config | `batch_size`, `max_concurrent`, `retry_strategy` |
| **skill-contract.schema.json** | Skill I/O validation | `input_schema`, `output_schema`, `dependencies` |
| **execution-manifest.schema.json** | Structured logging | `batch_number`, `success_count`, `errors` |
| **workflow.schema.json** | Extended YAML schema | Batch mode flag, config references |

## Migration Path

### Before (Monolithic Workflow)
```yaml
# Old: Sequential processing, all-or-nothing failure
steps:
  - name: fetch-and-generate
    skill: commander-to-proxies-monolithic
    # 15+ minutes, fails on single error
```

### After (Atomic Skills + Batch Processing)
```yaml
# New: Parallel batches, graceful degradation
config:
  batch:
    batch_size: 10
    max_concurrent: 3

steps:
  - name: fetch-deck
    skill: fetch-card-data

  - name: fetch-images
    skill: fetch-card-image
    batch_mode: true  # Process in parallel batches

  - name: generate-slides
    skill: generate-slide
    batch_mode: true
```

**Benefits**: 10x faster, ≥95% success rate, reusable skills

See **[quickstart.md § Migration](./quickstart.md#migration)** for 6-step migration guide.

## Development Workflow

### Current Status: Planning Complete ✅

- [x] Specification written and validated
- [x] Research decisions documented
- [x] Data model formalized
- [x] API contracts defined (JSON Schema)
- [x] Quickstart guide created
- [ ] **Next**: Run `/speckit.tasks` to generate implementation tasks

### Next Steps

1. **Generate Tasks**: Run `/speckit.tasks` to create dependency-ordered task list
2. **Implementation**: Execute tasks from `tasks.md`
3. **Testing**: Unit tests (batch_processor, retry_policy) + integration tests (parallel workflows)
4. **Validation**: Verify success criteria (≤2min, ≥95% success, 10x speedup)

## Related Features

- **Feature 011**: [Anthropic Skills Format](../011-anthropic-skills-format/) - Enables SKILL.md + scripts/ pattern for atomic skills
- **Feature 003**: [A2A Orchestration](../003-a2a-orchestration/) - Foundation for message-passing workflow execution
- **Feature 005**: [Template-Aware Fetch](../005-template-aware-fetch/) - Scryfall API integration patterns

## Performance Benchmarks

### Sequential Processing (Baseline)
```
100 cards × 9 seconds/card = 900 seconds (15 minutes)
- Network latency: ~2s per request
- Processing: ~7s per card (image download + resize)
- No parallelism, no retry logic
```

### Parallel Batch Processing (This Feature)
```
100 cards ÷ 10 batch_size = 10 batches
10 batches ÷ 3 max_concurrent = 4 rounds
4 rounds × 20 seconds/round = 80 seconds (≤2 minutes)

Speedup: 900s ÷ 80s = 11.25x faster ✓
```

**Variables**: Adjust `batch_size` and `max_concurrent` to tune performance vs API respect.

## Troubleshooting

### Common Issues

**Issue**: Workflow fails with "Scryfall rate limit exceeded"
**Solution**: Increase `retry_strategy.initial_delay_seconds` from 1s to 2s

**Issue**: Execution manifest shows 40% batch failure rate
**Solution**: Reduce `max_concurrent` from 5 to 3 to respect API limits

**Issue**: Contract validation error: "Missing required parameter 'card_name'"
**Solution**: Check skill contract in SKILL.md frontmatter, ensure workflow passes all required inputs

See **[quickstart.md § Debugging](./quickstart.md#debugging)** for JSONL manifest analysis with `jq` commands.

## Contributing

This feature follows the **speckit workflow**:

1. **Specify**: `/speckit.specify` - Create feature specification
2. **Plan**: `/speckit.plan` - Generate implementation plan (research, data model, contracts)
3. **Tasks**: `/speckit.tasks` - Create dependency-ordered task list
4. **Implement**: `/speckit.implement` - Execute tasks from tasks.md
5. **Analyze**: `/speckit.analyze` - Cross-artifact consistency validation

**Current Phase**: Planning complete, ready for `/speckit.tasks`

## License & Attribution

Part of the **magic-cards-edh-deck** project.

---

**Feature Branch**: `010-parallel-batch-processing`
**Specification**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Status**: 📋 Planning Complete | **Next**: `/speckit.tasks`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
