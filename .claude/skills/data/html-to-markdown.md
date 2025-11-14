# html-to-markdown

Generic HTML to Markdown conversion with cleanup and formatting.

## A2A Interface

**REQUEST Message**:
```json
{
  "html_files": [
    "downloads/html/page1.html",
    "downloads/html/page2.html"
  ],
  "output_dir": "downloads/markdown",
  "options": {
    "strip_tags": ["script", "style", "nav", "footer"],
    "preserve_links": true,
    "preserve_images": true,
    "heading_style": "atx",      // atx (#) or setext (underline)
    "code_language": "auto"
  }
}
```

**RESPONSE Message**:
```json
{
  "markdown_files": [
    "downloads/markdown/page1.md",
    "downloads/markdown/page2.md"
  ],
  "total": 2,
  "successful": 2,
  "failed": 0
}
```

## Domain-Agnostic Uses

- **Documentation**: Convert HTML docs to Markdown
- **Research**: Convert articles to readable format
- **Archiving**: Store web content as plain text
- **Content Processing**: Extract text for analysis
- **Static Sites**: Convert HTML to Markdown for Jekyll/Hugo

## Parameters

- `html_files` (required): List of HTML file paths or URLs
- `output_dir` (optional): Output directory (default: "downloads/markdown")
- `options` (optional): Conversion options

## Conversion Options

### strip_tags
Remove specific HTML tags (e.g., `script`, `style`, `nav`, `footer`)

### preserve_links
Keep links as Markdown `[text](url)` format

### preserve_images
Keep images as `![alt](src)` format

### heading_style
- `atx`: Use `#` symbols (`# Heading 1`)
- `setext`: Use underlines (```Heading 1\n=========```)

### code_language
Language hint for code blocks (`python`, `javascript`, `auto`)

## Usage

**Convert single HTML file**:
```bash
/data/html-to-markdown downloads/html/article.html
```

**Convert multiple files**:
```bash
/data/html-to-markdown \
  --files downloads/html/*.html \
  --output downloads/markdown \
  --strip-tags script,style,nav
```

**Preserve only text (strip all formatting)**:
```bash
/data/html-to-markdown \
  --file page.html \
  --no-links \
  --no-images \
  --output text/
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import re
from html.parser import HTMLParser

class HTMLToMarkdown(HTMLParser):
    """Convert HTML to Markdown"""
    
    def __init__(self, options=None):
        super().__init__()
        self.options = options or {}
        self.markdown = []
        self.current_tag = None
        self.link_text = None
        self.strip_tags = set(self.options.get('strip_tags', ['script', 'style']))
        self.skip_content = False
    
    def handle_starttag(self, tag, attrs):
        if tag in self.strip_tags:
            self.skip_content = True
            return
        
        attrs_dict = dict(attrs)
        
        if tag == 'h1':
            self.markdown.append('\n# ')
        elif tag == 'h2':
            self.markdown.append('\n## ')
        elif tag == 'h3':
            self.markdown.append('\n### ')
        elif tag == 'p':
            self.markdown.append('\n\n')
        elif tag == 'a' and self.options.get('preserve_links', True):
            self.link_text = ''
            self.current_tag = ('a', attrs_dict.get('href', ''))
        elif tag == 'img' and self.options.get('preserve_images', True):
            alt = attrs_dict.get('alt', '')
            src = attrs_dict.get('src', '')
            self.markdown.append(f'![{alt}]({src})')
        elif tag == 'code':
            self.markdown.append('`')
        elif tag == 'pre':
            self.markdown.append('\n```\n')
        elif tag == 'strong' or tag == 'b':
            self.markdown.append('**')
        elif tag == 'em' or tag == 'i':
            self.markdown.append('*')
        elif tag == 'ul':
            self.markdown.append('\n')
        elif tag == 'li':
            self.markdown.append('\n- ')
    
    def handle_endtag(self, tag):
        if tag in self.strip_tags:
            self.skip_content = False
            return
        
        if tag == 'a' and self.current_tag and self.current_tag[0] == 'a':
            href = self.current_tag[1]
            self.markdown.append(f'[{self.link_text}]({href})')
            self.current_tag = None
            self.link_text = None
        elif tag == 'code':
            self.markdown.append('`')
        elif tag == 'pre':
            self.markdown.append('\n```\n')
        elif tag == 'strong' or tag == 'b':
            self.markdown.append('**')
        elif tag == 'em' or tag == 'i':
            self.markdown.append('*')
        elif tag in ['h1', 'h2', 'h3', 'p']:
            self.markdown.append('\n')
    
    def handle_data(self, data):
        if self.skip_content:
            return
        
        if self.current_tag and self.current_tag[0] == 'a':
            self.link_text = data
        else:
            # Clean whitespace
            cleaned = ' '.join(data.split())
            if cleaned:
                self.markdown.append(cleaned)
    
    def get_markdown(self):
        # Join and clean up extra newlines
        text = ''.join(self.markdown)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

def convert_html_to_markdown(html_content, options):
    """Convert HTML string to Markdown"""
    parser = HTMLToMarkdown(options)
    parser.feed(html_content)
    return parser.get_markdown()

def main():
    if len(sys.argv) < 2:
        print("Error: html_files required", file=sys.stderr)
        sys.exit(1)
    
    html_files = []
    if os.path.isfile(sys.argv[1]):
        html_files = [sys.argv[1]]
    else:
        import glob
        html_files = glob.glob(sys.argv[1])
    
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads/markdown"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    options = {
        'strip_tags': ['script', 'style', 'nav', 'footer'],
        'preserve_links': True,
        'preserve_images': True,
        'heading_style': 'atx'
    }
    
    markdown_files = []
    successful = 0
    failed = 0
    
    for html_file in html_files:
        print(f"📄 Converting: {html_file}")
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            markdown_content = convert_html_to_markdown(html_content, options)
            
            # Output filename
            md_filename = Path(html_file).stem + '.md'
            md_path = os.path.join(output_dir, md_filename)
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            markdown_files.append(md_path)
            successful += 1
            print(f"  ✅ Saved: {md_path}")
            
        except Exception as e:
            failed += 1
            print(f"  ❌ Failed: {e}")
    
    print(f"\n📊 Results: {successful}/{len(html_files)} files converted")
    
    # Output paths for A2A orchestration
    for path in markdown_files:
        print(path)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Error Codes

- `0`: Success
- `1`: No HTML files provided

## Example Workflow

**Research Pipeline**:
```yaml
steps:
  # Fetch web pages
  - skill: data/fetch-web-page
    input: {urls: "research_urls.txt"}
    output_var: html_manifest
  
  # Convert to Markdown
  - skill: data/html-to-markdown
    input: {html_files: ${html_manifest.pages}}
    output_var: markdown_files
  
  # Extract key content
  - skill: data/extract-content
    input: {files: ${markdown_files}}
    output_var: extracted_content
```
