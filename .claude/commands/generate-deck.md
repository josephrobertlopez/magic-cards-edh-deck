# Generate Deck Proxies

Generate print-ready proxy PDFs from a decklist file.

## Arguments
- $ARGUMENTS: The decklist file path (e.g., `decklists/my_deck.txt`), or a deck name to look up

## Instructions

1. If the user provided a decklist file path, verify it exists. If it doesn't exist, check `decklists/` for similarly named files and suggest them.
2. If the user provided a deck name instead of a file path, search `decklists/` for a matching `.txt` file.
3. Read the decklist file and report the card count.
4. Run the generator script:
   ```bash
   python3 generate_deck.py <decklist_file>
   ```
5. Report the results: number of cards processed, output file locations, and any cards that failed to fetch.

## Notes
- The script fetches card images from Scryfall API and caches them in `images/`
- Output goes to `outputs/` as both PPTX and PDF
- PDF conversion requires LibreOffice; if unavailable, the PPTX is still generated
- Cards are laid out 8 per page (2x4 grid, landscape) on US Letter paper
- Print at 100% scale (no fit-to-page) for correct sizing
