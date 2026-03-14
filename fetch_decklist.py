#!/usr/bin/env python3
"""
Fetch decklists from popular MTG deck sites.

Supports: EDHREC, Moxfield, Archidekt, TappedOut, Scryfall.
Uses browser-like headers and site-specific API endpoints to bypass basic bot detection.

Usage:
    # EDHREC average deck
    python3 fetch_decklist.py edhrec osgir-the-reconstructor

    # EDHREC with theme
    python3 fetch_decklist.py edhrec osgir-the-reconstructor --theme artifacts

    # Moxfield deck by ID or URL
    python3 fetch_decklist.py moxfield OT7jKt0pAEmr6l1tKGvrMw
    python3 fetch_decklist.py moxfield https://moxfield.com/decks/OT7jKt0pAEmr6l1tKGvrMw

    # Archidekt deck by ID or URL
    python3 fetch_decklist.py archidekt 5919765
    python3 fetch_decklist.py archidekt https://archidekt.com/decks/5919765/edh_2024_osgir

    # TappedOut by slug or URL
    python3 fetch_decklist.py tappedout osgir-the-reconstructor

    # Auto-detect site from URL
    python3 fetch_decklist.py url https://moxfield.com/decks/OT7jKt0pAEmr6l1tKGvrMw

    # Scryfall card lookup
    python3 fetch_decklist.py scryfall "Osgir, the Reconstructor"
"""

import sys
import json
import argparse
import time
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


# Browser-like headers to bypass basic bot detection
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

SESSION = requests.Session()
SESSION.headers.update(BROWSER_HEADERS)


def fetch_edhrec(commander_slug, theme=None, output_dir="decklists"):
    """
    Fetch commander data from EDHREC's JSON API.

    Args:
        commander_slug: e.g. "osgir-the-reconstructor"
        theme: optional theme like "artifacts", "stax", "combo"
        output_dir: where to save the decklist
    """
    # EDHREC serves JSON at these endpoints
    if theme:
        url = f"https://json.edhrec.com/pages/commanders/{commander_slug}/{theme}.json"
    else:
        url = f"https://json.edhrec.com/pages/commanders/{commander_slug}.json"

    avg_url = f"https://json.edhrec.com/pages/average-decks/{commander_slug}.json"

    print(f"Fetching EDHREC: {commander_slug}" + (f" ({theme})" if theme else ""))

    # Try the commander page for top cards
    cards = []
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Extract card names from the cardlists
        if "cardlists" in data:
            for cardlist in data["cardlists"]:
                header = cardlist.get("header", "")
                for card_entry in cardlist.get("cardviews", []):
                    name = card_entry.get("name")
                    synergy = card_entry.get("synergy", 0)
                    inclusion = card_entry.get("inclusion", 0)
                    if name:
                        cards.append({
                            "name": name,
                            "category": header,
                            "synergy": synergy,
                            "inclusion": inclusion,
                        })

        # Also try container format
        if "container" in data:
            container = data["container"]
            if "json_dict" in container:
                jd = container["json_dict"]
                if "cardlists" in jd:
                    for cardlist in jd["cardlists"]:
                        header = cardlist.get("header", "")
                        for card_entry in cardlist.get("cardviews", []):
                            name = card_entry.get("name")
                            if name and not any(c["name"] == name for c in cards):
                                cards.append({
                                    "name": name,
                                    "category": header,
                                    "synergy": card_entry.get("synergy", 0),
                                    "inclusion": card_entry.get("inclusion", 0),
                                })

        print(f"  Found {len(cards)} cards from commander page")

    except requests.exceptions.HTTPError as e:
        print(f"  Warning: Commander page failed ({e})")
    except Exception as e:
        print(f"  Warning: {e}")

    # Try average deck
    avg_cards = []
    try:
        time.sleep(0.2)
        resp = SESSION.get(avg_url, timeout=15)
        resp.raise_for_status()
        avg_data = resp.json()

        # Average deck is usually in a different format
        if "deck" in avg_data:
            for card_name in avg_data["deck"]:
                avg_cards.append(card_name)
        elif "cardlists" in avg_data:
            for cardlist in avg_data["cardlists"]:
                for card_entry in cardlist.get("cardviews", []):
                    name = card_entry.get("name")
                    if name:
                        avg_cards.append(name)

        print(f"  Found {len(avg_cards)} cards from average deck")

    except Exception as e:
        print(f"  Note: Average deck not available ({e})")

    # Build output
    suffix = f"_{theme}" if theme else ""
    result = {
        "source": "edhrec",
        "commander": commander_slug,
        "theme": theme,
        "top_cards": cards,
        "average_deck": avg_cards,
    }

    # Save top cards as decklist
    if cards:
        # Take top cards by inclusion, limit to ~100
        sorted_cards = sorted(cards, key=lambda c: c["inclusion"], reverse=True)
        card_names = [c["name"] for c in sorted_cards[:100]]

        out_path = Path(output_dir) / f"{commander_slug}{suffix}_edhrec.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            f.write("\n".join(card_names) + "\n")
        print(f"  Saved: {out_path} ({len(card_names)} cards)")
        result["decklist_path"] = str(out_path)

    # Save average deck if available
    if avg_cards:
        avg_path = Path(output_dir) / f"{commander_slug}_average.txt"
        avg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(avg_path, "w") as f:
            f.write("\n".join(avg_cards) + "\n")
        print(f"  Saved: {avg_path} ({len(avg_cards)} cards)")
        result["average_deck_path"] = str(avg_path)

    # Save full JSON data
    json_path = Path(output_dir) / f"{commander_slug}{suffix}_edhrec.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Saved: {json_path}")

    return result


