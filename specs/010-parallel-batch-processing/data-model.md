# Data Model: Parallel Batch Processing

## Core Entities

### Entity: BatchConfig
**Purpose**: Configuration entity controlling parallel execution behavior for batch processing workflows

**Attributes**:
- `batch_size`: integer - Number of items to process in each batch (minimum: 1, default: 10)
  - Validation: Must be positive integer, workflow validation fails at load time if invalid
  - Rationale: Balances throughput (not too small) with failure blast radius (not too large)
- `max_concurrent`: integer - Maximum number of batches to execute simultaneously (minimum: 1, default: 3)
  - Validation: Must be positive integer
  - Rationale: Respects API fair use policies while providing meaningful parallelism (≥3x speedup)
  - Implementation: Enforced via `asyncio.Semaphore` for clean concurrency limiting
- `retry_strategy`: enum - Strategy for handling transient failures (ExponentialBackoff | LinearBackoff | None)
  - Validation: Must match one of defined strategy types
  - Default: ExponentialBackoff
  - Maps to: RetryPolicy entity for execution
- `request_timeout_seconds`: integer - Per-request timeout to prevent hung connections (minimum: 1, default: 30)
  - Validation: Must be positive integer
  - Rationale: 30s sufficient for 99% of requests, catches outliers preventing batch blocking

**Relationships**:
- Contains RetryPolicy configuration
- Referenced by Workflow execution context
- Validated against Skill requirements (some skills may override defaults)

**State Transitions**: Immutable once workflow execution starts (no runtime reconfiguration)

**Validation Rules**:
- FR-001: BatchConfig must be present for parallel execution
- Edge case handling: If max_concurrent exceeds total batches, system runs all batches in parallel
- Edge case handling: batch_size=0 or negative triggers workflow validation error at load time

---

### Entity: Skill
**Purpose**: Atomic automation unit with single responsibility, executable via A2A protocol

**Attributes**:
- `name`: string - Unique identifier for skill (pattern: kebab-case, e.g., "fetch-card-data")
  - Validation: Must be unique within skill registry
  - Rationale: Domain-agnostic naming encourages reusability (FR-012)
- `version`: string - Semantic version (e.g., "1.0.0")
  - Validation: Must follow semver format
  - Rationale: Enables skill evolution with backward compatibility tracking
- `description`: string - Human-readable purpose statement
- `single_responsibility`: string - Explicit declaration of what skill does (and does NOT do)
  - Validation: Required for documentation and contract adherence
- `contract`: SkillContract - JSON Schema defining input/output structure
  - Validation: Enforced at workflow load time via JSON Schema validation (FR-005)
- `dependencies`: array[string] - List of skill names this skill depends on
  - Validation: Orchestrator detects circular dependencies at load time (FR-008)
  - Default: Empty array (no dependencies)
- `executor_type`: enum - Execution strategy (async | sync | external_process)
  - Default: async
  - Rationale: Async executor enables parallel batch processing

**Relationships**:
- Has-a SkillContract (input/output schemas)
- References other Skills via dependencies array
- Referenced by Workflow steps
- Produces ExecutionManifest entries during execution

**State Transitions**:
- Discovered: Skill loaded from filesystem, not yet validated
- Validated: Contract validation passed, ready for workflow composition
- Executing: Currently running in batch or sequential context
- Completed: Execution finished with success/failure status

**Validation Rules**:
- FR-004: Must be atomic and single-responsibility
- FR-005: Contract validation must pass before workflow execution
- FR-008: No circular dependencies in dependency graph
- FR-012: Must be reusable across workflows without modifications

---

### Entity: SkillContract
**Purpose**: JSON Schema-based specification of skill input/output data structures, enabling fail-fast validation

**Attributes**:
- `input`: JSONSchema object - Schema for skill input parameters
  - Validation: Must be valid JSON Schema (draft-07 compatible)
  - Properties: type, properties, required, additionalProperties, etc.
  - Example: `{type: "object", properties: {card_name: {type: "string", minLength: 1}}, required: ["card_name"]}`
- `output`: JSONSchema object - Schema for skill output data
  - Validation: Must be valid JSON Schema
  - Rationale: Enables downstream skills to validate input compatibility
  - Example: `{type: "object", properties: {image_paths: {type: "object"}}, required: ["image_paths"]}`

