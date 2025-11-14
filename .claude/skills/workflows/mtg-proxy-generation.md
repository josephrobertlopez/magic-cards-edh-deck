# mtg-proxy-generation

**Domain-Specific Workflow**: MTG card proxy generation using generic A2A skills.

## Description

Composes 4 generic skills to create Magic card proxies:
1. **data/fetch-from-api** - Fetch cards from Scryfall API (EXTRACT)
2. **image/manipulate-images** - Resize/rotate card images (TRANSFORM)
3. **presentation/place-images-in-pptx** - Layout cards in template (TRANSFORM)
4. **pdf/convert-to-pdf** - Export to print-ready PDF (LOAD)

## A2A Workflow

Uses `workflows/mtg-proxy-pipeline.yaml`:

```yaml
name: mtg-proxy-generation
description: Generate MTG card proxies from decklist

steps:
  # EXTRACT: Fetch card images from Scryfall
  - skill: data/fetch-from-api
    input:
      api_config:
        base_url: "https://api.scryfall.com"
        endpoint: "/cards/named"
        query_param: "fuzzy"
        rate_limit: 10
      items: ${input.decklist_path}
      output_dir: "images"
      cache: true
    output_var: card_manifest

  # TRANSFORM 1: Resize/rotate images for PPTX slots
  - skill: image/manipulate-images
    input:
      operation: "resize"
      images: ${card_manifest.images}
      params:
        target_width: 150
        preserve_aspect: true
        auto_rotate: true
      output_dir: "processed"
    output_var: processed_images

  # TRANSFORM 2: Place images in PPTX template
  - skill: presentation/place-images-in-pptx
    input:
      template_path: ${input.template_path}
      image_manifest: ${processed_images}
      output_path: "outputs/${basename(input.decklist_path)}.pptx"
      layout_config:
        min_slot_size: 1.0
        aspect_fit: true
        auto_rotate: true
        background_color: "white"
    output_var: pptx_path

  # LOAD: Convert to PDF
  - skill: pdf/convert-to-pdf
    input:
      source_path: ${pptx_path}
      output_dir: "outputs"
    output_var: pdf_path
    condition: ${input.no_pdf} == false

output:
  pptx: ${pptx_path}
  pdf: ${pdf_path}
  manifest: ${card_manifest}
```

## Parameters

- `decklist_path` (required): Path to MTG decklist file
- `template_path` (optional): Template PPTX (default: `template_2v6h_FIXED.pptx`)
- `--no-pdf` (optional): Skip PDF conversion

## Usage

```bash
/workflows/mtg-proxy-generation decklists/frog_tribal.txt
/workflows/mtg-proxy-generation decklists/my_deck.txt template_custom.pptx
/workflows/mtg-proxy-generation decklists/test.txt --no-pdf
```

## A2A Message Flow

```
Orchestrator → data/fetch-from-api: REQUEST
  {api_config: {Scryfall config}, items: "decklists/test.txt"}
  
data/fetch-from-api → Orchestrator: RESPONSE
  {card_manifest: {images: ["images/Sol_Ring.jpg", ...]}}

Orchestrator → image/manipulate-images: DELEGATE
  {operation: "resize", images: [...], params: {resize config}}
  
image/manipulate-images → Orchestrator: RESPONSE
  {processed_images: ["processed/Sol_Ring.jpg", ...]}

Orchestrator → presentation/place-images-in-pptx: DELEGATE
  {template: "template.pptx", images: [...], layout_config: {...}}
  
place-images-in-pptx → Orchestrator: RESPONSE
  {pptx_path: "outputs/test.pptx"}

Orchestrator → pdf/convert-to-pdf: DELEGATE
  {source: "outputs/test.pptx"}
  
convert-to-pdf → Orchestrator: RESPONSE
  {pdf_path: "outputs/test.pdf"}
```

## Why This Is Better

### vs MTG-Specific Skills

**Old** (domain-specific):
```
fetch-cards.md           # Only works for MTG cards
generate-presentation.md # Only works for MTG layout
convert-to-pdf.md        # Generic (good!)
```

**New** (domain-agnostic):
```
data/fetch-from-api.md              # Works for ANY API (Scryfall, GitHub, npm)
image/manipulate-images.md          # Works for ANY images (cards, screenshots, photos)
presentation/place-images-in-pptx.md # Works for ANY image layout (cards, photos, charts)
pdf/convert-to-pdf.md               # Already generic

workflows/mtg-proxy-generation.md   # MTG-specific composition of generic skills
```

### Reusable for Other Domains

**Photo Album Workflow**:
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

**Code Screenshot Documentation**:
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

**Product Catalog**:
```yaml
steps:
  - skill: data/fetch-from-api
    input: {api_config: {Shopify API}, items: "products.txt"}
  - skill: image/manipulate-images
    input: {operation: "fit", images: [...]}  # Fit product images
  - skill: presentation/place-images-in-pptx
    input: {template: "catalog_template.pptx", images: [...]}
  - skill: pdf/convert-to-pdf
    input: {source: "catalog.pptx"}
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import os
import asyncio

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from a2a_orchestrator.orchestrator import load_yaml_workflow, execute_workflow

async def main():
    if len(sys.argv) < 2:
        print("Error: decklist_path required", file=sys.stderr)
        sys.exit(1)
    
    decklist_path = sys.argv[1]
    template_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "template_2v6h_FIXED.pptx"
    no_pdf = '--no-pdf' in sys.argv
    
    workflow = load_yaml_workflow("workflows/mtg-proxy-pipeline.yaml")
    
    result = await execute_workflow(workflow, {
        "decklist_path": decklist_path,
        "template_path": template_path,
        "no_pdf": no_pdf
    })
    
    print(result['pdf'] if not no_pdf else result['pptx'])
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
```
