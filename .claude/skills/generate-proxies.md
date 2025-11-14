# generate-proxies

**Composite Skill**: Orchestrates the complete MTG proxy generation pipeline via A2A protocol.

## Description

This skill coordinates three sub-skills using A2A message passing:
1. **fetch-cards**: Extract card data from Scryfall API
2. **generate-presentation**: Transform cards into PPTX layout
3. **convert-to-pdf**: Load final PDF output

Uses the `workflows/proxy-pipeline.yaml` ETL workflow for orchestration.

## Sub-Skills

Located in `.claude/skills/proxy-generation/`:
- `fetch-cards.md` - DataFetcher pattern (EXTRACT)
- `generate-presentation.md` - DocumentGenerator pattern (TRANSFORM)
- `convert-to-pdf.md` - FormatTransformer pattern (LOAD)

## Runtime Dependencies

- Python 3.9+
- All sub-skill dependencies:
  - `pip install requests>=2.31.0 Pillow>=10.0.0 python-pptx>=0.6.21`
  - LibreOffice installed
- A2A orchestrator: `a2a_orchestrator/orchestrator.py`

## Parameters

- `decklist_path` (required): Path to decklist file
- `template_path` (optional): Path to template PPTX (default: `template_2v6h_FIXED.pptx`)
- `--no-pdf` (optional): Skip PDF conversion, PPTX only

## Output

Returns path to final PDF (or PPTX if --no-pdf flag set).

## Usage

```bash
# Full ETL pipeline
/generate-proxies decklists/frog_tribal.txt

# With custom template
/generate-proxies decklists/my_deck.txt template_custom.pptx

# PPTX only (skip PDF)
/generate-proxies decklists/test.txt --no-pdf
```

## A2A Workflow

This skill executes the `workflows/proxy-pipeline.yaml` workflow:

```yaml
steps:
  # EXTRACT: Download card images
  - skill: fetch-cards
    input: {decklist: ${input.decklist_path}}
    output_var: manifest_path
  
  # TRANSFORM: Generate presentation
  - skill: generate-presentation
    input:
      manifest: ${manifest_path}
      template: ${input.template_path}
    output_var: pptx_path
  
  # LOAD: Convert to PDF
  - skill: convert-to-pdf
    input: {source: ${pptx_path}}
    output_var: pdf_path
    condition: ${input.no_pdf} == false
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import os
import asyncio

# Add repo root to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from a2a_orchestrator.orchestrator import load_yaml_workflow, execute_workflow

async def main():
    if len(sys.argv) < 2:
        print("Error: decklist_path required", file=sys.stderr)
        sys.exit(1)
    
    decklist_path = sys.argv[1]
    template_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "template_2v6h_FIXED.pptx"
    no_pdf = '--no-pdf' in sys.argv
    
    # Load workflow
    workflow_path = os.path.join(repo_root, "workflows/proxy-pipeline.yaml")
    workflow = load_yaml_workflow(workflow_path)
    
    # Execute via A2A orchestration
    inputs = {
        "decklist_path": decklist_path,
        "template_path": template_path,
        "no_pdf": no_pdf
    }
    
    try:
        result = await execute_workflow(workflow, inputs)
        
        # Output final result
        if no_pdf:
            print(result['pptx'])
        else:
            print(result['pdf'])
        
        sys.exit(0)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## A2A Message Flow

When you run `/generate-proxies decklists/test.txt`, the orchestrator:

1. **Sends REQUEST** to fetch-cards skill
   ```
   REQUEST {decklist: "decklists/test.txt"}
   ```

2. **Receives RESPONSE** with manifest path
   ```
   RESPONSE {manifest_path: ".claude/state/fetch_manifest.json"}
   ```

3. **Sends DELEGATE** to generate-presentation skill
   ```
   DELEGATE {
     manifest: ".claude/state/fetch_manifest.json",
     template: "template_2v6h_FIXED.pptx"
   }
   ```

4. **Receives RESPONSE** with PPTX path
   ```
   RESPONSE {pptx_path: "outputs/test.pptx"}
   ```

5. **Sends DELEGATE** to convert-to-pdf skill
   ```
   DELEGATE {source: "outputs/test.pptx"}
   ```

6. **Receives RESPONSE** with PDF path
   ```
   RESPONSE {pdf_path: "outputs/test.pdf"}
   ```

7. **Returns** final PDF path to user

## Message Log

All A2A messages are logged to `.claude/state/orchestrator_messages.json` for debugging:

```json
[
  {
    "message_id": "msg_1",
    "message_type": "REQUEST",
    "sender_skill": "orchestrator",
    "recipient_skill": "fetch-cards",
    "payload": {"decklist": "decklists/test.txt"}
  },
  {
    "message_id": "msg_2",
    "message_type": "RESPONSE",
    "sender_skill": "fetch-cards",
    "recipient_skill": "orchestrator",
    "payload": {"manifest_path": ".claude/state/fetch_manifest.json"},
    "parent_message_id": "msg_1"
  }
]
```

## Advantages Over Direct Execution

**vs Running Skills Manually**:
- Single command instead of 3 separate commands
- Automatic data flow (manifest → PPTX → PDF)
- Error handling (halt on failure)
- Message tracing for debugging

**vs Shell Script**:
- Type-safe data passing (not text pipes)
- Declarative workflow (YAML not bash)
- Conditional execution (skip PDF step)
- Reusable sub-skills (use fetch-cards in other workflows)

## Extending the Workflow

You can add validation, optimization, or other steps by editing `workflows/proxy-pipeline.yaml`:

```yaml
steps:
  - skill: fetch-cards
    output_var: manifest_path
  
  # Add validation step
  - skill: validate-manifest
    input: {manifest: ${manifest_path}}
    output_var: validation_result
  
  - skill: generate-presentation
    input: {manifest: ${manifest_path}}
    output_var: pptx_path
    condition: ${validation_result.valid} == true
  
  # Add optimization step
  - skill: optimize-images
    input: {pptx: ${pptx_path}}
    output_var: optimized_pptx
  
  - skill: convert-to-pdf
    input: {source: ${optimized_pptx}}
    output_var: pdf_path
```

## Examples

**Basic 3-card deck**:
```bash
echo "Sol Ring
Command Tower  
Arcane Signet" > decklists/test.txt

/generate-proxies decklists/test.txt
# Output: outputs/test.pdf
```

**75-card EDH deck**:
```bash
/generate-proxies decklists/frog_tribal.txt
# A2A orchestration handles full pipeline
# Message log shows all skill coordination
```

**PPTX only (no PDF)**:
```bash
/generate-proxies decklists/test.txt --no-pdf
# Output: outputs/test.pptx
# convert-to-pdf step skipped via condition
```