**Relationships**:
- Owned by Skill (1:1 relationship)
- Validated against actual invocation inputs at workflow load time
- Referenced by Workflow composer for type compatibility checking

**State Transitions**: Immutable once skill is registered

**Validation Rules**:
- FR-005: Validation happens at workflow load time, not runtime
- Must fail fast with actionable error messages including JSON Pointer paths
- Type mismatches rejected before execution starts
- Example error: `"Skill input validation failed: 'batch_size' must be integer, got string\nPath: /batch_size\nExpected: {type: integer, minimum: 1}"`

---

### Entity: ExecutionManifest
**Purpose**: Structured append-only log capturing batch execution state for debugging, resumption, and auditing

**Attributes**:
- `event_type`: enum - Type of manifest entry (workflow_start | batch_start | batch_complete | workflow_complete | error)
- `timestamp`: ISO8601 string - UTC timestamp of event (e.g., "2025-01-15T14:30:22.123Z")
- `batch_number`: integer - Sequential batch identifier (1-indexed)
  - Validation: Must increment sequentially within workflow
- `items_processed`: array[string] - List of items in batch (e.g., card names)
- `success_count`: integer - Number of successful operations in batch
  - Validation: success_count + failure_count = items_processed.length
- `failure_count`: integer - Number of failed operations in batch
- `errors`: array[BatchError] - Detailed failure information
  - Structure: `[{item: string, error_type: string, message: string}]`
  - error_type examples: HTTP_429, NETWORK_TIMEOUT, HTTP_404, CONNECTION_RESET
- `duration_seconds`: float - Batch execution time (optional, for performance analysis)

**Relationships**:
- Produced by Skill executions during batch processing
- References BatchConfig indirectly (batch_number derived from batch_size)
- Consumed by debugging tools and future resumable workflow feature

**State Transitions**: Append-only (no updates or deletes), immutable once written

**Validation Rules**:
- FR-006: Must log all batch executions with structured data
- FR-007: Partial outputs generated when ≥50% batches succeed, manifest records all failures
- SC-008: Must provide sufficient context to diagnose 100% of failures
- File format: JSON Lines (JSONL) - newline-delimited JSON for streamability
- File naming: `.execution_manifests/{workflow_name}_{timestamp}.jsonl`

**Example Structure**:
```json
{
  "timestamp": "2025-01-15T14:30:28.789Z",
  "event_type": "batch_complete",
  "batch_number": 2,
  "items_processed": ["Sol Ring", "Command Tower", "Cyclonic Rift"],
  "success_count": 2,
  "failure_count": 1,
  "errors": [
    {
      "item": "Cyclonic Rift",
      "error_type": "HTTP_429",
      "message": "Rate limit exceeded, retry after 2s"
    }
  ],
  "duration_seconds": 4.567
}
```

---

### Entity: RetryPolicy
**Purpose**: Configuration for handling transient failures with exponential backoff and selective retry logic

**Attributes**:
- `max_retries`: integer - Maximum retry attempts per request (minimum: 0, default: 3)
  - Validation: Must be non-negative integer
  - Rationale: 3 retries balances resilience with failure detection speed
- `initial_delay_seconds`: float - Starting delay before first retry (minimum: 0.1, default: 1.0)
  - Validation: Must be positive float
- `max_delay_seconds`: float - Maximum delay cap for exponential backoff (default: 8.0)
  - Validation: Must be ≥ initial_delay_seconds
  - Rationale: Prevents unbounded wait times (8s cap means max total retry time ~15s for 3 attempts)
- `backoff_strategy`: enum - Delay calculation method (ExponentialBackoff | LinearBackoff | ConstantDelay)
  - ExponentialBackoff: delay = initial_delay * (2 ^ retry_count), capped at max_delay
  - LinearBackoff: delay = initial_delay * retry_count
  - ConstantDelay: delay = initial_delay (no increase)
- `jitter_enabled`: boolean - Add randomization to prevent thundering herd (default: true)
  - Validation: When true, adds ±25% random variance to calculated delay
  - Rationale: Prevents synchronized retries across concurrent batches
- `retryable_errors`: array[enum] - Error types eligible for retry
  - Values: [HTTP_429, NETWORK_TIMEOUT, CONNECTION_RESET, HTTP_503]
  - Validation: Must not include permanent errors (HTTP_404, HTTP_401, HTTP_403)
  - Default: [HTTP_429, NETWORK_TIMEOUT]

