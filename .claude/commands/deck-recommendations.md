# Deck Recommendations

Analyze a commander's meta strategies and recommend specific card changes for a decklist.

## Arguments
- $ARGUMENTS: A commander name or decklist file, optionally with a target archetype or power level.
  Examples:
  - `Osgir, the Reconstructor` — general recommendations
  - `decklists/osgir_precon.txt upgrade to combo` — upgrade a specific list toward combo
  - `Atraxa superfriends budget` — budget build recommendations
  - `decklists/my_deck.txt vs decklists/meta_deck.txt` — diff two lists with upgrade suggestions

## Instructions

1. **Identify the starting point**:
   - If given a decklist file, read it
   - If given just a commander name, use the precon or average EDHREC list as baseline
   - If given two files with "vs" or "diff", compare them

2. **Research the meta** via web search:
   - Search for `"<commander name>" EDHREC top cards high synergy 2025 2026`
   - Search for `"<commander name>" commander upgrades best cards`
   - Search for `"<commander name>" <archetype> EDH primer`
   - Look for win rates, popular combos, and format-defining interactions

3. **Analyze the current list** against meta data:

   ### Category Audit
   For each category, compare the deck's count to recommended ranges:
   | Category    | Current | Recommended | Status |
   |-------------|---------|-------------|--------|
   | Lands       | 38      | 35-37       | High   |
   | Ramp        | 8       | 10-12       | Low    |
   | Card Draw   | 5       | 10+         | Low    |
   | Removal     | 6       | 8-10        | Low    |
   | Board Wipes | 2       | 3-5         | OK     |

   ### Upgrade Tiers
   Organize recommendations into tiers:

   **Tier 1 — Immediate Upgrades** (highest impact, should be in every build)
   - Cards to ADD with explanation of why
   - Cards to CUT with explanation of why they underperform

   **Tier 2 — Archetype Optimization** (specific to chosen strategy)
   - Cards that push the deck toward its win condition
   - Cards that are off-theme and dilute the strategy

   **Tier 3 — Power Level Bumps** (for when you want to level up)
   - Expensive staples that significantly improve consistency
   - Combo pieces that add alternate win conditions
   - Tutors and fast mana

   ### Swap List
   Present as concrete 1-for-1 swaps:
   ```
   OUT: Boros Locket        → IN: Arcane Signet       (strictly better mana rock)
   OUT: Secret Rendezvous   → IN: Esper Sentinel      (card draw that doesn't help opponents)
   OUT: Meteor Golem        → IN: Cavalier of Dawn     (cheaper, recursive with Osgir)
   ```

   ### Budget Options
   For expensive recommendations ($10+), suggest budget alternatives.

   ### Combo Packages
   If the target archetype supports combos, present them as installable "packages":
   ```
   Infinite Mana Package (3 cards):
   + Basalt Monolith
   + Rings of Brighthearth
   + Walking Ballista (outlet)
   Requires cutting: [3 weakest cards in current list]
   ```

4. **If comparing two decklists** ("vs" or "diff" mode):
   - Show cards unique to each list
   - Identify which list is stronger and why
   - Recommend a merged "best of both" list

5. **Output a summary** with:
   - Total recommended changes (adds/cuts)
   - Estimated budget for upgrades
   - Expected power level after changes
   - What the deck will be better/worse at after changes

6. **Optionally save** the upgraded decklist to `decklists/<name>_upgraded.txt`
