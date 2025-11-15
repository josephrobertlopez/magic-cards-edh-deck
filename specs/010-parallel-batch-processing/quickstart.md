# Quickstart Guide: Parallel Batch Processing for A2A Orchestrator

## Table of Contents
1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Configuration](#configuration)
4. [Skill Creation](#skill-creation)
5. [Debugging](#debugging)
6. [Migration](#migration)

---

## Installation

### Dependencies

The parallel batch processing feature requires the following new dependencies:

```bash
pip install tenacity==8.2.3 jsonschema==4.19.1
```

These packages are added to `requirements.txt`:
- **tenacity**: Provides exponential backoff retry logic for handling transient API failures
- **jsonschema**: Validates skill contracts at workflow load time for fail-fast error detection

### Verify Installation

Check that existing dependencies are satisfied:

```bash
# Required existing packages
pip install requests python-pptx Pillow PyYAML

# Verify installation
python -c "import tenacity, jsonschema; print('Dependencies installed successfully')"
```

---

## Basic Usage

### Simple Batch Workflow Example

Here's a minimal workflow that uses parallel batch processing to fetch card images 10x faster:

**File: `workflows/fetch_cards_parallel.yaml`**

```yaml
name: "fetch_cards_parallel"
description: "Fetch card images using parallel batch processing"
version: "2.0"

inputs:
  card_names:
    type: array
    required: true
    description: "List of card names to fetch"

# Batch processing configuration
batch_config:
  batch_size: 10           # Process 10 cards per batch
  max_concurrent: 3        # Run 3 batches in parallel
  retry_strategy: exponential_backoff
  request_timeout_seconds: 30

steps:
  # Step 1: Fetch card metadata (parallel batches)
  - name: fetch_metadata
    skill: data/fetch-card-data
    batch_mode: true       # Enable parallel batch processing
    args:
      card_names: "{{inputs.card_names}}"
    outputs:
      cards_data: "{{result.cards}}"

  # Step 2: Fetch card images (parallel batches)
  - name: fetch_images
    skill: images/fetch-card-image
    batch_mode: true
    args:
      cards_data: "{{steps.fetch_metadata.outputs.cards_data}}"
    outputs:
      image_paths: "{{result.images}}"

outputs:
  images: "{{steps.fetch_images.outputs.image_paths}}"
  manifest: ".execution_manifests/fetch_cards_parallel_{{workflow_run_id}}.jsonl"
```

### Running the Workflow

```bash
# Execute workflow with card list
python -m a2a_orchestrator.cli run \
  --workflow workflows/fetch_cards_parallel.yaml \
  --input '{"card_names": ["Sol Ring", "Command Tower", "Lightning Greaves"]}'

# Expected output:
# [2025-01-15 14:30:20] Workflow 'fetch_cards_parallel' started
# [2025-01-15 14:30:22] Batch 1/1 complete: 3 success, 0 failures (2.1s)
# [2025-01-15 14:30:22] Workflow complete. Manifest: .execution_manifests/fetch_cards_parallel_550e8400.jsonl
```

### Expected Performance

For a 100-card Commander deck:

- **Sequential (old)**: 15-20 minutes (12s per card average)
- **Parallel batch (new)**: ≤2 minutes (10x+ speedup)
- **Configuration**: `batch_size=10, max_concurrent=3`

**Speedup breakdown:**
1. Batching reduces overhead: 10 cards per batch = 10 batches total
2. Parallelism: 3 batches run simultaneously
3. Effective concurrency: ~30 cards in flight at once
4. Result: **10-15x faster** for image-heavy workflows

---

## Configuration

### Batch Configuration Options

The `batch_config` section controls parallel execution behavior. All parameters are optional with sensible defaults.

#### Basic Configuration

```yaml
batch_config:
  batch_size: 10              # Items per batch (default: 10)
  max_concurrent: 3           # Simultaneous batches (default: 3)
  retry_strategy: exponential_backoff  # Retry approach (default)
  request_timeout_seconds: 30 # Per-request timeout (default: 30)
```

#### Advanced Retry Configuration

```yaml
batch_config:
  batch_size: 10
  max_concurrent: 3
  retry_strategy: exponential_backoff
  request_timeout_seconds: 30

  # Detailed retry policy
  retry_policy:
    max_retries: 3                    # Max attempts per request (default: 3)
    initial_delay_seconds: 1.0        # Starting delay (default: 1.0)
    max_delay_seconds: 8.0            # Delay cap (default: 8.0)
    jitter_enabled: true              # Add randomness to prevent thundering herd
    retryable_errors:                 # Only retry these error types
      - HTTP_429                      # Rate limit exceeded
      - NETWORK_TIMEOUT               # Network timeout
      - CONNECTION_RESET              # Connection reset by peer
```

### Retry Strategies

#### 1. Exponential Backoff (Recommended)

Delay doubles after each retry: 1s → 2s → 4s → 8s (capped)

```yaml
retry_strategy: exponential_backoff
retry_policy:
  max_retries: 3
  initial_delay_seconds: 1.0
  max_delay_seconds: 8.0
```

**Best for**: API rate limiting (Scryfall, EDHREC)
**Resolves**: ≥90% of transient 429 errors
**Max total retry time**: ~15 seconds (1+2+4+8)

#### 2. Linear Backoff

Delay increases linearly: 1s → 2s → 3s → 4s

```yaml
retry_strategy: linear_backoff
retry_policy:
  max_retries: 3
  initial_delay_seconds: 1.0
```

**Best for**: Predictable retry timing
**Use case**: Services with fixed retry windows

#### 3. No Retry

Fail immediately on any error (fast fail)

```yaml
retry_strategy: none
```

**Best for**: Local operations, non-network skills
**Use case**: Testing, deterministic failures

### Tuning Batch Size

Choose `batch_size` based on failure blast radius vs throughput:

| Batch Size | Throughput | Failure Impact | Best For |
|------------|------------|----------------|----------|
| 5 | Medium | Low | Unreliable APIs |
| 10 | High | Medium | **Recommended default** |
| 20 | Very High | High | Stable APIs |
| 50 | Maximum | Very High | Local operations |

**Formula**: `total_batches = ceil(total_items / batch_size)`

Example: 100 cards with `batch_size=10` → 10 batches

### Tuning Concurrency

Choose `max_concurrent` based on API limits and available bandwidth:

| Concurrency | Speedup | API Pressure | Best For |
|-------------|---------|--------------|----------|
| 1 | None | Low | Rate-limited APIs |
| 3 | 3x | Medium | **Recommended default** |
| 5 | 5x | High | Generous APIs |
| 10 | 10x | Very High | Local operations |

**Warning**: High concurrency may trigger rate limits. Start with 3 and increase gradually.

---

## Skill Creation

### Atomic Skill Principles

Skills in the batch processing paradigm follow **single-responsibility** design:

1. **One job per skill**: Fetch data OR transform data, not both
2. **Clear contracts**: Define input/output schemas explicitly
3. **Batch-aware**: Support both single-item and batch execution
4. **Stateless**: No side effects between invocations

### Creating a Batch-Compatible Skill

**File: `.claude/skills/data/fetch-card-data.md`**

```markdown
---
name: fetch-card-data
version: 1.0.0
description: Fetches Magic card metadata from Scryfall API
single_responsibility: Returns card JSON. Does NOT fetch images or generate slides.
executor_type: async
dependencies: []
---

# Skill: fetch-card-data

## Input Contract

```json
{
  "type": "object",
  "properties": {
    "card_name": {
      "type": "string",
      "minLength": 1,
      "description": "Card name (e.g., 'Sol Ring')"
    }
  },
  "required": ["card_name"],
  "additionalProperties": false
}
```

## Output Contract

```json
{
  "type": "object",
  "properties": {
    "card_data": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "mana_cost": {"type": "string"},
        "type_line": {"type": "string"},
        "oracle_text": {"type": "string"},
        "image_uris": {
          "type": "object",
          "properties": {
            "png": {"type": "string", "format": "uri"},
            "large": {"type": "string", "format": "uri"}
          },
          "required": ["png"]
        },
        "prices": {"type": "object"}
      },
      "required": ["name", "image_uris"]
    }
  },
  "required": ["card_data"]
}
```

## Implementation

```python
import asyncio
import aiohttp
from typing import Dict, Any

async def execute(card_name: str) -> Dict[str, Any]:
    """Fetch card metadata from Scryfall API.

    This skill ONLY fetches metadata. Image downloading is handled
    by the separate 'fetch-card-image' skill.
    """
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=30) as response:
            if response.status == 404:
                raise ValueError(f"Card not found: {card_name}")
            elif response.status == 429:
                raise RateLimitError("Scryfall rate limit exceeded")

            response.raise_for_status()
            card_data = await response.json()

    return {"card_data": card_data}
```
```

### Contract Validation

When the orchestrator loads the workflow, it validates contracts **before execution**:

```python
# Automatic validation at workflow load time
from jsonschema import validate, ValidationError

try:
    validate(instance=skill_input, schema=skill.input_schema)
except ValidationError as e:
    print(f"Skill input validation failed: {e.message}")
    print(f"Path: {e.json_path}")
    print(f"Expected: {e.schema}")
    # Workflow fails BEFORE execution starts (fail fast)
```

### Example: Creating fetch-card-image Skill

**File: `.claude/skills/images/fetch-card-image.md`**

```markdown
---
name: fetch-card-image
version: 1.0.0
description: Downloads card images from Scryfall image URIs
single_responsibility: Downloads images. Does NOT fetch metadata or generate slides.
executor_type: async
dependencies: [fetch-card-data]
---

# Skill: fetch-card-image

## Input Contract

```json
{
  "type": "object",
  "properties": {
    "card_data": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "image_uris": {
          "type": "object",
          "properties": {
            "png": {"type": "string", "format": "uri"}
          },
          "required": ["png"]
        }
      },
      "required": ["name", "image_uris"]
    },
    "output_dir": {
      "type": "string",
      "default": ".claude/downloads/images"
    }
  },
  "required": ["card_data"],
  "additionalProperties": false
}
```

## Output Contract

```json
{
  "type": "object",
  "properties": {
    "image_path": {
      "type": "string",
      "description": "Local filesystem path to downloaded image"
    },
    "card_name": {
      "type": "string"
    }
  },
  "required": ["image_path", "card_name"]
}
```

## Implementation

```python
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any