**Relationships**:
- Owned by BatchConfig (1:1 relationship)
- Applied by Skill executors during batch processing
- Logged in ExecutionManifest when retries occur

**State Transitions**:
- Active: Policy applied during request execution
- Retrying: Delay in progress between retry attempts
- Exhausted: max_retries reached, failure propagated to caller
- Succeeded: Retry succeeded before max_retries exhausted

**Validation Rules**:
- FR-002: Exponential backoff required for rate limit handling (1s → 2s → 4s → 8s)
- FR-003: Must support configurable strategies (exponential, linear, none)
- FR-011: Must distinguish transient (retryable) vs permanent (non-retryable) errors
- SC-004: Exponential backoff must resolve ≥90% of transient rate limit errors

**Implementation Notes**:
- Uses `tenacity` library for retry logic
- Retry decorator applied per-skill, not globally
- Example configuration:
```yaml
retry_strategy:
  type: exponential_backoff
  max_retries: 3
  initial_delay_seconds: 1.0
  max_delay_seconds: 8.0
  jitter_enabled: true
  retryable_errors:
    - HTTP_429
    - NETWORK_TIMEOUT
    - CONNECTION_RESET
```

---

### Entity: CardData
**Purpose**: Domain entity representing Magic: The Gathering card metadata returned by Scryfall API

**Attributes**:
- `name`: string - Card name (required, unique identifier)
  - Validation: Must be non-empty string
  - Example: "Sol Ring", "Command Tower"
- `mana_cost`: string - Mana cost in Oracle notation (e.g., "{2}{U}{B}")
  - Validation: Must match mana symbol format or be empty for lands
- `type_line`: string - Card type (e.g., "Artifact", "Legendary Creature — Angel")
  - Validation: Must be non-empty string
- `oracle_text`: string - Rules text
- `image_uris`: object - Image URLs keyed by size
  - Structure: `{small: string, normal: string, large: string, png: string, art_crop: string}`
  - Validation: Must contain at least one URI
  - Rationale: Enables size selection based on use case (proxies need "png" for print quality)
- `prices`: object - Price data (optional)
  - Structure: `{usd: string, usd_foil: string, eur: string}`
  - Used by: Future price-tracker workflows
- `set`: string - Set code (e.g., "LEA", "MH3")
- `collector_number`: string - Card number within set

**Relationships**:
- Referenced by DeckList (many-to-many: decks contain multiple cards, cards appear in multiple decks)
- Fetched by fetch-card-data skill
- Image URLs consumed by fetch-card-image skill

**State Transitions**:
- Not Fetched: Card name known but metadata not retrieved
- Fetched: API call completed, data cached
- Stale: Cache expired, requires re-fetch (future feature)

**Validation Rules**:
- FR-004: fetch-card-data skill returns CardData, does NOT fetch images (single responsibility)
- Must serialize to/from JSON for skill input/output contracts
- image_uris required for proxy generation workflows

**Example Data**:
```json
{
  "name": "Sol Ring",
  "mana_cost": "{1}",
  "type_line": "Artifact",
  "oracle_text": "{T}: Add {C}{C}.",
  "image_uris": {
    "small": "https://cards.scryfall.io/small/...",
    "normal": "https://cards.scryfall.io/normal/...",
    "large": "https://cards.scryfall.io/large/...",
    "png": "https://cards.scryfall.io/png/..."
  },
  "prices": {"usd": "1.25", "usd_foil": "15.00"},
  "set": "C21",
  "collector_number": "247"
}
```

---

### Entity: DeckList
**Purpose**: Domain entity representing a Commander deck configuration with commander metadata

**Attributes**:
- `commander`: string - Commander card name (required)
  - Validation: Must be legendary creature or valid commander (e.g., planeswalker with "can be your commander" text)
  - Example: "Atraxa, Praetors' Voice"
- `card_names`: array[string] - List of 99 cards in deck (not including commander)
  - Validation: Must contain exactly 99 unique card names for Commander format
  - Rationale: Commander format requires 100 cards total (1 commander + 99 others)
- `total_cards`: integer - Computed property (card_names.length + 1 for commander)
  - Validation: Must equal 100 for valid Commander deck
