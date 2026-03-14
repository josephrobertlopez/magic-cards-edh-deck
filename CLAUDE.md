# MTG EDH Deck Proxy Generator

## Project Overview
Generates print-ready PDF proxies from MTG card lists. Fetches card images from Scryfall API, arranges them on US Letter paper (8.5" x 11") in a 2x4 landscape grid, and outputs PPTX + PDF files.

## Key Commands
- `python3 generate_deck.py <decklist_file>` - Generate proxies from a decklist

## Project Structure
- `generate_deck.py` - Main proxy generation script
- `decklists/` - Card lists (one card name per line)
- `outputs/` - Generated PPTX and PDF files
- `images/` - Cached card images from Scryfall
- `archive/` - Legacy scripts

## Custom Skills
- `/generate-deck <file>` - Generate printable proxies from a decklist
- `/analyze-deck <file>` - Analyze deck composition, mana curve, and strategy
- `/find-cards <query>` - Search for MTG cards via Scryfall (e.g., "green ramp under 3 mana")
- `/validate-deck <file>` - Check EDH format legality and best practices
- `/build-deck <concept>` - Build a new EDH deck from a commander or theme
- `/scrape-meta <commander>` - Scrape EDHREC for a meta decklist given a commander name

## Scryfall API
- Card lookup: `https://api.scryfall.com/cards/named?fuzzy=<name>`
- Card search: `https://api.scryfall.com/cards/search?q=<query>&order=edhrec`
- Rate limit: 10 requests/second, add 100ms delay between calls
- Docs: https://scryfall.com/docs/api

## EDH Format Rules
- Exactly 100 cards including commander
- Singleton (one copy of each card, except basic lands)
- All cards must match commander's color identity
- Commander must be a legendary creature (or card that says "can be your commander")