def fetch_moxfield(deck_id, output_dir="decklists"):
    """
    Fetch decklist from Moxfield API.

    Args:
        deck_id: Moxfield deck ID or full URL
    """
    # Extract ID from URL if needed
    if "moxfield.com" in deck_id:
        deck_id = deck_id.rstrip("/").split("/")[-1]
        # Strip /primer suffix
        if deck_id == "primer":
            parts = deck_id.rstrip("/").split("/")
            deck_id = parts[-2]

    # Moxfield API v3
    url = f"https://api2.moxfield.com/v3/decks/all/{deck_id}"

    print(f"Fetching Moxfield: {deck_id}")

    headers = {
        **BROWSER_HEADERS,
        "Accept": "application/json",
        "Origin": "https://www.moxfield.com",
        "Referer": "https://www.moxfield.com/",
    }

    try:
        resp = SESSION.get(url, headers=headers, timeout=15)

        # Try v2 if v3 fails
        if resp.status_code != 200:
            url_v2 = f"https://api2.moxfield.com/v2/decks/all/{deck_id}"
            resp = SESSION.get(url_v2, headers=headers, timeout=15)

        resp.raise_for_status()
        data = resp.json()

    except Exception as e:
        print(f"  Error: {e}")
        return None

    # Extract cards
    cards = []
    commanders = []
    deck_name = data.get("name", deck_id)

    # Commanders
    for name, entry in data.get("commanders", {}).items():
        commanders.append(name)
        cards.append(name)

    # Mainboard
    for name, entry in data.get("mainboard", {}).items():
        qty = entry.get("quantity", 1)
        for _ in range(qty):
            cards.append(name)

    print(f"  Deck: {deck_name}")
    print(f"  Commander(s): {', '.join(commanders)}")
    print(f"  Total cards: {len(cards)}")

    # Save
    safe_name = re.sub(r'[^a-z0-9_-]', '_', deck_name.lower().strip())[:50]
    out_path = Path(output_dir) / f"{safe_name}_moxfield.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(cards) + "\n")
    print(f"  Saved: {out_path}")

    return {"source": "moxfield", "name": deck_name, "cards": cards, "path": str(out_path)}


def fetch_archidekt(deck_id, output_dir="decklists"):
    """
    Fetch decklist from Archidekt API.

    Args:
        deck_id: Archidekt deck ID or full URL
    """
    # Extract ID from URL if needed
    if "archidekt.com" in deck_id:
        match = re.search(r'/decks/(\d+)', deck_id)
        if match:
            deck_id = match.group(1)

    url = f"https://archidekt.com/api/decks/{deck_id}/small/"

    print(f"Fetching Archidekt: {deck_id}")

    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Error: {e}")
        return None

    cards = []
    commanders = []
    deck_name = data.get("name", str(deck_id))

    for card_entry in data.get("cards", []):
        card = card_entry.get("card", {})
        name = card.get("oracleCard", {}).get("name", "")
        qty = card_entry.get("quantity", 1)
        categories = card_entry.get("categories", [])

        if not name:
            continue

        if "Commander" in categories:
            commanders.append(name)

        for _ in range(qty):
            cards.append(name)

    print(f"  Deck: {deck_name}")
    print(f"  Commander(s): {', '.join(commanders)}")
    print(f"  Total cards: {len(cards)}")

    safe_name = re.sub(r'[^a-z0-9_-]', '_', deck_name.lower().strip())[:50]
    out_path = Path(output_dir) / f"{safe_name}_archidekt.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(cards) + "\n")
    print(f"  Saved: {out_path}")

    return {"source": "archidekt", "name": deck_name, "cards": cards, "path": str(out_path)}


def fetch_tappedout(deck_slug, output_dir="decklists"):
    """
    Fetch decklist from TappedOut.

    Args:
        deck_slug: TappedOut deck slug or full URL
    """
    if "tappedout.net" in deck_slug:
        match = re.search(r'/mtg-decks/([^/]+)', deck_slug)
        if match:
            deck_slug = match.group(1)

    # TappedOut has a download endpoint
    url = f"https://tappedout.net/mtg-decks/{deck_slug}/?fmt=txt"

    print(f"Fetching TappedOut: {deck_slug}")

    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        print(f"  Error: {e}")
        return None

    # Parse the text format: "1x Card Name" or just "Card Name"
    cards = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # Strip quantity prefix
        match = re.match(r'^(\d+)x?\s+(.+)$', line)
        if match:
            qty = int(match.group(1))
            name = match.group(2).strip()
            # Strip set info in parens
            name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
            for _ in range(qty):
                cards.append(name)
        else:
            name = re.sub(r'\s*\([^)]*\)\s*$', '', line)
            if name:
                cards.append(name)

    print(f"  Total cards: {len(cards)}")

    safe_name = re.sub(r'[^a-z0-9_-]', '_', deck_slug.lower().strip())[:50]
    out_path = Path(output_dir) / f"{safe_name}_tappedout.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(cards) + "\n")
    print(f"  Saved: {out_path}")

    return {"source": "tappedout", "slug": deck_slug, "cards": cards, "path": str(out_path)}


