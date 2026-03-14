# Find MTG Cards

Search for Magic: The Gathering cards using Scryfall's search API.

## Arguments
- $ARGUMENTS: A description of what you're looking for (e.g., "green ramp spells under 3 mana", "white board wipes", "artifacts that give +1/+1 counters")

## Instructions

1. Parse the user's search description and translate it into a Scryfall search query.

2. Use WebFetch to query the Scryfall search API:
   ```
   https://api.scryfall.com/cards/search?q=<scryfall_query>&order=edhrec
   ```

   Common Scryfall syntax to use:
   - `c:` or `id:` for color/color identity (e.g., `id<=gw` for cards legal in GW commander)
   - `t:` for type (e.g., `t:creature`, `t:instant`)
   - `o:` for oracle text (e.g., `o:"draw a card"`, `o:"+1/+1 counter"`)
   - `cmc:` or `mv:` for mana value (e.g., `mv<=3`)
   - `f:commander` for EDH-legal cards
   - `is:commander` for legal commanders
   - `order=edhrec` to sort by EDH popularity

3. Present the results in a clear format:
   - Card name
   - Mana cost
   - Type line
   - Key abilities (brief summary)
   - EDHREC rank if available

4. Show up to 10-15 results. If there are more, mention the total count and suggest how to narrow the search.

5. If the user is building a specific deck, suggest which of the found cards would fit best and why.

## Examples
- "find-cards green creatures that put +1/+1 counters" → `f:commander c:g t:creature o:"+1/+1 counter" order=edhrec`
- "find-cards cheap white removal" → `f:commander c:w (t:instant or t:sorcery) o:destroy mv<=3 order=edhrec`
- "find-cards simic commanders" → `is:commander id=ug order=edhrec`
