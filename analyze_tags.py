#!/usr/bin/env python3
"""
MTG Card Tag Analysis using Scryfall API + Tagger scraping.
Extends generate_deck.py with community tag mining and rule analysis.
"""

import sys
import json
import requests
import time
from pathlib import Path
from collections import Counter, defaultdict
from urllib.parse import quote
import re

# Import existing Scryfall functionality
from generate_deck import fetch_card_from_scryfall, load_metadata_cache, save_metadata_cache

TAG_CACHE_PATH = "cache/tag_data.json"

def load_tag_cache():
    """Load tag data cache."""
    if Path(TAG_CACHE_PATH).exists():
        with open(TAG_CACHE_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_tag_cache(cache):
    """Save tag data cache."""
    Path("cache").mkdir(exist_ok=True)
    with open(TAG_CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)

def search_cards_by_name_pattern(pattern):
    """Search for all cards matching a name pattern using Scryfall search API."""
    print(f"🔍 Searching for cards matching: '{pattern}'")

    url = "https://api.scryfall.com/cards/search"
    params = {
        "q": pattern,
        "order": "name"
    }

    cards = []
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        total_cards = data.get('total_cards', 0)
        print(f"  📊 Found {total_cards} cards")

        # Get all pages of results
        while True:
            cards.extend(data.get('data', []))

            if not data.get('has_more', False):
                break

            next_page = data.get('next_page')
            if not next_page:
                break

            print(f"  📄 Fetching next page...")
            time.sleep(0.1)  # Rate limiting
            response = requests.get(next_page, timeout=10)
            response.raise_for_status()
            data = response.json()

    except Exception as e:
        print(f"  ❌ Search failed: {e}")
        return []

    print(f"  ✅ Retrieved {len(cards)} total cards")
    return cards

def scrape_tagger_data(set_code, collector_number, card_name):
    """Get community tags from Scryfall Tagger GraphQL API."""
    from scryfall_tagger_api import ScryfallTaggerAPI

    print(f"  🏷️  Fetching via GraphQL API: {set_code}/{collector_number}")

    try:
        api = ScryfallTaggerAPI()
        card_data = api.fetch_card_tags(set_code, collector_number)

        if not card_data:
            print(f"  ❌ Failed to fetch card data")
            return None

        tag_info = api.extract_community_tags(card_data)
        if not tag_info:
            print(f"  ❌ Failed to extract tag data")
            return None

        # Extract inherited tags from ancestor hierarchy
        inherited_artwork = set()
        inherited_card = set()

        # Collect ancestor tags from artwork tags
        for tag in tag_info['artwork_tags']:
            for ancestor in tag.get('ancestor_tags', []):
                inherited_artwork.add(ancestor['name'])

        # Collect ancestor tags from card tags
        for tag in tag_info['card_tags']:
            for ancestor in tag.get('ancestor_tags', []):
                inherited_card.add(ancestor['name'])

        # Convert to the expected format
        tags = {
            'artwork': [tag['name'] for tag in tag_info['artwork_tags']],
            'card': [tag['name'] for tag in tag_info['card_tags']],
            'printing': [tag['name'] for tag in tag_info['print_tags']],
            'inherited_artwork': list(inherited_artwork),
            'inherited_card': list(inherited_card)
        }

        artwork_count = len(tags['artwork'])
        card_count = len(tags['card'])
        print_count = len(tags['printing'])

        print(f"  ✅ Extracted {artwork_count} artwork + {card_count} card + {print_count} print tags")

        return tags

    except Exception as e:
        print(f"  ❌ Failed to get tagger data: {e}")
        return None

def analyze_card_batch(card_names_or_pattern):
    """Analyze a batch of cards for tag patterns."""
    print(f"🎯 Starting tag analysis for: {card_names_or_pattern}")

    # Check if it's a search pattern or specific card names
    if ',' in card_names_or_pattern:
        # Comma-separated list of specific cards
        card_names = [name.strip() for name in card_names_or_pattern.split(',')]
        cards_data = []

        for card_name in card_names:
            card_data = fetch_card_from_scryfall(card_name)
            if card_data:
                cards_data.append(card_data)
    else:
        # Search pattern
        cards_data = search_cards_by_name_pattern(card_names_or_pattern)

    if not cards_data:
        print("❌ No cards found!")
        return

    print(f"📊 Analyzing {len(cards_data)} cards...")

    # Load tag cache
    tag_cache = load_tag_cache()
    results = []

    for card in cards_data:
        card_name = card.get('name', 'Unknown')
        set_code = card.get('set', '')
        collector_number = card.get('collector_number', '')

        print(f"\n🔍 Processing: {card_name} ({set_code} #{collector_number})")

        # Check cache first
        cache_key = f"{set_code}_{collector_number}"
        if cache_key in tag_cache:
            print(f"  💾 Using cached tag data")
            tag_data = tag_cache[cache_key]
        else:
            # Scrape fresh data
            tag_data = scrape_tagger_data(set_code, collector_number, card_name)
            if tag_data:
                tag_cache[cache_key] = tag_data
                time.sleep(0.2)  # Rate limiting for scraping

        results.append({
            'name': card_name,
            'set': set_code,
            'number': collector_number,
            'type_line': card.get('type_line', ''),
            'mana_cost': card.get('mana_cost', ''),
            'tags': tag_data or {},
            'tagger_url': f"https://tagger.scryfall.com/card/{set_code}/{collector_number}"
        })

    # Save updated cache
    save_tag_cache(tag_cache)

    # Analysis summary
    print(f"\n📈 ANALYSIS SUMMARY")
    print(f"={'='*50}")

    for result in results:
        print(f"{result['name']:30} | {result['set']:5} #{result['number']:>3} | {result['type_line']}")
        print(f"{'':30} | Tagger: {result['tagger_url']}")
        if result['tags']:
            artwork_count = len(result['tags'].get('artwork', []))
            card_count = len(result['tags'].get('card', []))
            print(f"{'':30} | Tags: {artwork_count} artwork, {card_count} card")
        print()

    # Save results to file
    output_file = f"analysis_results_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved to: {output_file}")

    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_tags.py '<card_pattern_or_list>'")
        print("Examples:")
        print("  python3 analyze_tags.py 'ajani'")
        print("  python3 analyze_tags.py 'Lightning Bolt, Counterspell, Sol Ring'")
        sys.exit(1)

    pattern = sys.argv[1]
    analyze_card_batch(pattern)

if __name__ == "__main__":
    main()