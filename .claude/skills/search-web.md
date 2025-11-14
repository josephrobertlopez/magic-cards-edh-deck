# Search Web

Search for Magic card information, decklists, and strategies online.

## Usage

```bash
# Search for specific card
.claude/skills/web/search-query.py --card-name "Gitrog Monster"

# Search for deck archetype
.claude/skills/web/search-query.py --deck-archetype "Frog Tribal"

# Search for commander decklists
.claude/skills/web/search-query.py --commander "Tatsunari"

# Generic web search
.claude/skills/web/search-query.py --query "best edh commanders 2024"
```

## Parameters

- `--card-name`: Search for specific card (MTG-optimized)
- `--deck-archetype`: Search for deck archetype
- `--commander`: Search for commander decklists
- `--query`: Generic web search query
- `--max-results`: Maximum results to return (default: 5)
- `--allowed-domains`: Restrict to specific domains
- `--blocked-domains`: Exclude specific domains

## Output

Returns A2A-compatible JSON with:
- `query`: Optimized search query
- `search_type`: Type of search (mtg_cards, web)
- `allowed_domains`: List of prioritized domains
- `max_results`: Number of results requested

## Domain Prioritization

MTG searches prioritize:
- scryfall.com
- edhrec.com
- mtggoldfish.com
- archidekt.com
- moxfield.com
- commanderspellbook.com

## Integration

This skill outputs search parameters. The actual WebSearch execution is handled by the MCP server when used in workflows.

## Example Workflow Usage

```yaml
steps:
  - name: search-decklist
    skill: web/search-query
    input:
      deck_archetype: "Frog Tribal"
    output_var: search_params
```
