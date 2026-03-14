# Commander Profile

Deep-dive into a commander's identity, archetypes, play patterns, and strategic routes.

## Arguments
- $ARGUMENTS: A commander name (e.g., "Osgir, the Reconstructor", "Atraxa, Praetors' Voice")

## Instructions

1. **Look up the commander** on Scryfall to get exact card data:
   ```
   https://api.scryfall.com/cards/named?fuzzy=<commander_name>
   ```
   Extract: name, mana cost, color identity, type line, oracle text, power/toughness, EDHREC rank.

2. **Research the commander's meta standing** using web search:
   - Search for `"<commander name>" EDHREC commander archetypes strategies`
   - Search for `"<commander name>" commander guide primer 2025 2026`
   - Search for `"<commander name>" EDH builds routes`
   - Check EDHREC themes page if available: `https://edhrec.com/commanders/<slug>`

3. **Build a comprehensive profile** covering:

   ### Identity
   - Color identity and what it means for available tools
   - Mana cost and when the commander typically hits the table
   - Keywords and innate abilities
   - What makes this commander unique vs. similar options

   ### Archetypes & Build Routes
   For EACH viable archetype/build, describe:
   - **Strategy name** (e.g., "Artifact Value", "Stax", "Combo", "Voltron")
   - **Core game plan**: how does this build win?
   - **Key cards** (5-10 that define this archetype)
   - **Strengths**: what matchups/metas does this build shine in?
   - **Weaknesses**: what shuts it down?
   - **Power level**: casual / mid / high / cEDH
   - **Budget range**: budget-friendly or requires expensive staples?

   ### Play Patterns
   - Ideal turn sequence (turns 1-5)
   - When to cast the commander vs. develop the board
   - Key decision points during a game
   - How to recover from board wipes
   - Common mistakes to avoid

   ### Synergy Map
   - Cards that are auto-includes regardless of archetype
   - Cards that are archetype-specific
   - Combos (2-card, 3-card) with explanation of how they work
   - Engines that generate recurring value

   ### Archetype Comparison Table
   Present a comparison table of the viable builds:
   ```
   | Build     | Power | Budget | Complexity | Win Speed | Resilience |
   |-----------|-------|--------|------------|-----------|------------|
   | Value     | Mid   | $      | Low        | Slow      | High       |
   | Combo     | High  | $$$    | High       | Fast      | Medium     |
   | Stax      | cEDH  | $$$$   | Very High  | Slow      | Very High  |
   ```

   ### Route Diff
   Show what cards change between archetypes:
   - **Shared core** (cards in ALL builds)
   - **Build-specific cards** (what makes each route unique)
   - **Cards to cut** from the precon/base for each route

4. **If a precon exists** for this commander, note it and describe the upgrade path from precon → each archetype.

5. **Save the profile** to `decklists/<commander-slug>_profile.md` for reference.

## Output Format
Use clear headers, tables, and bullet points. This should serve as a comprehensive reference for someone deciding how to build this commander.