- `deck_name`: string - User-provided deck name (optional)
  - Default: "{commander} Commander Deck"
- `source_url`: string - URL where decklist was fetched (optional)
  - Example: "https://edhrec.com/api/commanders/atraxa-praetors-voice"
- `format`: enum - Format validation (Commander | Brawl | Future_formats)
  - Default: Commander
  - Rationale: Enables future support for Brawl (60 cards) or other formats

**Relationships**:
- Contains CardData references (via card_names array)
- Input to commander_to_proxies workflow
- Source for batch processing (card_names split into batches)

**State Transitions**:
- Draft: Partial decklist, less than 100 cards
- Complete: Valid 100-card Commander deck
- Validated: All card names resolved to CardData
- Processing: Batch fetching in progress
- Ready: All card images fetched, ready for proxy generation

**Validation Rules**:
- Must contain exactly 100 unique cards for Commander format
- Commander must be legendary creature or valid commander type
- Card names must resolve to real cards (validated via fetch-card-data skill)
- Edge case: What if commander is in the 99? → Validation error, commander must be separate

**Example Structure**:
```json
{
  "commander": "Atraxa, Praetors' Voice",
  "deck_name": "Atraxa Superfriends",
  "card_names": [
    "Sol Ring",
    "Command Tower",
    "Cyclonic Rift",
    "... 96 more cards ..."
  ],
  "total_cards": 100,
  "source_url": "https://edhrec.com/api/commanders/atraxa-praetors-voice",
  "format": "Commander"
}
```

---

## Entity Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Workflow Layer                          │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ configures
                                 ▼
                        ┌────────────────┐
                        │  BatchConfig   │
                        ├────────────────┤
                        │ batch_size     │
                        │ max_concurrent │◄────┐
                        │ retry_strategy │     │
                        │ timeout        │     │
                        └────────┬───────┘     │
                                 │             │
                                 │ contains    │
                                 ▼             │
                        ┌────────────────┐     │
                        │  RetryPolicy   │     │
                        ├────────────────┤     │
                        │ max_retries    │     │
                        │ initial_delay  │     │
                        │ backoff_type   │     │
                        │ retryable_errs │     │
                        └────────────────┘     │
                                               │ references
┌─────────────────────────────────────────────┼──────────────────┐
│                     Skill Layer             │                  │
└─────────────────────────────────────────────┼──────────────────┘
                                               │
                ┌──────────────────────────────┘
                │
                ▼
        ┌──────────────┐
        │    Skill     │
        ├──────────────┤
        │ name         │
        │ version      │
        │ dependencies │──┐ self-reference
        │ executor     │  │ (dependency graph)
        └───────┬──────┘  │
                │         │
                │ has-a   └───► Circular dependency
                ▼               detection (FR-008)
        ┌──────────────┐
        │SkillContract │
        ├──────────────┤
        │ input_schema │
        │ output_schema│
        └──────────────┘
                │
                │ validates
                │ (at workflow load time)
                ▼
        ┌──────────────────────────┐
        │  Invocation Inputs       │
        │  (from workflow YAML)    │
        └──────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      Execution Layer                            │
└─────────────────────────────────────────────────────────────────┘

    Skill Execution ──produces──► ┌──────────────────┐
                                   │ExecutionManifest │
                                   ├──────────────────┤
                                   │ batch_number     │
                                   │ items_processed  │
                                   │ success_count    │
                                   │ failure_count    │
                                   │ errors[]         │
                                   │ timestamps       │
                                   └──────────────────┘
                                            │
                                            │ logs to
                                            ▼
                                   ┌──────────────────┐
                                   │  JSONL File      │
                                   │ (.execution_     │
                                   │  manifests/)     │
                                   └──────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                       Domain Layer                              │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────┐           ┌──────────────┐
        │   DeckList   │──contains─►│  CardData    │
        ├──────────────┤           ├──────────────┤
        │ commander    │           │ name         │
        │ card_names[] │           │ mana_cost    │
        │ total_cards  │           │ type_line    │
        │ source_url   │           │ oracle_text  │
        └──────┬───────┘           │ image_uris{} │
               │                   │ prices{}     │
               │                   └──────────────┘
               │                           ▲
               │                           │
               │ splits into               │ fetched by
               │ batches                   │
               ▼                           │
        ┌──────────────┐                  │
        │ Batch 1:     │                  │
        │ [card1..10]  │──────────────────┘
        ├──────────────┤        fetch-card-data skill
        │ Batch 2:     │
        │ [card11..20] │
        ├──────────────┤
        │ Batch N:     │
        │ [card91..100]│
        └──────────────┘
              │
              │ parallel processing
              │ (max_concurrent=3 batches)
              │
              ▼
        ExecutionManifest