async def execute(card_data: Dict[str, Any], output_dir: str = ".claude/downloads/images") -> Dict[str, Any]:
    """Download card image from Scryfall.

    Accepts output from fetch-card-data skill via contract validation.
    """
    card_name = card_data["name"]
    image_url = card_data["image_uris"]["png"]

    # Sanitize filename
    safe_name = card_name.replace("/", "_").replace(" ", "_")
    output_path = Path(output_dir) / f"{safe_name}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Download image
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url, timeout=30) as response:
            response.raise_for_status()
            image_data = await response.read()

    # Save to disk
    output_path.write_bytes(image_data)

    return {
        "image_path": str(output_path),
        "card_name": card_name
    }
```
```

### Dependency Graph Validation

The orchestrator detects circular dependencies at load time:

```yaml
# This configuration will FAIL at load time
skills:
  - name: skill-a
    dependencies: [skill-b]

  - name: skill-b
    dependencies: [skill-a]

# Error: Circular dependency detected: skill-a → skill-b → skill-a
```

---

## Debugging

### Reading Execution Manifests

Execution manifests are append-only JSONL (JSON Lines) files in `.execution_manifests/`:

**File: `.execution_manifests/fetch_cards_parallel_550e8400.jsonl`**

```jsonl
{"event_type":"workflow_start","timestamp":"2025-01-15T14:30:20.000Z","workflow_name":"fetch_cards_parallel","workflow_run_id":"550e8400-e29b-41d4-a716-446655440000"}
{"event_type":"batch_start","timestamp":"2025-01-15T14:30:20.123Z","batch_number":1,"items_processed":["Sol Ring","Command Tower","Lightning Greaves"],"workflow_name":"fetch_cards_parallel","workflow_run_id":"550e8400-e29b-41d4-a716-446655440000"}
{"event_type":"batch_complete","timestamp":"2025-01-15T14:30:22.234Z","batch_number":1,"items_processed":["Sol Ring","Command Tower","Lightning Greaves"],"success_count":2,"failure_count":1,"errors":[{"item":"Lightning Greaves","error_type":"HTTP_429","message":"Rate limit exceeded","retries_attempted":2}],"duration_seconds":2.111,"workflow_name":"fetch_cards_parallel","workflow_run_id":"550e8400-e29b-41d4-a716-446655440000"}
{"event_type":"workflow_complete","timestamp":"2025-01-15T14:30:22.250Z","workflow_name":"fetch_cards_parallel","workflow_run_id":"550e8400-e29b-41d4-a716-446655440000"}
```

