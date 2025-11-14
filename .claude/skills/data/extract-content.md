# extract-content

Generic content extraction from text/markdown files using patterns or selectors.

## A2A Interface

**REQUEST Message**:
```json
{
  "files": [
    "downloads/markdown/article1.md",
    "downloads/markdown/article2.md"
  ],
  "extraction_rules": {
    "type": "sections",     // sections | headings | code_blocks | links | paragraphs
    "pattern": "## (.+)",   // regex pattern (optional)
    "min_length": 100       // minimum content length (optional)
  },
  "output_format": "json",  // json | markdown | text
  "output_path": "extracted/content.json"
}
```

**RESPONSE Message**:
```json
{
  "output_path": "extracted/content.json",
  "total_files": 2,
  "total_items_extracted": 15,
  "extraction_summary": {
    "headings": 8,
    "paragraphs": 5,
    "code_blocks": 2
  }
}
```

## Domain-Agnostic Uses

- **Research**: Extract key sections from articles
- **Documentation**: Extract code examples from docs
- **Content Analysis**: Extract headings/structure
- **Link Aggregation**: Extract all links from pages
- **Data Mining**: Extract structured data from text

## Extraction Types

### sections
Extract content by section (between headings)

### headings
Extract all headings (H1, H2, H3, etc.)

### code_blocks
Extract code examples from markdown code fences

### links
Extract all URLs and link text

### paragraphs
Extract paragraphs matching criteria (length, keywords)

### custom
Use regex pattern to extract specific content

## Parameters

- `files` (required): List of text/markdown files
- `extraction_rules` (required): Extraction configuration
- `output_format` (optional): Output format (json, markdown, text)
- `output_path` (optional): Output file path

## Usage

**Extract headings**:
```bash
/data/extract-content \
  --files downloads/markdown/*.md \
  --type headings \
  --output headings.json
```

**Extract code blocks**:
```bash
/data/extract-content \
  --files docs/*.md \
  --type code_blocks \
  --output code_examples.md
```

**Extract sections matching pattern**:
```bash
/data/extract-content \
  --files research/*.md \
  --type sections \
  --pattern "## Methods" \
  --output methods.txt
```

**Extract links**:
```bash
/data/extract-content \
  --files articles/*.md \
  --type links \
  --output links.json
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import os
import re
import json
from pathlib import Path

def extract_headings(content):
    """Extract all markdown headings"""
    pattern = r'^(#{1,6})\s+(.+)$'
    matches = re.findall(pattern, content, re.MULTILINE)
    return [{'level': len(m[0]), 'text': m[1]} for m in matches]

def extract_code_blocks(content):
    """Extract code blocks from markdown"""
    pattern = r'```(\w+)?\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    return [{'language': m[0] or 'text', 'code': m[1]} for m in matches]

def extract_links(content):
    """Extract markdown links"""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)
    return [{'text': m[0], 'url': m[1]} for m in matches]

def extract_sections(content, heading_pattern=None):
    """Extract content by sections"""
    sections = []
    lines = content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        if re.match(r'^#{1,6}\s+', line):
            if current_section:
                sections.append({
                    'heading': current_section,
                    'content': '\n'.join(current_content).strip()
                })
            current_section = line.strip('# ').strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_section:
        sections.append({
            'heading': current_section,
            'content': '\n'.join(current_content).strip()
        })
    
    # Filter by pattern if provided
    if heading_pattern:
        pattern = re.compile(heading_pattern)
        sections = [s for s in sections if pattern.search(s['heading'])]
    
    return sections

def extract_paragraphs(content, min_length=0):
    """Extract paragraphs"""
    paragraphs = content.split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) >= min_length]
    return [{'text': p} for p in paragraphs]

def main():
    if len(sys.argv) < 2:
        print("Error: files required", file=sys.stderr)
        sys.exit(1)
    
    import glob
    files = glob.glob(sys.argv[1])
    extraction_type = sys.argv[2] if len(sys.argv) > 2 else 'headings'
    output_path = sys.argv[3] if len(sys.argv) > 3 else 'extracted/content.json'
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    all_extracted = []
    
    for file_path in files:
        print(f"📄 Extracting from: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if extraction_type == 'headings':
            extracted = extract_headings(content)
        elif extraction_type == 'code_blocks':
            extracted = extract_code_blocks(content)
        elif extraction_type == 'links':
            extracted = extract_links(content)
        elif extraction_type == 'sections':
            extracted = extract_sections(content)
        elif extraction_type == 'paragraphs':
            extracted = extract_paragraphs(content)
        else:
            extracted = []
        
        all_extracted.append({
            'file': file_path,
            'items': extracted
        })
        
        print(f"  ✅ Extracted {len(extracted)} items")
    
    # Save output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_extracted, f, indent=2)
    
    total_items = sum(len(e['items']) for e in all_extracted)
    print(f"\n📊 Results: {total_items} total items extracted from {len(files)} files")
    print(output_path)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Error Codes

- `0`: Success
- `1`: No files provided

## Example Workflows

**Research Pipeline**:
```yaml
steps:
  - skill: data/fetch-web-page
    input: {urls: "research_urls.txt"}
    output_var: html_pages
  
  - skill: data/html-to-markdown
    input: {html_files: ${html_pages}}
    output_var: markdown_files
  
  - skill: data/extract-content
    input:
      files: ${markdown_files}
      extraction_rules: {type: "sections", pattern: "## (?:Methods|Results)"}
    output_var: extracted_sections
```

**Documentation Scraper**:
```yaml
steps:
  - skill: data/fetch-web-page
    input: {urls: "https://docs.python.org/3/library/"}
    output_var: docs_html
  
  - skill: data/html-to-markdown
    input: {html_files: ${docs_html}}
    output_var: docs_md
  
  - skill: data/extract-content
    input:
      files: ${docs_md}
      extraction_rules: {type: "code_blocks"}
    output_var: code_examples
```
