# magic-cards-edh-deck Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-07

## Active Technologies
- Python 3.9+ (existing modules), Markdown (skill definitions) + Existing modules (python-pptx, Pillow, requests), A2A framework (asyncio, dataclasses) (003-a2a-orchestration)
- File-based (manifest JSON, YAML workflows, skill markdown) (003-a2a-orchestration)
- Python 3.9+ (existing codebase) + pytest (test framework), pytest-cov (coverage), requests (existing), python-pptx (existing), Pillow (existing) (004-debt-remediation)
- Filesystem (manifest JSON, images, PPTX/PDF outputs) (004-debt-remediation)
- Python 3.9+ + Existing codebase (python-pptx, Pillow, requests), A2A workflow framework (asyncio, dataclasses) (005-template-aware-fetch)
- File-based (JSON manifests for fetch tracking, YAML for workflow definitions) (005-template-aware-fetch)
- Python 3.9+ + Existing (python-pptx, Pillow, requests), math module (sqrt) (006-fetch-size-hints)
- File-based (JSON manifests) (006-fetch-size-hints)
- Python 3.9+ (existing codebase standard) + Existing modules (python-pptx, Pillow, requests), json (stdlib), jsonschema (for strategy config validation) (007-protocol-first-refactor)
- JSON config files in `.config/strategies/` and `.config/oracle_knowledge.json`, manifest JSON files (existing) (007-protocol-first-refactor)
- File-based (YAML workflows, JSON manifests, skill outputs) (008-yaml-workflow-validation)
- Python 3.9+ (existing codebase standard) + asyncio (stdlib), existing orchestrator modules (workflow_skill, exceptions) (009-fix-async-skill-execution)
- N/A (bug fix, no data storage changes) (009-fix-async-skill-execution)
- Python 3.9+ (existing codebase standard) + asyncio (stdlib), aiohttp (async HTTP client for parallel requests), existing a2a_orchestrator modules (workflow_skill, message_cache, exceptions) (010-parallel-batch-processing)
- File-based (JSON manifests for execution logs, YAML workflows, skill markdown files in .claude/skills/) (010-parallel-batch-processing)

- Python 3.9+ + `python-pptx`, `Pillow`, `requests`, LibreOffice (system dependency) (002-consolidate-codebase)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.9+: Follow standard conventions

## Recent Changes
- 010-parallel-batch-processing: Added Python 3.9+ (existing codebase standard) + asyncio (stdlib), aiohttp (async HTTP client for parallel requests), existing a2a_orchestrator modules (workflow_skill, message_cache, exceptions)
- 009-fix-async-skill-execution: Added Python 3.9+ (existing codebase standard) + asyncio (stdlib), existing orchestrator modules (workflow_skill, exceptions)
- 009-fix-async-skill-execution: Added Python 3.9+ (existing codebase standard) + asyncio (stdlib), existing orchestrator modules (workflow_skill, exceptions)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
