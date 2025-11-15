# Research: Parallel Batch Processing

## Decision 1: Async Batch Processing Library
**Chosen**: Native `asyncio` with `asyncio.gather()` and `asyncio.Semaphore`

**Rationale**:
- Python's built-in `asyncio` provides all necessary primitives without external dependencies
- `asyncio.gather()` handles parallel task execution with built-in error aggregation via `return_exceptions=True`
- `asyncio.Semaphore` provides clean, efficient concurrency limiting (max_concurrent batches)
- Zero additional dependencies aligns with project's lightweight approach
- Direct async/await syntax is idiomatic Python 3.9+ and already used in existing A2A orchestrator codebase

**Alternatives Considered**:
- **`aiohttp.ClientSession` connection pooling**: Excellent for HTTP-specific optimizations (connection reuse, DNS caching), but adds dependency. Could be future enhancement if Scryfall API becomes primary bottleneck.
- **`asyncio.TaskGroup` (Python 3.11+)**: Cleaner error handling and automatic cancellation, but requires Python 3.11+ while project targets 3.9+. Future migration candidate.
- **Third-party libraries (`trio`, `anyio`)**: More opinionated async frameworks with structured concurrency, but introduce unnecessary complexity for straightforward batch processing use case.

**References**:
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [asyncio.gather() error handling patterns](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- [asyncio.Semaphore concurrency control](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore)

**Implementation Pattern**:
```python
async def process_batches(items, batch_size, max_concurrent):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch_with_limit(batch):
        async with semaphore:
            return await process_batch(batch)

    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
    results = await asyncio.gather(
        *[process_batch_with_limit(batch) for batch in batches],
        return_exceptions=True
    )
    return results
```

---

## Decision 2: Exponential Backoff Retry Strategies
**Chosen**: `tenacity` library with custom retry predicates

**Rationale**:
- Industry-standard library (5.5k+ GitHub stars, used by OpenStack, Google Cloud SDK)
- Declarative retry configuration via decorators matches skill-based architecture philosophy
- Built-in exponential backoff with jitter prevents thundering herd problems
- Flexible retry predicates allow distinguishing transient (429, timeout) vs permanent (404, 401) errors
- Comprehensive logging/callbacks for execution manifest integration
- Actively maintained (last release 2024) with Python 3.9+ support

**Alternatives Considered**:
- **`backoff` library**: Simpler API, but less flexible retry predicates. Harder to implement "retry only 429/timeout, not 404" requirement (FR-011).
- **Custom implementation**: Full control, but reinventing well-tested wheel. Exponential backoff with jitter is deceptively complex (need to prevent synchronized retries across concurrent batches).
- **`aiohttp-retry`**: HTTP-specific, tightly coupled to aiohttp. Would lock us into aiohttp ecosystem vs current requests-based approach.

**References**:
- [tenacity documentation](https://tenacity.readthedocs.io/)
- [tenacity GitHub repository](https://github.com/jd/tenacity)
- [Exponential backoff best practices (Google Cloud)](https://cloud.google.com/iot/docs/how-tos/exponential-backoff)
- [Jitter in retry strategies (AWS Architecture Blog)](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)

**Implementation Pattern**:
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

@retry(
    retry=retry_if_exception_type((RateLimitError, TimeoutError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),  # 1s, 2s, 4s, 8s
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def fetch_with_retry(url):
    response = await fetch(url)
    if response.status == 429:
        raise RateLimitError("API rate limit exceeded")
    return response
```

**Configuration Schema**:
```yaml
retry_strategy:
  type: exponential_backoff
  initial_delay_seconds: 1.0
  max_delay_seconds: 8.0
  max_retries: 3
  retryable_errors:
    - HTTP_429
    - NETWORK_TIMEOUT
    - CONNECTION_RESET
```

---

## Decision 3: Skill Contract Validation
**Chosen**: JSON Schema with fail-fast validation at workflow load time

**Rationale**:
- JSON Schema is language-agnostic specification format, ideal for A2A protocol interoperability
- Validation happens at workflow load time (before execution), satisfying FR-005 fail-fast requirement
- Supports complex validation rules (type checking, required fields, enum values, regex patterns)
- Rich error messages with JSON Pointers pinpoint exact validation failures
- No runtime overhead after initial validation (unlike Pydantic model creation)
- Already familiar format if project uses JSON for manifests/configs

**Alternatives Considered**:
- **Pydantic**: Excellent for Python-native validation with type hints, but couples skill contracts to Python ecosystem. A2A protocol should support non-Python skill implementations (future bash/Go skills).
- **Custom validation**: Full control over error messages, but error-prone and lacks standardization. JSON Schema provides battle-tested validation logic.
- **TypeScript-style interface definitions**: Clean syntax, but requires additional tooling (type checkers, transpilers) and less runtime validation support than JSON Schema.

**References**:
- [JSON Schema specification](https://json-schema.org/)
- [Python jsonschema library](https://python-jsonschema.readthedocs.io/)
- [JSON Schema best practices](https://json-schema.org/understanding-json-schema/)
- [JSON Schema validation error handling](https://python-jsonschema.readthedocs.io/en/stable/errors/)

**Implementation Pattern**:
```python
import jsonschema
from jsonschema import validate, ValidationError

# Skill contract definition (in skill metadata)
FETCH_CARD_DATA_CONTRACT = {
    "input": {
        "type": "object",
        "properties": {
            "card_name": {"type": "string", "minLength": 1}
        },
        "required": ["card_name"],
        "additionalProperties": False
    },
    "output": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "mana_cost": {"type": "string"},
            "type_line": {"type": "string"},
            "image_uris": {"type": "object"}
        },
        "required": ["name", "image_uris"]
    }
}

# Validation at workflow load time
def validate_skill_invocation(skill_contract, input_data):
    try:
        validate(instance=input_data, schema=skill_contract["input"])
    except ValidationError as e:
        raise WorkflowValidationError(
            f"Skill input validation failed: {e.message}\n"
            f"Path: {'/'.join(str(p) for p in e.path)}\n"
            f"Expected: {e.schema}"
        )
```

**Contract Definition Format** (in skill markdown frontmatter):
```yaml
---
name: fetch-card-data
version: 1.0.0
contract:
  input:
    type: object
    properties:
      card_name:
        type: string
        minLength: 1
    required: [card_name]
  output:
    type: object
    properties:
      name: {type: string}
      image_uris: {type: object}
    required: [name, image_uris]
---
```

---

## Decision 4: Execution Manifest Logging
**Chosen**: JSON Lines (JSONL) format with structured event logging

**Rationale**:
- JSON Lines (newline-delimited JSON) is streamable and resumable - can read partial logs even if workflow crashes mid-execution
- Structured data enables programmatic analysis (parsing, filtering, aggregation) vs unstructured text logs
- Each line is valid JSON, parseable independently - no need to read entire file into memory
- Industry standard for event streaming (used by ELK stack, Datadog, CloudWatch)
- Easy to implement with Python's built-in `json` module - just write one JSON object per line
- Supports execution manifest requirements (FR-006) and resumable workflows (edge case: Ctrl+C mid-batch)

**Alternatives Considered**:
- **Single JSON file**: Requires reading entire file into memory, can't stream results, file corruption if crash during write
- **SQLite database**: Overkill for append-only logging, adds dependency and complexity, harder to inspect manually
- **Python pickle files**: Not human-readable, version-dependent, security risks if unpickling untrusted data
- **Plain text logs**: Human-readable but hard to parse programmatically, no structure enforcement

**References**:
- [JSON Lines format specification](https://jsonlines.org/)
- [JSONL best practices](https://github.com/wardi/jsonlines)
- [Logging best practices (12-factor app)](https://12factor.net/logs)
- [Python logging to JSON](https://github.com/madzak/python-json-logger)

**Implementation Pattern**:
```python
import json
from datetime import datetime
from pathlib import Path

class ExecutionManifestLogger:
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def log_batch_start(self, batch_number, items):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "batch_start",
            "batch_number": batch_number,
            "item_count": len(items),
            "items": items
        }
        self._append_event(event)

    def log_batch_complete(self, batch_number, results):
        successes = [r for r in results if r.get("status") == "success"]
        failures = [r for r in results if r.get("status") == "failure"]

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "batch_complete",
            "batch_number": batch_number,
            "success_count": len(successes),
            "failure_count": len(failures),
            "errors": [
                {"item": f["item"], "error_type": f["error_type"], "message": f["message"]}
                for f in failures
            ]
        }
        self._append_event(event)

    def _append_event(self, event):
        with open(self.manifest_path, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def read_manifest(self):
        """Parse manifest for resumption or debugging"""
        if not self.manifest_path.exists():
            return []

        events = []
        with open(self.manifest_path, 'r') as f:
            for line in f:
                events.append(json.loads(line.strip()))
        return events
```

**Manifest File Structure** (example `.execution_manifests/commander_proxies_20250115_143022.jsonl`):
```jsonl
{"timestamp": "2025-01-15T14:30:22.123Z", "event_type": "workflow_start", "workflow": "commander_to_proxies", "commander": "Atraxa, Praetors' Voice", "total_cards": 100}
{"timestamp": "2025-01-15T14:30:22.456Z", "event_type": "batch_start", "batch_number": 1, "item_count": 10, "items": ["Sol Ring", "Command Tower", ...]}
{"timestamp": "2025-01-15T14:30:28.789Z", "event_type": "batch_complete", "batch_number": 1, "success_count": 10, "failure_count": 0, "errors": []}
{"timestamp": "2025-01-15T14:30:29.012Z", "event_type": "batch_start", "batch_number": 2, "item_count": 10, "items": ["Cyclonic Rift", ...]}
{"timestamp": "2025-01-15T14:30:35.234Z", "event_type": "batch_complete", "batch_number": 2, "success_count": 8, "failure_count": 2, "errors": [{"item": "Timetwister", "error_type": "HTTP_429", "message": "Rate limit exceeded"}, {"item": "Mox Diamond", "error_type": "NETWORK_TIMEOUT", "message": "Request timeout after 30s"}]}
```

**Debugging Query Examples**:
```python
# Find all failed items across workflow
def get_all_failures(manifest_path):
    events = ExecutionManifestLogger(manifest_path).read_manifest()
    return [
        error
        for event in events
        if event.get("event_type") == "batch_complete"
        for error in event.get("errors", [])
    ]

# Calculate workflow success rate
def get_success_rate(manifest_path):
    events = ExecutionManifestLogger(manifest_path).read_manifest()
    batch_results = [e for e in events if e.get("event_type") == "batch_complete"]
    total_success = sum(e["success_count"] for e in batch_results)
    total_failure = sum(e["failure_count"] for e in batch_results)
    return total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0.0
```

---

## Decision 5: A2A Protocol Atomic Skill Composition
**Chosen**: Single-responsibility skills with explicit dependency declarations and contract-first design

**Rationale**:
- Single-responsibility principle (SRP) from SOLID maximizes reusability - each skill does one thing well
- Contract-first design (define input/output schemas before implementation) enables parallel development and prevents integration surprises
- Explicit dependency declarations in skill frontmatter allow orchestrator to build execution DAG and detect cycles (FR-008)
- Domain-agnostic skill naming (`fetch-json-from-url` not `fetch-edhrec-data`) encourages reuse across workflows
- Aligns with A2A protocol philosophy of composable, protocol-driven automation

**Alternatives Considered**:
- **Monolithic skills**: Single `generate-commander-proxies` skill handling data fetch + image fetch + slide generation. Faster initial development but zero reusability (FR-012 violation).
- **Microservices-style skills**: Each skill as separate process/container. Too heavyweight for filesystem-based orchestrator, introduces network latency.
- **Implicit dependencies via data flow**: Skills infer dependencies from input/output data without declarations. Prevents static cycle detection (FR-008) and makes workflow behavior non-obvious.

**References**:
- [Single Responsibility Principle (Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html)
- [Contract-first development](https://www.thoughtworks.com/insights/blog/contract-first-development)
- [Dependency Injection patterns](https://martinfowler.com/articles/injection.html)
- [Unix philosophy (do one thing well)](https://en.wikipedia.org/wiki/Unix_philosophy)

**Skill Decomposition Pattern** (commander_to_proxies workflow):

**Before (Monolithic)**:
```yaml
# Old approach: single skill does everything
- skill: generate-commander-proxies
  inputs:
    commander: "Atraxa, Praetors' Voice"
  # Internally: fetch EDHREC → parse JSON → fetch 100 images → resize → generate PPTX
  # Problem: Can't reuse image fetching for other workflows, can't test components independently
```

**After (Atomic Composition)**:
```yaml
# New approach: compose small, reusable skills
- skill: fetch-json-from-url
  inputs:
    url: "https://edhrec.com/api/commanders/atraxa-praetors-voice"
  outputs: {decklist_json}

- skill: extract-card-names
  inputs: {decklist_json}
  outputs: {card_names_list}

- skill: fetch-card-images-batch  # This skill uses parallel batch processing
  inputs:
    card_names: {card_names_list}
    batch_size: 10
    max_concurrent: 3
  outputs: {image_paths_dict}

- skill: generate-proxy-slides
  inputs:
    card_names: {card_names_list}
    image_paths: {image_paths_dict}
    cards_per_slide: 9
  outputs: {pptx_path}
```

**Skill Contract Template** (frontmatter format):
```yaml
---
name: fetch-card-images-batch
version: 1.0.0
description: Fetch Magic card images from Scryfall API using parallel batch processing
single_responsibility: Fetch and save card images only (does not parse data, resize, or generate slides)

contract:
  input:
    type: object
    properties:
      card_names:
        type: array
        items: {type: string}
        minItems: 1
      batch_size:
        type: integer
        minimum: 1
        default: 10
      max_concurrent:
        type: integer
        minimum: 1
        default: 3
    required: [card_names]

  output:
    type: object
    properties:
      image_paths:
        type: object
        additionalProperties: {type: string}  # {card_name: file_path}
      success_count: {type: integer}
      failure_count: {type: integer}
      failures:
        type: array
        items:
          type: object
          properties:
            card_name: {type: string}
            error_type: {type: string}
            message: {type: string}
    required: [image_paths, success_count, failure_count]

dependencies: []  # No skill dependencies (could depend on fetch-card-data if needed)

reusability_notes: |
  Domain-agnostic image fetching logic. Can be reused for:
  - Card art wallpaper generation
  - Deck visual analysis workflows
  - Price comparison with image previews
  To make fully generic, could extract Scryfall API logic to separate fetch-scryfall-image skill
---
```

**Dependency Declaration for Cycle Detection**:
```yaml
# Skill A
---
name: skill-a
dependencies: [skill-b]  # A depends on B
---

# Skill B
---
name: skill-b
dependencies: [skill-c]  # B depends on C
---

# Skill C
---
name: skill-c
dependencies: [skill-a]  # C depends on A → CYCLE!
---

# Orchestrator detects: A → B → C → A
# Fails at load time: "Circular dependency detected in workflow: skill-a → skill-b → skill-c → skill-a"
```

**Orchestrator Cycle Detection Algorithm**:
```python
def detect_circular_dependencies(skills):
    """Topological sort to detect cycles in skill dependency graph"""
    graph = {skill.name: skill.dependencies for skill in skills}
    visited = set()
    rec_stack = set()

    def visit(node, path):
        if node in rec_stack:
            cycle = path[path.index(node):] + [node]
            raise CircularDependencyError(f"Circular dependency detected: {' → '.join(cycle)}")

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)

        for dependency in graph.get(node, []):
            visit(dependency, path + [node])

        rec_stack.remove(node)

    for skill_name in graph:
        visit(skill_name, [])
```

---

## Implementation Recommendations

### High-Priority Patterns
1. **Use asyncio.Semaphore for concurrency control**: Clean, efficient way to limit max_concurrent batches without complex queue management
2. **Implement tenacity retry decorators per-skill**: Each skill can define custom retry logic (some skills might need different backoff strategies)
3. **Validate skill contracts at workflow load time with JSON Schema**: Catch type errors before executing expensive batch operations
4. **Log all batch events to JSON Lines manifest**: Essential for debugging parallel execution and future resumable workflows
5. **Design skills with single responsibility in mind**: "Fetch data" and "fetch images" and "generate slides" should be separate skills

### Performance Optimizations
6. **Use asyncio.gather(return_exceptions=True)**: Prevents one failed batch from canceling all concurrent batches
7. **Apply jitter to exponential backoff**: Prevents thundering herd when multiple batches hit rate limits simultaneously (tenacity supports this via `wait_random_exponential`)
8. **Batch size tuning**: Start with batch_size=10, max_concurrent=3 (30 concurrent requests). Monitor Scryfall rate limits and adjust.
9. **Connection pooling**: If HTTP becomes bottleneck, consider migrating to aiohttp with connection pooling (but only after profiling proves it's needed)

### Error Handling
10. **Distinguish transient vs permanent errors**: Only retry 429, timeouts, connection resets. Do NOT retry 404 (card not found) or 401 (auth error)
11. **Aggregate batch results**: Process partial successes rather than all-or-nothing failure (per FR-007)
12. **Structured error logging**: Include error_type, item_name, timestamp, batch_number in all error logs for debuggability

### Testability
13. **Mock retry logic in tests**: Use tenacity's `@retry.retry_if_not_exception_type(SkipRetryInTests)` to disable retries during unit tests
14. **Fixture-based batch testing**: Create small test batches (3-5 items) to verify parallel logic without long test execution times
15. **Manifest replay for debugging**: Build tools to replay workflow from execution manifest for reproducible debugging

### Future Enhancements
16. **Resumable workflows**: Parse execution manifest to skip completed batches and resume from last checkpoint (enables Ctrl+C edge case handling)
17. **Dynamic batch sizing**: Adjust batch_size based on observed latency (smaller batches if requests are slow, larger if fast)
18. **Circuit breaker pattern**: Temporarily disable skill after repeated failures to prevent cascading failures (could use tenacity's stop_after_delay)
19. **Skill versioning**: Support multiple versions of same skill (v1, v2) with contract backward compatibility validation

### Code Organization
20. **Create dedicated modules**:
    - `a2a_orchestrator/batch_processor.py`: Batch processing logic with semaphore
    - `a2a_orchestrator/retry_policies.py`: Tenacity-based retry configurations
    - `a2a_orchestrator/contract_validator.py`: JSON Schema validation
    - `a2a_orchestrator/execution_manifest.py`: JSONL logging
    - `a2a_orchestrator/skill_registry.py`: Skill discovery and dependency resolution

### Dependency Management
21. **Add to requirements.txt**:
    ```
    tenacity>=8.2.0  # Exponential backoff retry logic
    jsonschema>=4.17.0  # Skill contract validation
    ```
22. **Keep asyncio stdlib-only**: No need for aiohttp/anyio/trio unless profiling shows bottleneck

### Documentation
23. **Document skill contract format**: Provide examples and templates for developers creating new skills
24. **Workflow composition guide**: Show how to compose atomic skills into workflows (with examples beyond commander proxies)
25. **Batch processing tuning guide**: Document how to tune batch_size and max_concurrent based on API rate limits and desired throughput