### Analyzing Manifests

**Find all failed items:**

```bash
jq 'select(.event_type == "batch_complete") | select(.failure_count > 0) | .errors[]' \
  .execution_manifests/fetch_cards_parallel_550e8400.jsonl
```

Output:
```json
{
  "item": "Lightning Greaves",
  "error_type": "HTTP_429",
  "message": "Rate limit exceeded",
  "retries_attempted": 2
}
```

**Calculate success rate:**

```bash
jq -s 'map(select(.event_type == "batch_complete")) |
       {total_success: (map(.success_count) | add),
        total_failure: (map(.failure_count) | add)}' \
  .execution_manifests/fetch_cards_parallel_550e8400.jsonl
```

Output:
```json
{
  "total_success": 97,
  "total_failure": 3
}
```

**Performance analysis:**

```bash
jq -s 'map(select(.event_type == "batch_complete")) |
       {batches: length,
        total_duration: (map(.duration_seconds) | add),
        avg_batch_time: ((map(.duration_seconds) | add) / length)}' \
  .execution_manifests/fetch_cards_parallel_550e8400.jsonl
```

Output:
```json
{
  "batches": 10,
  "total_duration": 45.678,
  "avg_batch_time": 4.5678
}
```

### Common Errors

#### 1. Rate Limit Errors (HTTP_429)

