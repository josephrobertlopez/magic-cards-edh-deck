# Parse Command Skill

**Natural language command → A2A workflow YAML compiler**

## Purpose

Converts natural language commands into executable A2A workflow definitions. Detects user intent, extracts parameters, maps to available skills, and generates valid workflow YAML.

This is a **meta-skill**: It doesn't execute tasks itself - it GENERATES workflows that execute tasks.

## Usage

```bash
.claude/skills/workflows/parse-command.py \
  --command "fetch cards from deck.txt and convert to PDF" \
  --output generated_workflow.yaml \
  --format yaml
```

## Parameters

- `--command` (required): Natural language command describing desired workflow
- `--output` (optional): Save generated workflow to file
- `--format` (optional): Output format - `yaml` (default) or `json`

## Supported Intents

The parser detects these intent keywords:

| Intent | Keywords | Maps to Skills |
|--------|----------|----------------|
| **fetch** | fetch, get, download, retrieve, pull | `data/fetch-from-api` |
| **search** | search, find, query, lookup | `data/search-oracle` |
| **probe** | probe, analyze, discover, inspect | `data/probe-api-schema` |
| **generate** | generate, create, make, build, arrange | `presentation/place-images-in-pptx` |
| **convert** | convert, transform, export, pdf | `pdf/convert-to-pdf` |

## Parameter Extraction

Parser automatically extracts from natural language:

- **File paths**: `deck.txt`, `template.pptx`, `output.pdf`
- **Quoted strings**: `"search query here"` → query parameter
- **API hints**: `Pokemon`, `MTG`, `Magic` → sets API defaults
- **Dimensions**: `2.5 x 3.5 inches` → size hints
- **DPI**: `300 dpi` → print quality
- **Output dirs**: `output: images/` → output_dir parameter

## Examples

### Example 1: Simple Fetch + Generate

**Command**:
```bash
--command "fetch cards from decklists/frog_tribal.txt and generate presentation"
```

**Generated Workflow**:
```yaml
name: auto-generated-workflow
steps:
- name: step1-fetch-resources
  skill: data/fetch-from-api
  input:
    decklist_path: decklists/frog_tribal.txt
    output_dir: images
  output_var: fetch_manifest

- name: step2-generate-presentation
  skill: presentation/place-images-in-pptx
  input:
    manifest_path: ${fetch_manifest.manifest_path}
    template_path: ${input.template_path}
    output_path: output.pptx
  output_var: pptx_output
```

### Example 2: Search → Fetch with Size Hints

**Command**:
```bash
--command "search for MTG card dimensions, then fetch cards from deck.txt at optimal size"
```

**Generated Workflow**:
```yaml
steps:
- name: step1-search-oracle
  skill: data/search-oracle
  input:
    query: "standard card dimensions"  # Extracted from command
    num_results: 5
  output_var: oracle_facts

- name: step2-fetch-resources
  skill: data/fetch-from-api
  input:
    decklist_path: deck.txt
    output_dir: images
    size_hints: ${oracle_facts.facts}  # Chained from oracle!
  output_var: fetch_manifest
```

### Example 3: Full Pipeline (Pokemon)

**Command**:
```bash
--command "fetch Pokemon sprites, generate presentation template.pptx, then convert to PDF for printing"
```

**Generated Workflow**:
```yaml
steps:
- name: step1-fetch-resources
  skill: data/fetch-from-api
  input:
    decklist_path: ${input.decklist_path}
    output_dir: images
    api_url: https://pokeapi.co/api/v2/pokemon/{identifier}  # Auto-detected!
    schema_json: pokeapi  # Auto-detected!
  output_var: fetch_manifest

- name: step2-generate-presentation
  skill: presentation/place-images-in-pptx
  input:
    manifest_path: ${fetch_manifest.manifest_path}
    template_path: template.pptx  # Extracted from command
    output_path: output.pptx
  output_var: pptx_output

- name: step3-convert-to-pdf
  skill: pdf/convert-to-pdf
  input:
    pptx_path: ${pptx_output.output_path}
    output_path: output.pdf
  output_var: pdf_output
```

## Workflow Chaining Logic

The parser intelligently chains steps using output variables:

1. **Search oracle** → outputs `oracle_facts`
   - Next step can use `${oracle_facts.facts}` as size hints

2. **Fetch** → outputs `fetch_manifest`
   - Next step can use `${fetch_manifest.manifest_path}`

3. **Generate presentation** → outputs `pptx_output`
   - Next step can use `${pptx_output.output_path}`

4. **Convert PDF** → outputs `pdf_output`
   - Final output is `${pdf_output}`

## Executing Generated Workflows

```bash
# Step 1: Generate workflow from command
.claude/skills/workflows/parse-command.py \
  --command "fetch cards and convert to PDF" \
  --output my_workflow.yaml

# Step 2: Execute the workflow
python3 a2a_orchestrator/orchestrator.py my_workflow.yaml \
  decklist_path=deck.txt \
  template_path=template.pptx
```

## Advanced: Quoted Queries

Use quotes for explicit search queries:

```bash
--command 'search for "business card dimensions for print" then fetch data'
```

Generated search step will use exact query: `"business card dimensions for print"`

## Skill Registry

The parser knows about these skills:

- `data/fetch-from-api` - Fetch resources from APIs
- `data/probe-api-schema` - Auto-discover API schemas
- `data/search-oracle` - Search for factual information
- `presentation/place-images-in-pptx` - Generate presentations
- `pdf/convert-to-pdf` - Convert to PDF

To add new skills, edit `SKILL_REGISTRY` in `parse-command.py`.

## Integration Patterns

### Pattern 1: One-Shot Workflow Generation

```bash
# Generate + execute in one go
python3 a2a_orchestrator/orchestrator.py \
  "$(.claude/skills/workflows/parse-command.py --command 'fetch and generate' --output /dev/stdout)" \
  decklist_path=deck.txt
```

### Pattern 2: Template Workflows

Save common workflows as templates:

```bash
# Generate template
.claude/skills/workflows/parse-command.py \
  --command "search for dimensions, fetch at optimal size, generate, convert PDF" \
  --output workflows/template-aware-pipeline.yaml

# Reuse template
python3 a2a_orchestrator/orchestrator.py workflows/template-aware-pipeline.yaml \
  decklist_path=different_deck.txt
```

### Pattern 3: Interactive Workflow Builder

```bash
# Prompt user for command
read -p "What workflow do you want? " cmd

# Generate and show
.claude/skills/workflows/parse-command.py --command "$cmd" --output workflow.yaml

# Confirm and execute
read -p "Execute this workflow? (y/n) " confirm
[[ $confirm == "y" ]] && python3 a2a_orchestrator/orchestrator.py workflow.yaml
```

## Limitations

- **Intent ambiguity**: "get cards" could mean fetch OR analyze
  - Mitigation: Be specific - "fetch cards" vs "analyze cards"

- **Parameter extraction**: Relies on regex patterns
  - Mitigation: Use clear file extensions (.txt, .pptx, .pdf)

- **Skill coverage**: Only maps to registered skills
  - Mitigation: Extend SKILL_REGISTRY for new skills

- **No semantic understanding**: Keyword-based, not AI-powered
  - Future: Could use LLM for better intent detection

## Future Enhancements

- [ ] LLM-powered intent classification
- [ ] Multi-language support (Spanish, Japanese commands)
- [ ] Confidence scoring for intent detection
- [ ] Workflow validation before generation
- [ ] Interactive parameter prompting for missing values
- [ ] Learning from user corrections (feedback loop)
