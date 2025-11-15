# fetch-card-data

Atomic skill: Fetch card metadata from Scryfall API without downloading images.

## A2A Interface

**REQUEST Message**:
```json
{
  "card_names": [
    "Black Lotus",
    "Mox Sapphire",
    "Time Walk"
  ],
  "options": {
    "fuzzy_match": true,
    "include_prices": true,
    "timeout": 10
  }
}
```

**RESPONSE Message**:
```json
{
  "cards": [
    {
      "name": "Black Lotus",
      "scryfall_id": "bd8fa327-dd41-4737-8f19-2cf5eb1f7cdd",
      "mana_cost": "{0}",
      "type_line": "Artifact",
      "oracle_text": "{T}, Sacrifice Black Lotus: Add three mana of any one color.",
      "image_uris": {
        "small": "https://cards.scryfall.io/small/...",
        "normal": "https://cards.scryfall.io/normal/...",
        "large": "https://cards.scryfall.io/large/..."
      },
      "prices": {
        "usd": "120000.00",
        "usd_foil": null
      },
      "status": "success"
    }
  ],
  "total": 3,
  "successful": 3,
  "failed": 0,
  "errors": []
}
```

## Contract

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "card_names": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1
    },
    "options": {
      "type": "object",
      "properties": {
        "fuzzy_match": {"type": "boolean", "default": true},
        "include_prices": {"type": "boolean", "default": false},
        "timeout": {"type": "integer", "default": 10}
      }
    }
  },
  "required": ["card_names"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "cards": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "scryfall_id": {"type": "string"},
          "image_uris": {"type": "object"},
          "status": {"type": "string", "enum": ["success", "failed"]}
        }
      }
    },
    "total": {"type": "integer"},
    "successful": {"type": "integer"},
    "failed": {"type": "integer"},
    "errors": {"type": "array"}
  },
  "required": ["cards", "total", "successful", "failed"]
}
```

## Single Responsibility

**Does**: Fetch card metadata (name, ID, text, image URLs, prices) from Scryfall API
**Does NOT**: Download images, generate slides, create PPTX files, resize images

## Batch Processing Support

✅ **Batch-compatible**: This skill can process multiple cards in a single invocation via `card_names` array parameter.

## Domain-Agnostic Uses

- **Card Price Tracking**: Fetch current market prices for collection valuation
- **Deck Analysis**: Get card statistics (CMC, type distribution, colors)
- **Format Legality Checker**: Validate deck legality via card metadata
- **Oracle Text Search**: Find cards with specific rules text
- **Art Collector**: Catalog art variations via image_uris without downloading

## Parameters

- `card_names` (required): Array of card names to fetch
- `options.fuzzy_match` (optional, default: true): Use fuzzy matching for misspellings
- `options.include_prices` (optional, default: false): Include current market prices
- `options.timeout` (optional, default: 10): Per-request timeout in seconds

## Usage

**Fetch single card**:
```bash
/data/fetch-card-data "Black Lotus"
```

**Fetch multiple cards**:
```bash
/data/fetch-card-data \
  --cards "Black Lotus,Mox Sapphire,Time Walk" \
  --include-prices
```

**Fetch from decklist file**:
```bash
/data/fetch-card-data --cards-file decklists/commander.txt
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import json
import requests
import urllib.parse
from typing import List, Dict, Any

def fetch_card_data(card_name: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch card metadata from Scryfall API.

    Args:
        card_name: Name of the card to fetch
        options: Request options (fuzzy_match, include_prices, timeout)

    Returns:
        Card metadata dict with status field
    """
    fuzzy = options.get('fuzzy_match', True)
    timeout = options.get('timeout', 10)

    try:
        # URL encode card name
        encoded_name = urllib.parse.quote(card_name.strip())

        # Use fuzzy or exact search
        search_type = "fuzzy" if fuzzy else "exact"
        api_url = f"https://api.scryfall.com/cards/named?{search_type}={encoded_name}"

        response = requests.get(api_url, timeout=timeout)
        response.raise_for_status()

        card_data = response.json()

        # Extract relevant fields
        result = {
            "name": card_data.get("name"),
            "scryfall_id": card_data.get("id"),
            "mana_cost": card_data.get("mana_cost"),
            "type_line": card_data.get("type_line"),
            "oracle_text": card_data.get("oracle_text"),
            "image_uris": card_data.get("image_uris", {}),
            "status": "success"
        }

        # Include prices if requested
        if options.get('include_prices', False):
            result["prices"] = card_data.get("prices", {})

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {
                "name": card_name,
                "status": "failed",
                "error": "Card not found",
                "error_type": "HTTP_404"
            }
        else:
            return {
                "name": card_name,
                "status": "failed",
                "error": f"HTTP {e.response.status_code}",
                "error_type": f"HTTP_{e.response.status_code}"
            }

    except requests.exceptions.Timeout:
        return {
            "name": card_name,
            "status": "failed",
            "error": "Request timeout",
            "error_type": "NETWORK_TIMEOUT"
        }

    except Exception as e:
        return {
            "name": card_name,
            "status": "failed",
            "error": str(e),
            "error_type": "UNKNOWN_ERROR"
        }

def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "card_names required",
            "usage": "fetch-card-data.py <card_name> [<card_name2> ...]"
        }), file=sys.stderr)
        sys.exit(1)

    # Parse card names from arguments
    card_names = sys.argv[1:]

    options = {
        'fuzzy_match': True,
        'include_prices': False,
        'timeout': 10
    }

    results = {
        'cards': [],
        'total': len(card_names),
        'successful': 0,
        'failed': 0,
        'errors': []
    }

    for card_name in card_names:
        card_data = fetch_card_data(card_name, options)
        results['cards'].append(card_data)

        if card_data['status'] == 'success':
            results['successful'] += 1
        else:
            results['failed'] += 1
            results['errors'].append({
                'card': card_name,
                'error': card_data.get('error'),
                'error_type': card_data.get('error_type')
            })

    # Output JSON result
    print(json.dumps(results, indent=2))

    # Exit with error if any failures
    sys.exit(0 if results['failed'] == 0 else 1)

if __name__ == "__main__":
    main()
```

## Error Codes

- `0`: Success (all cards fetched)
- `1`: Partial or total failure (check errors array)

## Error Types

- `HTTP_404`: Card not found (permanent error, do not retry)
- `HTTP_429`: Rate limit exceeded (transient error, retry with backoff)
- `NETWORK_TIMEOUT`: Request timeout (transient error, retry)
- `UNKNOWN_ERROR`: Other errors (inspect error message)