**Symptom:** Many failures with `"error_type": "HTTP_429"`

**Solution:** Increase retry delays or reduce concurrency

```yaml
batch_config:
  max_concurrent: 2  # Reduce from 3 to 2
  retry_policy:
    initial_delay_seconds: 2.0  # Increase from 1.0 to 2.0
    max_delay_seconds: 16.0     # Increase cap
```

#### 2. Network Timeouts

**Symptom:** Failures with `"error_type": "NETWORK_TIMEOUT"`

**Solution:** Increase request timeout

```yaml
batch_config:
  request_timeout_seconds: 60  # Increase from 30 to 60
```

#### 3. Contract Validation Failures

**Symptom:** Workflow fails at load time with schema errors

```
Skill input validation failed: 'batch_size' must be integer, got string
Path: /batch_size
Expected: {type: integer, minimum: 1}
```

**Solution:** Fix workflow YAML to match skill contract

```yaml
# Wrong
args:
  batch_size: "10"  # String

# Correct
args:
  batch_size: 10    # Integer
```

#### 4. Circular Dependencies

**Symptom:** Workflow fails at load time

```
Error: Circular dependency detected: fetch-card-data → enrich-metadata → fetch-card-data
```

**Solution:** Refactor skills to break circular dependency

```yaml
# Before (circular)
skill-a:
  dependencies: [skill-b]
skill-b:
  dependencies: [skill-a]

# After (fixed)
skill-a:
  dependencies: []
skill-b:
  dependencies: [skill-a]
```

### Debugging Workflow Execution

