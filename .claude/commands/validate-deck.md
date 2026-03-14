# Validate EDH Deck

Check an EDH/Commander decklist against format rules and best practices.

## Arguments
- $ARGUMENTS: The decklist file path (e.g., `decklists/gw_counters.txt`)

## Instructions

1. Read the decklist file. If no path provided, list available decklists in `decklists/` and ask which one to validate.

2. **Card Count Validation**
   - EDH decks must have exactly 100 cards (including the commander)
   - Report the current count and whether cards need to be added or removed

3. **Duplicate Check**
   - EDH is a singleton format (only 1 copy of each card, except basic lands)
   - Flag any duplicate non-basic-land cards

4. **Card Legality Check**
   For each card, verify it exists on Scryfall and check:
   - Is it a real Magic card? (catches typos/misspellings)
   - Is it legal in Commander format?
   Use WebFetch with Scryfall API:
   ```
   https://api.scryfall.com/cards/named?fuzzy=<card_name>
   ```
   Check the `legalities.commander` field in the response.

5. **Commander Identification**
   - Try to identify the commander (usually the first card, or ask the user)
   - Verify the commander has the "can be your commander" property
   - Check all cards match the commander's color identity

6. **Land Count Check**
   - Typical EDH decks run 35-38 lands
   - Flag if significantly above or below this range
   - Check for appropriate color fixing if multicolor

7. **Essential Categories Check**
   - Ramp: recommend 10-12 sources
   - Card draw: recommend 10+ sources
   - Removal: recommend 8-10 pieces
   - Board wipes: recommend 3-5

8. **Output a validation report** with:
   - PASS/FAIL status for each rule
   - Warnings for best-practice violations
   - Specific cards that have issues
   - Suggested fixes for any failures
