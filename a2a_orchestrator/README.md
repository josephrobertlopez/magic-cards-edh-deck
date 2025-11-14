# A2A Orchestration Layer

Agent-to-Agent (A2A) orchestration system that wraps existing Python modules in reusable skills and coordinates them via YAML workflows.

## Architecture

```
MTG Proxy Generator (Domain-Specific Workflow)
    ↓
YAML Workflow Definition (mtg-proxy-pipeline.yaml)
    ↓
A2A Orchestrator (orchestrator.py)
    ↓
Generic Skills (data/, image/, presentation/, pdf/)
    ↓
Python Modules (data_fetcher.py, document_generator.py, format_transformer.py)
```

## Directory Structure

```
.claude/skills/
├── data/
│   ├── fetch-from-api.md        # Generic API fetching (Scryfall, npm, GitHub, etc.)
│   ├── fetch-web-page.md        # Generic web scraping
│   ├── html-to-markdown.md      # HTML → Markdown conversion
│   └── extract-content.md       # Content extraction (headings, code, links)
├── image/
│   └── manipulate-images.md     # Generic image operations (resize, rotate, crop)
├── presentation/
│   └── place-images-in-pptx.md  # Generic PPTX image layout
├── pdf/
│   └── convert-to-pdf.md        # Generic file → PDF conversion
└── workflows/
    └── mtg-proxy-generation     # MTG-specific workflow executable

workflows/
└── mtg-proxy-pipeline.yaml      # YAML workflow definition

a2a_orchestrator/
├── orchestrator.py              # Workflow orchestrator
└── vendor/
    └── mcp_a2a_server.py        # A2A protocol framework
```

## Usage

### Running MTG Proxy Workflow

```bash
# Basic usage
python3 .claude/skills/workflows/mtg-proxy-generation decklists/frog_tribal.txt

# With custom template
python3 .claude/skills/workflows/mtg-proxy-generation decklists/my_deck.txt template_custom.pptx

# Skip PDF conversion
python3 .claude/skills/workflows/mtg-proxy-generation decklists/test.txt --no-pdf
```

### Running Generic Workflows

```bash
python3 a2a_orchestrator/orchestrator.py workflows/mtg-proxy-pipeline.yaml \
  decklist_path=decklists/test.txt \
  template_path=template.pptx \
  no_pdf=false
```

## A2A Message Flow

Example from MTG proxy generation:

```
Orchestrator → data/fetch-from-api: REQUEST
  message_id: msg_1
  payload: {
    api_config: {base_url: "https://api.scryfall.com", ...},
    items: "decklists/frog_tribal.txt"
  }

data/fetch-from-api → Orchestrator: RESPONSE (simulated)
  message_id: msg_1_response
  payload: {manifest_path: ".claude/state/card_manifest.json"}

Orchestrator → image/manipulate-images: REQUEST
  message_id: msg_2
  payload: {
    operation: "resize",
    images: ${card_manifest.images},
    params: {target_width: 150, ...}
  }

image/manipulate-images → Orchestrator: RESPONSE (simulated)
  message_id: msg_2_response
  payload: {processed_images: [...]}

[... continues through presentation and PDF steps ...]
```

All messages are logged to `.claude/state/<workflow-name>_messages.json`

## YAML Workflow Format

```yaml
name: workflow-name
description: Workflow description

inputs:
  param1:
    type: string
    required: true
    description: Parameter description
  param2:
    type: boolean
    default: false

steps:
  - name: step-name
    skill: category/skill-name  # e.g., data/fetch-from-api
    input:
      param: ${input.param1}    # Variable substitution
      config: {key: "value"}
    output_var: step_output     # Store response in this variable
    condition: ${input.param2} == false  # Optional conditional execution
    on_error: halt               # halt | continue | retry

  - name: next-step
    skill: image/manipulate-images
    input:
      images: ${step_output.images}  # Reference previous step output
    output_var: processed

output:
  result: ${processed}
  metadata: ${step_output}
```

## Variable Substitution

The orchestrator supports `${var.path}` syntax:

- `${input.decklist_path}` - Access workflow input
- `${card_manifest.images}` - Access previous step output
- `outputs/${input.decklist_path}.pptx` - Embedded substitution

Substitution is recursive and works in:
- Strings (full or embedded)
- Dictionaries (all values)
- Lists (all items)

## Skill Interface

Each skill defines its A2A interface in markdown:

```markdown
## A2A Interface

**REQUEST Message**:
```json
{
  "param1": "value",
  "param2": {...}
}
```

**RESPONSE Message**:
```json
{
  "output_path": "result.txt",
  "metadata": {...}
}
```
```

## Domain-Agnostic Design

Skills are designed to work across domains:

**Photo Album Workflow** (same skills, different domain):
```yaml
steps:
  - skill: data/fetch-from-api
    input: {api_config: {Flickr API}, items: "photo_ids.txt"}
  - skill: image/manipulate-images
    input: {operation: "resize", images: [...]}
  - skill: presentation/place-images-in-pptx
    input: {template: "album_template.pptx", images: [...]}
  - skill: pdf/convert-to-pdf
    input: {source: "album.pptx"}
```

**Code Documentation Workflow**:
```yaml
steps:
  - skill: data/fetch-from-api
    input: {api_config: {GitHub API}, items: "code_files.txt"}
  - skill: image/manipulate-images
    input: {operation: "crop", images: [...]}  # Crop screenshots
  - skill: presentation/place-images-in-pptx
    input: {template: "code_template.pptx", images: [...]}
  - skill: pdf/convert-to-pdf
    input: {source: "docs.pptx"}
```

## Implementation Status

### ✅ Complete
- YAML workflow parser
- A2A message creation and logging
- Variable substitution (recursive, embedded)
- Conditional execution
- Message logging to state directory
- MTG proxy workflow definition
- Web content skills (fetch, html-to-md, extract)

### 🚧 Simulated (Not Yet Implemented)
- Skill execution (currently returns mock responses)
- Actual A2A message passing between skills
- Python Skill wrappers for existing modules
- Error handling and retries
- Parallel step execution

## Next Steps

1. **Create Skill Wrappers**: Wrap existing modules in Python `Skill` subclasses
2. **Implement Message Routing**: Connect orchestrator to actual skills via A2A messages
3. **Add Error Handling**: Implement retry logic and error propagation
4. **Parallel Execution**: Support concurrent step execution where dependencies allow
5. **Real Workflow Testing**: Run end-to-end with actual skill implementations
