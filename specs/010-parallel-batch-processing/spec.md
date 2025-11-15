# Feature Specification: Parallel Batch Processing for A2A Orchestrator

**Feature Branch**: `010-parallel-batch-processing`
**Created**: 2025-11-15
**Status**: Draft
**Input**: User description: "Add parallel batch processing to A2A orchestrator for 10x speedup when fetching card images for Commander deck proxy generation. Support configurable batch_size, max_concurrent execution, and exponential backoff rate limiting. Refactor commander_to_proxies workflow to use reusable atomic skills (fetch-card-data, fetch-card-image, generate-slide) following single-responsibility principle."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Commander Proxy Generation (Priority: P1)

As a Commander player, I want to generate printable proxies for my entire deck in under 2 minutes, so I can quickly playtest expensive cards without waiting 15+ minutes for image downloads.

**Why this priority**: Delivers immediate, measurable value to end users. 10x speedup transforms the tool from "slow but useful" to "fast and essential" - the difference between users abandoning mid-workflow vs completing successfully.

**Independent Test**: Can be fully tested by running the workflow for "Atraxa, Praetors' Voice" (100 cards) and verifying completion time is ≤2 minutes vs ≥15 minutes baseline. Delivers complete PPTX output with all card images.

**Acceptance Scenarios**:

1. **Given** user provides commander "Atraxa, Praetors' Voice", **When** workflow executes with parallel batch processing enabled (batch_size=10, max_concurrent=3), **Then** system fetches 100 card images in ≤2 minutes and generates complete PPTX with 9 cards per slide
2. **Given** Scryfall API responds normally, **When** batch processing executes, **Then** system processes 10 batches of 10 cards each with 3 batches running concurrently, achieving ≥10x speedup over sequential processing
3. **Given** 5 cards fail to fetch due to network errors, **When** workflow completes, **Then** system generates PPTX with 95 real images + 5 placeholders, logs warnings for failures, and completes successfully

---

### User Story 2 - Reliable Rate Limit Handling (Priority: P2)

As a workflow operator, I want the system to automatically handle API rate limits with exponential backoff, so workflows complete successfully even when Scryfall throttles requests.

**Why this priority**: Prevents workflow failures from transient API issues. Rate limiting is inevitable when fetching 100+ images - graceful handling is the difference between 95% success rate vs 50% failure rate requiring manual retries.

**Independent Test**: Can be fully tested by simulating rate limit responses (429 errors) and verifying system applies exponential backoff (1s → 2s → 4s), retries up to 3 times, and recovers successfully.

**Acceptance Scenarios**:

1. **Given** Scryfall returns 429 (rate limit exceeded) on request 15 of 100, **When** retry logic triggers, **Then** system waits 1 second, retries successfully, and continues batch processing without failing entire workflow
2. **Given** rate limit error persists for 3 consecutive retries, **When** exponential backoff completes, **Then** system doubles wait time after each retry (1s → 2s → 4s) and fails gracefully with clear error message after max retries exhausted
3. **Given** mixed batch results (7 success, 2 rate-limited, 1 timeout), **When** batch completes, **Then** system retries only the 2 rate-limited requests, logs the 1 timeout as failure, and aggregates all results for next workflow step

---

### User Story 3 - Reusable Atomic Skills (Priority: P3)

As a workflow developer, I want to compose new workflows from single-responsibility skills (fetch-card-data, fetch-card-image, generate-slide), so I can build deck-analyzer or price-tracker workflows without duplicating code.

**Why this priority**: Enables sustainable ecosystem growth beyond just proxy generation. Atomic skills reduce maintenance burden and unlock future workflows (draft simulator, budget optimizer, legality checker) that reuse proven components.

**Independent Test**: Can be fully tested by creating a new workflow (e.g., card-art-wallpaper-generator) that reuses fetch-card-image skill without modifications, verifying skill contract validation passes and execution succeeds.

**Acceptance Scenarios**:

1. **Given** skills define clear input/output contracts (fetch-card-data: input {card_name: string}, output {card_json: object}), **When** workflow invokes skill, **Then** orchestrator validates contract before execution and rejects mismatched types at load time (not runtime)
2. **Given** skills follow single-responsibility (fetch-card-data returns JSON, does NOT fetch images), **When** developer composes deck-analyzer workflow, **Then** workflow reuses fetch-card-data + custom analysis skill, skipping image fetching entirely
3. **Given** workflow references non-existent skill or passes wrong parameter types, **When** workflow loads, **Then** orchestrator fails fast with actionable error message listing available skills and expected contracts

---

### Edge Cases

