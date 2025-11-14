# extract-content-from-html

Generic HTML content extractor using CSS selectors.

## Purpose

Extract structured data from HTML without domain-specific parsers. Works for ANY site: MTG decklists, Pokemon teams, recipes, product lists, etc.

## Why Generic?

**Problem**: Modern deck sites (Moxfield, Archidekt, MTGDecks.net) use JavaScript SPAs and block automated scraping.

**Solution**: User provides HTML + CSS selector → We extract content. Domain-agnostic protocol.

## Usage

```bash
# Extract MTG decklist
python3 .claude/skills/data/extract-content-from-html.py \
  --content-file deck.html \
  --extract-type list \
  --selector ".card-item" \
  --output decklist.txt

# Extract Pokemon team
python3 .claude/skills/data/extract-content-from-html.py \
  --content-file pokemon.html \
  --extract-type list \
  --selector "li.pokemon-name"

# Extract recipe table
python3 .claude/skills/data/extract-content-from-html.py \
  --content-file recipe.html \
  --extract-type table \
  --selector "table.ingredients"
```

## Extract Types

1. **list**: Extract text from matching elements → newline-separated output
2. **table**: Extract table rows → CSV or dict format
3. **article**: Extract long-form content → plain text

## Workflows

### Manual Paste (Recommended for JS sites)

```bash
# 1. Browser: Right-click deck list → Copy outerHTML
# 2. Save to file:
cat > /tmp/deck.html
# (paste HTML, Ctrl+D)

# 3. Extract:
python3 .claude/skills/data/extract-content-from-html.py \
  --content-file /tmp/deck.html \
  --extract-type list \
  --selector ".card-row"
```

### Programmatic Fetch (For static sites)

```bash
# 1. Fetch HTML
python3 .claude/skills/web/fetch-content.py \
  --url "https://example.com/deck" \
  --output /tmp/page.html

# 2. Extract
python3 .claude/skills/data/extract-content-from-html.py \
  --content-file /tmp/page.html \
  --extract-type list \
  --selector ".card-name"
```

## Finding CSS Selectors

**Browser DevTools Method:**
1. Press F12 → Elements tab
2. Click element inspector (top-left arrow icon)
3. Hover over card in list
4. Note the class name (e.g., `class="card-item"`)
5. Selector: `.card-item`

**Common Patterns:**
- `.card-item` → Elements with class "card-item"
- `li.card` → `<li>` tags with class "card"
- `table.deck tbody tr` → Table rows
- `div[data-card]` → Divs with data-card attribute

## A2A JSON Output

```json
{
  "status": "success",
  "extract_type": "list",
  "selector": ".card-item",
  "result": {
    "type": "list",
    "items": ["Forest", "Island", "The Gitrog Monster"],
    "count": 3
  },
  "output_file": "/tmp/decklist.txt"
}
```

## Dependencies

- beautifulsoup4 >= 4.12.0
- lxml >= 4.9.0 (faster HTML parsing)

## Protocol-First Design

This skill is **domain-agnostic**:
- No MTG-specific logic
- No Pokemon-specific logic
- No hardcoded site URLs

**User provides:**
- HTML content (file or stdin)
- CSS selector (what to extract)
- Extract type (list/table/article)

**Skill provides:**
- Clean extracted data
- A2A JSON output
- Multiple output formats

## Test Coverage

**Unit tests**: `tests/unit/test_extract_html.py` (6 tests)
- MTG decklist extraction
- Pokemon list extraction
- Recipe table extraction
- Output file generation
- Error handling

**Integration tests**: `tests/integration/test_html_to_decklist_workflow.py` (2 tests)
- Manual paste workflow
- Programmatic fetch → extract pipeline

All tests passing ✅
