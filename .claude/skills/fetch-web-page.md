# Fetch Web Page

Fetch content from URLs including decklists, card data, and web pages.

## Usage

```bash
# Fetch card data from Scryfall
.claude/skills/web/fetch-page.py --card-name "The Gitrog Monster"

# Fetch decklist from deck builder
.claude/skills/web/fetch-page.py --decklist-url "https://www.moxfield.com/decks/abc123"

# Fetch generic URL
.claude/skills/web/fetch-page.py --url "https://edhrec.com/commanders/gitrog-monster"

# Fetch by Scryfall ID
.claude/skills/web/fetch-page.py --scryfall-id "5790dd89-2be5-4a77-9450-2d3c1422bfc9"
```

## Parameters

- `--url`: Generic URL to fetch
- `--decklist-url`: Fetch decklist from deck builder
- `--card-name`: Fetch card data from Scryfall by name
- `--scryfall-id`: Fetch card data from Scryfall by ID
- `--extract-type`: Content extraction type (text, decklist, json, html)
- `--output-format`: Output format for decklists (txt, json, yaml)

## Output

Returns A2A-compatible JSON with:
- `url`: URL to fetch
- `fetch_type`: Type of fetch (card_data, decklist, generic)
- `platform`: Platform identifier (moxfield, archidekt, scryfall, etc.)
- `extraction_strategy`: Strategy for content extraction

## Supported Platforms

### Deck Builders
- Moxfield (moxfield.com)
- Archidekt (archidekt.com)
- MTGGoldfish (mtggoldfish.com)
- EDHREC (edhrec.com)

### APIs
- Scryfall API (api.scryfall.com)

## Integration

This skill outputs fetch parameters. The actual WebFetch execution is handled by the MCP server when used in workflows.

## Example Workflow Usage

```yaml
steps:
  - name: fetch-card-info
    skill: web/fetch-page
    input:
      card_name: "Gitrog Monster"
    output_var: card_data

  - name: fetch-decklist
    skill: web/fetch-page
    input:
      decklist_url: "https://www.moxfield.com/decks/frog-tribal"
      output_format: "txt"
    output_var: decklist
```

## Scryfall API

Card data fetching uses the Scryfall API:
- By name: `/cards/named?exact={card_name}`
- By ID: `/cards/{scryfall_id}`

Returns structured JSON with card attributes, images, and metadata.