Enable verbose logging:

```bash
export A2A_LOG_LEVEL=DEBUG

python -m a2a_orchestrator.cli run \
  --workflow workflows/fetch_cards_parallel.yaml \
  --input '{"card_names": ["Sol Ring"]}'
```

Output includes:
- Batch creation: "Created 1 batches (batch_size=10)"
- Semaphore acquisition: "Batch 1 acquired semaphore (2/3 slots available)"
- Retry attempts: "Retry 1/3 for 'Sol Ring' after HTTP_429 (delay: 1.0s)"
- Contract validation: "Validated skill input against schema: PASS"

---

## Migration

### Migrating Existing Workflows to Batch Processing

Follow these steps to refactor legacy workflows for 10x speedup:

#### Step 1: Identify Batch-Eligible Steps

Look for steps that:
- Fetch data from APIs (Scryfall, EDHREC)
- Download images or files
- Process lists of items independently

**Example: Legacy `commander_to_proxies.yaml`**

```yaml
steps:
  - name: fetch_page
    skill: data/fetch-web-page
    # ❌ Not batch-eligible (single fetch)

  - name: extract_cards
    skill: data/extract-cards-from-html
    # ❌ Not batch-eligible (single HTML parse)

  - name: generate_proxies
    workflow: workflows/proxy_pipeline_composed.yaml
    # ✅ BATCH-ELIGIBLE (processes 100 cards)
```

#### Step 2: Decompose Monolithic Skills

Break large skills into atomic units following single-responsibility:

**Before: Monolithic `generate-proxies` skill**

```python
# ❌ Does too much: fetch metadata, download images, generate slides
def generate_proxies(card_names: List[str]) -> str:
    cards_data = []
    for card in card_names:
        metadata = fetch_from_scryfall(card)      # API call
        image_path = download_image(metadata)     # Download
        cards_data.append((metadata, image_path))

    pptx = create_presentation()
    for metadata, image_path in cards_data:
        add_slide(pptx, metadata, image_path)     # Slide generation

    return save_pptx(pptx)
```

**After: Three atomic skills**

```python
# ✅ Skill 1: fetch-card-data (API only)
async def fetch_card_data(card_name: str) -> Dict:
    return await scryfall_api.get_card(card_name)

# ✅ Skill 2: fetch-card-image (download only)
async def fetch_card_image(card_data: Dict) -> str:
    url = card_data["image_uris"]["png"]
    return await download_file(url, output_dir)

# ✅ Skill 3: generate-slide (slide creation only)
def generate_slide(image_path: str, card_data: Dict) -> None:
    pptx.add_slide(image_path, card_data)
```

#### Step 3: Add Batch Configuration

Add `batch_config` section to workflow:

```yaml
name: "commander_to_proxies_v2"
description: "Parallel batch processing version (10x faster)"
version: "2.0"

inputs:
  commander_name:
    type: string
    required: true

# NEW: Batch configuration
batch_config:
  batch_size: 10
  max_concurrent: 3
  retry_strategy: exponential_backoff
  request_timeout_seconds: 30
```

#### Step 4: Enable Batch Mode on Steps

Add `batch_mode: true` to batch-eligible steps:

```yaml
steps:
  # Non-batched (single commander fetch)
  - name: fetch_page
    skill: data/fetch-web-page
    args:
      url: "https://edhrec.com/commanders/{{inputs.commander_name}}"
    outputs:
      html_path: "{{result.html_path}}"

  # Non-batched (single HTML parse)
  - name: extract_cards
    skill: data/extract-cards-from-html
    args:
      html_file: "{{steps.fetch_page.outputs.html_path}}"
    outputs:
      card_names: "{{result.card_names}}"

  # NEW: Batched card metadata fetching
  - name: fetch_metadata
    skill: data/fetch-card-data
    batch_mode: true  # Process 10 cards per batch, 3 batches in parallel
    args:
      card_names: "{{steps.extract_cards.outputs.card_names}}"
    outputs:
      cards_data: "{{result.cards}}"

  # NEW: Batched image downloads
  - name: fetch_images
    skill: images/fetch-card-image
    batch_mode: true
    args:
      cards_data: "{{steps.fetch_metadata.outputs.cards_data}}"
    outputs:
      image_paths: "{{result.images}}"

  # Non-batched (single PPTX generation)
  - name: generate_pptx
    skill: slides/generate-proxy-slides
    args:
      image_paths: "{{steps.fetch_images.outputs.image_paths}}"
      cards_data: "{{steps.fetch_metadata.outputs.cards_data}}"
    outputs:
      pptx_file: "{{result.pptx_path}}"
```