def fetch_scryfall(card_name):
    """Look up a single card on Scryfall and print its details."""
    url = "https://api.scryfall.com/cards/named"
    params = {"fuzzy": card_name}

    print(f"Looking up: {card_name}")

    try:
        resp = SESSION.get(url, params=params, timeout=10)
        resp.raise_for_status()
        d = resp.json()
    except Exception as e:
        print(f"  Error: {e}")
        return None

    print(f"  Name: {d['name']}")
    print(f"  Mana: {d.get('mana_cost', 'N/A')}")
    print(f"  Type: {d['type_line']}")
    print(f"  Text: {d.get('oracle_text', 'N/A')}")
    if 'power' in d:
        print(f"  P/T: {d['power']}/{d['toughness']}")
    print(f"  Colors: {d.get('color_identity', [])}")
    print(f"  EDHREC rank: {d.get('edhrec_rank', 'N/A')}")
    print(f"  Price: ${d.get('prices', {}).get('usd', 'N/A')}")
    print(f"  Legal in Commander: {d.get('legalities', {}).get('commander', 'N/A')}")

    return d


def detect_site(url_str):
    """Auto-detect site from URL and return (site, identifier)."""
    parsed = urlparse(url_str)
    host = parsed.hostname or ""

    if "edhrec.com" in host:
        # Extract commander slug from path
        match = re.search(r'/commanders/([^/]+)', parsed.path)
        if match:
            return "edhrec", match.group(1)
        match = re.search(r'/average-decks/([^/]+)', parsed.path)
        if match:
            return "edhrec", match.group(1)

    elif "moxfield.com" in host:
        match = re.search(r'/decks/([^/]+)', parsed.path)
        if match:
            return "moxfield", match.group(1)

    elif "archidekt.com" in host:
        match = re.search(r'/decks/(\d+)', parsed.path)
        if match:
            return "archidekt", match.group(1)

    elif "tappedout.net" in host:
        match = re.search(r'/mtg-decks/([^/]+)', parsed.path)
        if match:
            return "tappedout", match.group(1)

    return None, None


def main():
    parser = argparse.ArgumentParser(
        description="Fetch MTG decklists from popular deck sites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sites:
  edhrec      EDHREC commander page (top cards + average deck)
  moxfield    Moxfield deck by ID or URL
  archidekt   Archidekt deck by ID or URL
  tappedout   TappedOut deck by slug or URL
  scryfall    Single card lookup
  url         Auto-detect site from any URL

Examples:
  %(prog)s edhrec osgir-the-reconstructor
  %(prog)s edhrec osgir-the-reconstructor --theme artifacts
  %(prog)s moxfield https://moxfield.com/decks/OT7jKt0pAEmr6l1tKGvrMw
  %(prog)s archidekt 5919765
  %(prog)s tappedout osgir-the-reconstructor
  %(prog)s url https://edhrec.com/commanders/osgir-the-reconstructor
  %(prog)s scryfall "Osgir, the Reconstructor"
        """
    )

    parser.add_argument("site", choices=["edhrec", "moxfield", "archidekt", "tappedout", "scryfall", "url"],
                        help="Source site")
    parser.add_argument("identifier", help="Deck ID, slug, URL, or card name")
    parser.add_argument("--theme", help="EDHREC theme (artifacts, stax, combo, etc.)")
    parser.add_argument("-o", "--output-dir", default="decklists", help="Output directory")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    result = None

    if args.site == "url":
        site, identifier = detect_site(args.identifier)
        if not site:
            print(f"Error: Could not detect site from URL: {args.identifier}")
            sys.exit(1)
        print(f"Detected: {site} ({identifier})")
        args.site = site
        args.identifier = identifier

    if args.site == "edhrec":
        result = fetch_edhrec(args.identifier, theme=args.theme, output_dir=args.output_dir)
    elif args.site == "moxfield":
        result = fetch_moxfield(args.identifier, output_dir=args.output_dir)
    elif args.site == "archidekt":
        result = fetch_archidekt(args.identifier, output_dir=args.output_dir)
    elif args.site == "tappedout":
        result = fetch_tappedout(args.identifier, output_dir=args.output_dir)
    elif args.site == "scryfall":
        result = fetch_scryfall(args.identifier)

    if result is None:
        print("Failed to fetch decklist.")
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))

    print("\nDone.")


if __name__ == "__main__":
    main()
