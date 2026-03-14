# Build EDH Deck

Help build a new EDH/Commander deck from scratch or from a starting concept.

## Arguments
- $ARGUMENTS: A commander name, color combination, theme, or strategy (e.g., "Atraxa +1/+1 counters", "mono-red goblins", "simic landfall")

## Instructions

1. **Parse the request** to identify:
   - Commander (if specified)
   - Color identity
   - Theme/strategy
   - Budget constraints (if mentioned)

2. **If a commander is specified**, look it up on Scryfall to confirm it's a valid commander:
   ```
   https://api.scryfall.com/cards/named?fuzzy=<commander_name>
   ```
   Confirm its color identity, abilities, and synergies.

3. **If only a theme is specified**, suggest 3-5 commander options that support that theme using your MTG knowledge and Scryfall searches. Let the user pick one before proceeding.

4. **Build the decklist** with this structure (totaling 100 cards including commander):
   - **Commander** (1)
   - **Lands** (35-37): appropriate basics + utility lands + color fixing
   - **Ramp** (10-12): mana rocks, land ramp, mana dorks as appropriate
   - **Card Draw** (10-12): card advantage engines matching the strategy
   - **Removal** (8-10): targeted removal + 3-4 board wipes
   - **Core Strategy** (30-35): cards that directly support the deck's game plan
   - **Support/Utility** (remaining): protection, recursion, tutors

5. **For each category**, explain WHY key cards were chosen and how they synergize with the commander/theme.

6. **Write the decklist** to a new file:
   ```
   decklists/<deck_name>.txt
   ```
   Format: one card name per line, no quantities (EDH is singleton).

7. **After creating the decklist**, offer to:
   - Run `/analyze-deck` on it
   - Run `/validate-deck` on it
   - Run `/generate-deck` to create printable proxies

## Notes
- Prioritize cards that synergize with the commander and theme
- Include a healthy mana base appropriate to the color count
- For 2-color decks: ~10 dual lands + basics
- For 3-color decks: ~15 dual/tri lands + basics
- Use your knowledge of EDH staples and format-defining cards
- Default to a mid-power casual build unless the user specifies otherwise
