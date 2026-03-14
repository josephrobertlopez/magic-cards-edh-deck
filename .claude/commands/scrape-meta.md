# Scrape Meta Decklist

Scrape a competitive/popular EDH decklist for a given commander from EDHREC and other sources.

## Arguments
- $ARGUMENTS: A commander name (e.g., "Atraxa Praetors Voice", "Krenko Mob Boss", "Tymna Thrasios")

## Instructions

1. **Normalize the commander name** for URL formatting:
   - Lowercase, replace spaces with hyphens, strip commas/apostrophes
   - Example: "Atraxa, Praetors' Voice" → "atraxa-praetors-voice"

2. **Fetch the EDHREC commander page** to get popular/meta cards:
   ```
   https://edhrec.com/commanders/<commander-slug>
   ```
   Use WebFetch to retrieve the page and extract:
   - The most-played cards for this commander (EDHREC shows cards by inclusion %)
   - Card categories: creatures, instants, sorceries, artifacts, enchantments, planeswalkers, lands
   - Synergy scores (cards that are uniquely popular with THIS commander vs. generally popular)

3. **Also try the EDHREC average deck page** for a pre-built meta list:
   ```
   https://edhrec.com/average-decks/<commander-slug>
   ```
   This page often has a complete "average deck" that represents the meta build.

4. **If EDHREC data is insufficient**, supplement with Scryfall search for the commander's top synergy cards:
   ```
   https://api.scryfall.com/cards/named?fuzzy=<commander_name>
   ```
   Use the commander's color identity and keywords to find staples.

5. **Build the decklist** (100 cards total):
   - Start with the commander
   - Pull the highest-inclusion-% cards from each category on EDHREC
   - Ensure proper deck structure:
     - 35-37 lands (including color-appropriate fixing)
     - 10-12 ramp sources
     - 10+ card draw
     - 8-10 removal pieces
   - Prioritize high-synergy cards (cards that are disproportionately popular with this specific commander)
   - Fill remaining slots with format staples in the commander's colors

6. **Save the decklist** to:
   ```
   decklists/<commander-slug>.txt
   ```
   Format: one card name per line, commander as the first card.

7. **Report results** including:
   - Commander name and color identity
   - Source of data (EDHREC page URL)
   - Number of decks sampled (EDHREC shows this)
   - Total cards in the generated list
   - Top 5 highest-synergy cards and why they're strong with this commander
   - Any notable meta variations or archetypes (e.g., "Atraxa has Superfriends, +1/+1 Counters, and Infect builds")

8. **Offer next steps**:
   - Run `/validate-deck` to verify legality
   - Run `/analyze-deck` for mana curve analysis
   - Run `/generate-deck` to create printable proxies

## Tips
- EDHREC commander slugs typically follow: `firstname-lastname` (e.g., `krenko-mob-boss`)
- For partner commanders, use: `commander1/commander2` format
- If the commander page isn't found, suggest similar commander names
- High synergy score = uniquely good with this commander (prioritize these)
- High inclusion % = generically popular (good but less unique)
