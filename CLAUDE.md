# MTG EDH Deck Proxy Generator

## Project Overview
Generates print-ready PDF proxies from MTG card lists. Fetches card images from Scryfall API, arranges them on US Letter paper (8.5" x 11") in a 2x4 landscape grid, and outputs PPTX + PDF files.

## Key Commands
- `python3 generate_deck.py <decklist_file>` - Generate proxies from a decklist
- `python3 grid_layout.py [OPTIONS] <images>` - Configurable grid layout for any images

## Project Structure
- `generate_deck.py` - Main proxy generation script (decklist → Scryfall → proxies)
- `grid_layout.py` - Configurable grid layout (any images → print-ready PPTX/PDF)
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
- `/proxy-grid <images>` - Generate proxy sheets with configurable grids (2x4, 3x3, full-art, etc.)
- `/fetch-decklist <url|query>` - Fetch decklists from any site via WebSearch (bypasses 403s)
- `/commander-profile <name>` - Deep-dive: archetypes, play patterns, route diffs, combo maps
- `/deck-recommendations <list>` - Meta-informed upgrade recommendations with tiered swap lists

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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **magic-cards-edh-deck** (683 symbols, 1413 relationships, 55 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/magic-cards-edh-deck/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/magic-cards-edh-deck/context` | Codebase overview, check index freshness |
| `gitnexus://repo/magic-cards-edh-deck/clusters` | All functional areas |
| `gitnexus://repo/magic-cards-edh-deck/processes` | All execution flows |
| `gitnexus://repo/magic-cards-edh-deck/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
