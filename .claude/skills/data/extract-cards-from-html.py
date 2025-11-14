#!/usr/bin/env python3
"""Extract card names from HTML file (EDHREC format)."""

import sys
import json
import re
from pathlib import Path

def extract_card_names(html_path, max_cards=100):
    """Extract card names from EDHREC HTML."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Extract card names from JSON data in HTML
    pattern = r'"name":"([^"]+)"'
    matches = re.findall(pattern, html)
    
    # Filter out non-card names
    filtered = []
    skip_terms = ['EDHREC', 'Ben Doolittle', 'Commander', 'Decklist']
    
    for name in matches:
        if any(skip in name for skip in skip_terms):
            continue
        filtered.append(name)
    
    # Deduplicate and limit
    unique_cards = list(dict.fromkeys(filtered))[:max_cards]
    
    return unique_cards

def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "status": "error",
            "error": "Usage: extract-cards-from-html.py <html_file> <output_txt>"
        }))
        sys.exit(1)
    
    html_path = sys.argv[1]
    output_path = sys.argv[2]
    max_cards = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    
    try:
        cards = extract_card_names(html_path, max_cards)
        
        # Write to text file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('\n'.join(cards))
        
        print(json.dumps({
            "status": "success",
            "decklist_path": output_path,
            "total_cards": len(cards)
        }))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
