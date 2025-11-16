---
name: "html/extract-css"
description: "Extract data from HTML documents using CSS selectors"
version: "1.0.0"
supports_batch: false

inputs:
  - name: html_content
    type: string
    required: true
    description: "Raw HTML content or file path (if starts with / treated as file)"

  - name: selector
    type: string
    required: true
    description: "CSS selector (e.g., '.card-name', '#content', 'a[href*=scryfall]')"

  - name: extract_type
    type: string
    required: false
    default: "text"
    description: "Extraction mode: 'text' | 'attribute' | 'html'"

  - name: attribute_name
    type: string
    required: false
    default: null
    description: "Attribute to extract (required if extract_type='attribute')"

  - name: default_value
    type: any
    required: false
    default: []
    description: "Return value if no matches found"

outputs:
  - name: items
    type: list
    description: "Extracted values (strings) - empty list if no matches"

  - name: count
    type: integer
    description: "Number of matches found"
---

# html/extract-css

Extract structured data from HTML documents using CSS selectors.

## Purpose

This skill provides domain-agnostic HTML data extraction using CSS selectors. It works with any HTML structure including decklists, product catalogs, data tables, navigation menus, and article content.

## Implementation

### Prerequisites

- Python 3.9+
- beautifulsoup4 library
- lxml parser

### Algorithm

1. **Parse HTML**: Use BeautifulSoup with lxml parser for robust HTML parsing
2. **Select Elements**: Apply CSS selector to find matching elements
3. **Extract Data**: Based on extract_type:
   - `text`: Extract `.get_text(strip=True)` from each element
   - `attribute`: Extract specified attribute value from each element
   - `html`: Extract `.decode_contents()` or `str(element)` for full HTML
4. **Handle Empty**: Return `default_value` if no matches found
5. **Return Results**: Return `{items: [...], count: N}`

### Error Handling

- **Invalid selector**: Catch selector exceptions, return default_value
- **Malformed HTML**: lxml parser handles gracefully (auto-corrects)
- **No matches**: Return `{items: default_value, count: 0}` (success, not error)
- **File not found**: Raise FILE_NOT_FOUND error
- **Missing attribute**: Return empty string for that element (do not skip)

### Pseudo-code

```python
from bs4 import BeautifulSoup

def execute_html_extract_css(args):
    html_content = args["html_content"]
    selector = args["selector"]
    extract_type = args.get("extract_type", "text")
    attribute_name = args.get("attribute_name")
    default_value = args.get("default_value", [])

    # Load HTML (from string or file)
    if html_content.startswith("/"):
        with open(html_content, 'r') as f:
            html_content = f.read()

    # Parse HTML
    soup = BeautifulSoup(html_content, 'lxml')

    # Find elements
    try:
        elements = soup.select(selector)
    except Exception:
        return {"items": default_value, "count": 0, "error": "INVALID_SELECTOR"}

    # Extract data
    items = []
    for element in elements:
        if extract_type == "text":
            items.append(element.get_text(strip=True))
        elif extract_type == "attribute":
            items.append(element.get(attribute_name, ""))
        elif extract_type == "html":
            items.append(str(element))

    # Return results
    if not items:
        items = default_value

    return {
        "items": items,
        "count": len(items)
    }
```

## Usage Examples

### Example 1: Extract Text Content

```yaml
- name: extract_names
  skill: html/extract-css
  args:
    html_content: "<div class='item'>Item 1</div><div class='item'>Item 2</div>"
    selector: ".item"
    extract_type: "text"
  outputs:
    names: "{{result.items}}"
```

### Example 2: Extract Link URLs

```yaml
- name: extract_links
  skill: html/extract-css
  args:
    html_content: "{{steps.fetch_page.outputs.html}}"
    selector: "a.external-link"
    extract_type: "attribute"
    attribute_name: "href"
  outputs:
    urls: "{{result.items}}"
```

### Example 3: Extract Full HTML Blocks

```yaml
- name: extract_articles
  skill: html/extract-css
  args:
    html_content: "/path/to/page.html"
    selector: "article.post"
    extract_type: "html"
  outputs:
    articles: "{{result.items}}"
```

## Domain-Agnostic Design

This skill contains **zero domain-specific logic**. It works equally well for:

- E-commerce: Product titles, prices, images
- Content sites: Article headings, author names, timestamps
- Data tables: Cell values, row data
- Navigation: Menu links, breadcrumbs
- Forms: Input values, labels

The skill accepts any CSS selector and extracts any data structure defined by the workflow configuration.
