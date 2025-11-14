# Decklists Directory

This directory is for **generated** decklists, not static files.

## How to Generate

Use workflows to fetch decklists from live sources:

```bash
# Fetch commander deck from EDHREC
python3 a2a_orchestrator/orchestrator.py \
  workflows/commander_to_proxies.yaml \
  commander_name=krenko-mob-boss

# Generates: decklists/krenko-mob-boss_extracted.txt
```

## Examples

- `commander_to_proxies.yaml` - Fetches from EDHREC
- `search_and_extract_decklist.yaml` - Fetches from Google search
- `extract_decklist_from_url.yaml` - Extracts from any URL

All decklists are **regenerable** - no need to commit them!