- What happens when **all cards in a batch fail** (Scryfall API completely down)? → System retries batch once after 5s delay, then fails entire workflow with clear error: "Scryfall unreachable for batch 3/10, aborting workflow"
- What happens when **user interrupts workflow mid-execution** (Ctrl+C during batch 5/10)? → Orchestrator logs completed batches to manifest, gracefully shuts down, and provides resumption instructions (future enhancement: auto-resume from manifest)
- What happens when **batch_size=0 or batch_size=-5**? → Workflow validation catches invalid config at load time, fails with error: "batch_size must be positive integer, got: 0"
- What happens when **max_concurrent exceeds total batches** (max_concurrent=10 but only 3 batches)? → System runs all 3 batches in parallel without errors, effectively acting as concurrent=3
- What happens when **skills have circular dependencies** (skill A calls B, B calls A)? → Orchestrator detects cycle during workflow graph analysis, fails at load time with error: "Circular dependency detected: A → B → A"
- What happens when **partial batch success** (batch 1: 10/10 success, batch 2: 3/10 success, batch 3: 10/10 success)? → System aggregates results, continues processing if ≥50% batches succeed, generates partial output with warnings for failed items
- How does system handle **network timeouts mid-batch** (3 of 10 requests hang)? → Apply request timeout (default 30s per card), log timeouts as failures, continue processing remaining 7 cards in batch

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Orchestrator MUST execute workflow steps in parallel batches when configured with batch_size (cards per batch) and max_concurrent (simultaneous batches) parameters
- **FR-002**: Batch processing MUST apply exponential backoff retry logic when API returns rate limit errors (429), starting at 1 second and doubling on each retry (1s → 2s → 4s), max 3 retries per request
- **FR-003**: System MUST support configurable retry strategies (exponential backoff, linear backoff, none) definable in workflow configuration
- **FR-004**: Skills MUST be decomposed into atomic, single-responsibility units following A2A protocol (fetch-card-data, fetch-card-image, generate-slide as separate skills)
- **FR-005**: Skills MUST define input/output contracts validated by orchestrator before workflow execution starts (fail fast on type mismatches or missing parameters)
- **FR-006**: Orchestrator MUST log all batch executions to structured manifest (batch number, card names, success/failure status, timestamps, errors) for debugging and resumption
- **FR-007**: System MUST generate partial outputs when ≥50% of batch operations succeed, logging clear warnings for failed items rather than failing entire workflow
- **FR-008**: Workflow validation MUST detect circular skill dependencies at load time and fail with actionable error messages before execution starts
- **FR-009**: Batch processing MUST preserve existing message caching performance (no cache invalidation side effects that degrade 25x speedup)
- **FR-010**: System MUST apply per-request timeouts (configurable, default 30 seconds) to prevent hung connections from blocking batch processing indefinitely
- **FR-011**: Retry logic MUST only retry transient errors (rate limits, network timeouts), NOT permanent failures (404 card not found, 401 authentication error)
- **FR-012**: Skills MUST be reusable across workflows without modifications (domain-agnostic where possible, e.g., fetch-json-from-url not fetch-edhrec-data)

### Key Entities

- **BatchConfig**: Workflow configuration controlling parallel execution (batch_size: integer, max_concurrent: integer, retry_strategy: ExponentialBackoff|LinearBackoff|None, request_timeout_seconds: integer)
- **Skill**: Atomic automation unit with defined input/output contract, executable via A2A protocol, single responsibility (e.g., fetch-card-image does NOT also resize or generate slides)
- **ExecutionManifest**: Structured log capturing batch execution state (batch_number, items_processed, success_count, failure_count, errors: [{item, error_type, message}], timestamps)
- **RetryPolicy**: Configuration for handling transient failures (max_retries: integer, initial_delay_seconds: float, backoff_strategy: ExponentialBackoff|LinearBackoff, retryable_errors: [HTTP_429, NETWORK_TIMEOUT])
- **CardData**: Domain entity representing card metadata (name, mana_cost, type_line, oracle_text, image_uris, prices) returned by fetch-card-data skill
- **DeckList**: Collection of card names with commander metadata, input to batch processing workflows

### Assumptions

- **API Behavior**: Scryfall API returns standard HTTP status codes (429 for rate limits, 404 for not found, 200 for success)
- **Network Reliability**: Network is generally reliable (≥95% uptime), but transient errors (timeouts, rate limits) occur occasionally and should be handled gracefully
- **Batch Size**: Default batch size of 10 cards balances throughput (not too small) with failure blast radius (not too large if batch fails)
- **Concurrency**: Default max_concurrent=3 respects API fair use policies while providing meaningful parallelism (3x speedup minimum even before batching)
- **Request Timeout**: 30 seconds per card fetch is sufficient for 99% of requests under normal conditions (average response time ~2s, timeout catches outliers)
- **Partial Success**: Users prefer partial outputs (95 cards with 5 failures) over all-or-nothing failure, especially for long-running workflows

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Commander deck proxy generation completes in ≤2 minutes for 100-card deck (down from ≥15 minutes baseline sequential processing), measured via execution manifest timestamps
- **SC-002**: Parallel batch processing achieves ≥10x speedup compared to sequential execution for image fetching operations (100 cards: 2min parallel vs 20min sequential)
- **SC-003**: System successfully handles partial failures with ≥95% batch success rate under normal API conditions (Scryfall uptime ≥99%)
- **SC-004**: Exponential backoff retry logic resolves ≥90% of transient rate limit errors (429 responses) without manual intervention or workflow failure
- **SC-005**: Workflow validation catches 100% of skill contract type mismatches and missing required parameters before execution starts (zero runtime contract errors)
- **SC-006**: Atomic skills reduce code duplication by ≥60% compared to monolithic workflow implementations (measured by lines of code in skill definitions vs legacy commander_to_proxies implementation)
- **SC-007**: Batch processing preserves existing message caching performance within ±5% of baseline (cache hit rate ≥95% maintained)
- **SC-008**: Execution manifests provide sufficient debugging context to diagnose 100% of batch failures without requiring code inspection or log archaeology