```

## Data Flow Through System

### Workflow Initialization
1. **Workflow Loaded** → BatchConfig validated → RetryPolicy configured
2. **Skills Discovered** → SkillContract schemas validated → Dependency graph analyzed for cycles
3. **DeckList Input** → Card names extracted → Batches created (batch_size=10)

### Parallel Batch Execution
4. **Batches Queued** → Semaphore controls concurrency (max_concurrent=3)
5. **Per-Batch Processing**:
   - Skill invoked with batch items
   - RetryPolicy applied to each API call
   - Results aggregated (success/failure counts)
   - ExecutionManifest entry logged (JSONL)
6. **Batch Completion** → Next batch starts (if semaphore permits)
7. **All Batches Complete** → Results merged → Partial output generated if ≥50% success

### Error Handling Flow
- **Transient Error** (HTTP_429) → RetryPolicy triggered → Exponential backoff → Retry up to max_retries
- **Permanent Error** (HTTP_404) → No retry → Logged to ExecutionManifest → Continue processing other items
- **Timeout** → Logged as failure → Batch continues with remaining items
- **Total Batch Failure** → Retry entire batch once → If fails again, abort workflow

### State Persistence
- **ExecutionManifest** → Append-only JSONL file → Enables debugging and future resumption
- **CardData** → Returned by skills → Not persisted (stateless skill execution)
- **DeckList** → Input only → Not modified during execution

## Validation Rules Summary

### Load-Time Validation (Fail Fast)
- BatchConfig: batch_size > 0, max_concurrent > 0, timeout > 0
- SkillContract: Input/output schemas valid JSON Schema
- Skill Dependencies: No circular references in dependency graph
- Workflow Composition: All referenced skills exist and contracts compatible

### Runtime Validation
- RetryPolicy: Only retry transient errors (not 404, 401, 403)
- ExecutionManifest: success_count + failure_count = items_processed.length
- Partial Success: Continue if ≥50% batches succeed (FR-007)
- Timeout Enforcement: Per-request timeout prevents hung connections

### Domain Validation
- DeckList: Exactly 100 cards for Commander format
- CardData: Must have at least one image_uri for proxy generation
- Batch Processing: If max_concurrent > total_batches, run all in parallel (no error)

## Performance Characteristics

### Expected Latencies
- **Sequential Processing**: ~20 minutes for 100 cards (12s per card average)
- **Parallel Batch Processing**: ≤2 minutes for 100 cards (SC-001)
- **Speedup Factor**: ≥10x improvement (SC-002)
- **Success Rate**: ≥95% batch success under normal API conditions (SC-003)

### Concurrency Model
- **asyncio.Semaphore**: Limits max_concurrent batches to prevent API overwhelming
- **asyncio.gather()**: Executes batches in parallel with exception handling
- **Connection Pooling**: Future enhancement if HTTP becomes bottleneck (currently not needed)

### Retry Timing (Exponential Backoff)
- Retry 1: 1s delay
- Retry 2: 2s delay
- Retry 3: 4s delay
- Retry 4: 8s delay (capped)
- Max total retry time: ~15s per request (1+2+4+8)

## Future Enhancements

### Resumable Workflows
- Parse ExecutionManifest on workflow restart
- Skip completed batches
- Resume from last checkpoint
- Enables Ctrl+C edge case handling

### Dynamic Batch Sizing
- Monitor average request latency
- Adjust batch_size in real-time
- Smaller batches if slow, larger if fast
- Optimize throughput vs failure blast radius

### Circuit Breaker Pattern
- Track consecutive failures per skill
- Temporarily disable skill after threshold
- Prevents cascading failures
- Re-enable after cooldown period

### Skill Versioning
- Support multiple versions simultaneously (v1.0.0, v2.0.0)
- Contract backward compatibility validation
- Workflow pins to specific skill versions
- Migration paths for breaking changes
