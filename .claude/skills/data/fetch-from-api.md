# fetch-from-api

Generic API data fetching with rate limiting, caching, and retry logic.

## A2A Interface

**REQUEST Message**:
```json
{
  "api_config": {
    "base_url": "https://api.scryfall.com",
    "endpoint": "/cards/named",
    "query_param": "fuzzy",
    "rate_limit": 10  // requests per second
  },
  "items": ["item1", "item2", "item3"],
  "output_dir": "downloads",
  "cache": true
}
```

**RESPONSE Message**:
```json
{
  "manifest_path": ".claude/state/fetch_manifest.json",
  "total": 3,
  "successful": 3,
  "failed": 0
}
```

## Domain-Agnostic Uses

- **MTG Cards**: Fetch from Scryfall API
- **NPM Packages**: Fetch from npm registry
- **GitHub Issues**: Fetch from GitHub API
- **Stock Data**: Fetch from financial APIs
- **Weather Data**: Fetch from weather APIs

## Parameters

- `api_config` (required): API configuration (base URL, endpoint, rate limit)
- `items` (required): List of items to fetch
- `output_dir` (optional): Download directory (default: "downloads")
- `cache` (optional): Use cached results (default: true)

## CLI Usage

**Standalone Invocation** (User Story 1):
```bash
python3 .claude/skills/data/fetch-from-api.py \
  --decklist decklists/my_deck.txt \
  --output-dir images \
  --manifest .claude/state/my_deck_manifest.json
```

**Parameters**:
- `--decklist` (required): Path to decklist file (one item per line)
- `--output-dir` (required): Directory to save downloaded resources
- `--manifest` (optional): Path to output manifest JSON (default: `.claude/state/<decklist>_manifest.json`)

**Success Output** (JSON to stdout):
```json
{
  "status": "success",
  "manifest_path": ".claude/state/my_deck_manifest.json",
  "output_dir": "images",
  "decklist": "decklists/my_deck.txt"
}
```

**Error Output** (JSON to stderr):
```json
{
  "status": "error",
  "error": "Decklist file not found: decklists/missing.txt",
  "exit_code": 1,
  "context": {"decklist": "decklists/missing.txt"}
}
```

**Exit Codes**:
- `0`: Success
- `1`: Resource/file not found
- `3`: Network/API failure

## Implementation

Wraps `magic_cards.data_fetcher.fetch_resources_from_list()` module but can be extended for other APIs.

**Runtime Dependencies**:
- Python 3.9+
- `pip install requests Pillow`
