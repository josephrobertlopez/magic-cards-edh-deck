# Analyze EDH Deck

Analyze an EDH/Commander decklist for composition, mana curve, and strategy insights.

## Arguments
- $ARGUMENTS: The decklist file path (e.g., `decklists/gw_counters.txt`)

## Instructions

1. Read the decklist file from the provided path. If no path given, list available decklists in `decklists/` and ask which one to analyze.
2. For each card in the list, fetch its data from Scryfall to get type, mana cost, colors, and keywords:
   ```
   https://api.scryfall.com/cards/named?fuzzy=<card_name>
   ```
   Use WebFetch for a sample of key cards (up to ~20-30) to avoid rate limits, and use your MTG knowledge for well-known staples.

3. Provide a comprehensive analysis including:

   **Deck Composition**
   - Total card count (EDH requires exactly 100 including commander)
   - Breakdown by card type: creatures, instants, sorceries, enchantments, artifacts, planeswalkers, lands
   - Color identity summary

   **Mana Curve**
   - Distribution of cards by mana value (0, 1, 2, 3, 4, 5, 6, 7+)
   - Show as a simple ASCII histogram
   - Average mana value (excluding lands)

   **Strategy Assessment**
   - Identify the deck's likely strategy/archetype
   - Key synergies and combos spotted
   - Win conditions

   **EDH Staples Check**
   - Ramp package (count and quality)
   - Card draw sources
   - Removal/interaction count
   - Board wipes

   **Recommendations**
   - Cards that seem off-theme or underperforming
   - Common staples that are missing for this strategy
   - Mana curve concerns
   - Suggest 3-5 cards to add and 3-5 cards to consider cutting

4. Format the output clearly with headers and bullet points.