#### Step 5: Update Skill Contracts

Ensure skills have explicit input/output schemas:

**Before: No contract (runtime errors possible)**

```markdown
# Skill: fetch-card-data
No schema defined
```

**After: Explicit contract (fail-fast validation)**

```markdown
---
name: fetch-card-data
version: 1.0.0
---

## Input Contract
```json
{
  "type": "object",
  "properties": {
    "card_name": {"type": "string", "minLength": 1}
  },
  "required": ["card_name"]
}
```

## Output Contract
```json
{
  "type": "object",
  "properties": {
    "card_data": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "image_uris": {"type": "object"}
      },
      "required": ["name", "image_uris"]
    }
  },
  "required": ["card_data"]
}
```
```

#### Step 6: Test Migration

Run both workflows side-by-side to verify correctness:

```bash
# Legacy workflow (slow)
time python -m a2a_orchestrator.cli run \
  --workflow workflows/commander_to_proxies.yaml \
  --input '{"commander_name": "atraxa-praetors-voice"}'
# Expected: ~15 minutes

# New batch workflow (fast)
time python -m a2a_orchestrator.cli run \
  --workflow workflows/commander_to_proxies_v2.yaml \
  --input '{"commander_name": "atraxa-praetors-voice"}'
# Expected: ≤2 minutes (10x faster)
```

Compare outputs:
```bash
# Verify PPTX files are identical (except metadata)
diff <(unzip -l output_legacy.pptx | sort) \
     <(unzip -l output_batch.pptx | sort)
```

### Migration Checklist

- [ ] Identify batch-eligible workflow steps (API calls, downloads)
- [ ] Decompose monolithic skills into atomic units (single responsibility)
- [ ] Add `batch_config` section to workflow YAML
- [ ] Enable `batch_mode: true` on eligible steps
- [ ] Define explicit input/output contracts for all skills
- [ ] Validate contracts using JSON Schema
- [ ] Test workflow with small dataset (10 cards)
- [ ] Test workflow with full dataset (100 cards)
- [ ] Compare outputs with legacy workflow
- [ ] Verify ≥10x speedup for 100-card workflows
- [ ] Review execution manifests for errors
- [ ] Update documentation and examples

---

## Next Steps

1. **Read the spec**: Review `specs/010-parallel-batch-processing/spec.md` for detailed requirements
2. **Study contracts**: Examine JSON schemas in `specs/010-parallel-batch-processing/contracts/`
3. **Explore examples**: Check `workflows/` for batch-enabled workflow examples
4. **Create skills**: Build atomic skills following the contract validation pattern
5. **Monitor manifests**: Use `.execution_manifests/` to debug and optimize performance

---

## Additional Resources

- **Spec**: `specs/010-parallel-batch-processing/spec.md` - Full requirements and user stories
- **Data Model**: `specs/010-parallel-batch-processing/data-model.md` - Entity relationships
- **Plan**: `specs/010-parallel-batch-processing/plan.md` - Implementation roadmap
- **Contracts**: `specs/010-parallel-batch-processing/contracts/` - JSON Schema definitions
- **Tenacity Docs**: https://tenacity.readthedocs.io/ - Retry library documentation
- **JSON Schema**: https://json-schema.org/ - Schema validation reference

---

**Questions or issues?** Check the execution manifest for detailed error information, or consult the debugging section above.
