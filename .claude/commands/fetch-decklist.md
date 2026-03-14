# Fetch Decklist

Fetch full decklists from the web using search. Bypasses API restrictions by using web search to find and extract card lists from deck sites.

## Arguments
- $ARGUMENTS: A URL, commander name, deck site + ID, or search query.
  Examples:
  - `https://edhrec.com/commanders/osgir-the-reconstructor`
  - `https://moxfield.com/decks/OT7jKt0pAEmr6l1tKGvrMw`
  - `osgir-the-reconstructor edhrec top cards`
  - `osgir precon lorehold legacies`
  - `krenko mob boss budget edh`

## Instructions

IMPORTANT: Direct HTTP requests (curl, requests, WebFetch) are often blocked by deck sites (EDHREC, Moxfield, Archidekt, TappedOut). Use **WebSearch** as the primary tool — it reliably returns data from these sites.

### Strategy: Multi-pass WebSearch extraction

1. **Parse the request** to identify:
   - Commander name
   - Source site preference (EDHREC, Moxfield, Archidekt, TappedOut)
   - Theme/archetype if specified
   - Whether they want a precon, average deck, or specific user deck

2. **Execute targeted searches** to extract card data. Run multiple searches to cover different card categories:

   **Search 1 — Full decklist:**
   ```
   "<commander name>" decklist full 100 cards site:<preferred_site>
   ```

   **Search 2 — Creatures and key cards:**
   ```
   "<commander name>" EDH best creatures artifacts top cards EDHREC
   ```

   **Search 3 — Support cards (ramp, draw, removal):**
   ```
   "<commander name>" commander ramp card draw removal lands decklist
   ```

   **Search 4 — Precon list (if applicable):**
   ```
   "<commander name>" precon decklist full card list
   ```

   **Search 5 — Specific archetype (if requested):**
   ```
   "<commander name>" <archetype> EDH decklist cards primer
   ```

3. **Try WebFetch as a bonus** on any promising URLs found in search results. It may work on some sites:
   - TappedOut text export: `https://tappedout.net/mtg-decks/<slug>/?fmt=txt`
   - Archidekt API: `https://archidekt.com/api/decks/<id>/small/`
   - EDHREC JSON: `https://json.edhrec.com/pages/commanders/<slug>.json`
   - Scryfall API: `https://api.scryfall.com/cards/named?fuzzy=<name>`

   If WebFetch fails (403), that's expected — fall back to the WebSearch data.

4. **Compile the decklist** from all search results:
   - Deduplicate card names
   - Organize by category (commander, creatures, artifacts, instants, sorceries, enchantments, lands)
   - Flag any cards you're uncertain about
   - Aim for 100 cards (EDH) or whatever format requires

5. **Save the decklist** to:
   ```
   decklists/<descriptive_name>.txt
   ```
   Format: one card name per line, commander first.

6. **Report results:**
   - Source URLs used
   - Total cards extracted
   - Confidence level (high if from a complete list, medium if assembled from multiple searches)
   - Any gaps or cards that need verification

## Tips
- Run 3-5 WebSearch queries to triangulate a complete list
- Search snippets often contain 10-20 card names each — combining multiple searches builds a full picture
- For precons, search for the precon product name (e.g., "Lorehold Legacies") rather than the commander name
- If searching for a specific Moxfield/Archidekt deck, include the deck name or author in the search
- EDHREC "average deck" and "top cards" pages are the richest sources of card data
