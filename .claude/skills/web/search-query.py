#!/usr/bin/env python3
"""
Web Search Skill

Performs web searches and returns structured results for use in workflows.
Useful for finding decklists, card info, strategies, and resources.

Protocol-first: Outputs A2A-compatible JSON for skill chaining.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, COMMAND_ERROR


def search_web(
    query: str,
    max_results: int = 5,
    allowed_domains: Optional[List[str]] = None,
    blocked_domains: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Perform web search and return structured results.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        allowed_domains: Optional list of domains to restrict search to
        blocked_domains: Optional list of domains to exclude

    Returns:
        Dict with search_results, query, result_count
    """
    # Note: This is a protocol interface. In actual execution, the MCP server
    # would handle the WebSearch tool call. This skill defines the contract.

    print(f"\n🔍 Searching: {query}", file=sys.stderr)
    if allowed_domains:
        print(f"   Domains: {', '.join(allowed_domains)}", file=sys.stderr)

    # Return structured output for A2A protocol
    return {
        "query": query,
        "max_results": max_results,
        "allowed_domains": allowed_domains or [],
        "blocked_domains": blocked_domains or [],
        "search_type": "web",
        "note": "Search will be executed by MCP server with WebSearch tool"
    }


def search_cards(
    card_name: str = None,
    deck_archetype: str = None,
    commander: str = None
) -> Dict[str, Any]:
    """
    Search for Magic card or deck information.

    Args:
        card_name: Specific card to search for
        deck_archetype: Deck type (e.g., "Frog Tribal", "Goblins")
        commander: Commander name for EDH decks

    Returns:
        Dict with search parameters optimized for MTG content
    """
    # Build search query
    query_parts = []

    if card_name:
        query_parts.append(f'"{card_name}" mtg card')
    if deck_archetype:
        query_parts.append(f'{deck_archetype} edh deck')
    if commander:
        query_parts.append(f'{commander} commander decklist')

    if not query_parts:
        raise ValueError("Must provide at least one search parameter")

    query = " ".join(query_parts)

    # Prioritize MTG-specific sites
    allowed_domains = [
        "scryfall.com",
        "edhrec.com",
        "mtggoldfish.com",
        "archidekt.com",
        "moxfield.com",
        "commanderspellbook.com"
    ]

    print(f"\n🎴 MTG Card Search: {query}", file=sys.stderr)
    print(f"   Prioritizing: {', '.join(allowed_domains[:3])}", file=sys.stderr)

    return {
        "query": query,
        "search_type": "mtg_cards",
        "card_name": card_name,
        "deck_archetype": deck_archetype,
        "commander": commander,
        "allowed_domains": allowed_domains,
        "max_results": 10,
        "note": "Search optimized for Magic: The Gathering content"
    }


def main():
    """CLI entry point for web search skill"""
    parser = argparse.ArgumentParser(
        description='Web search skill for finding card/deck information'
    )

    # Search type
    search_group = parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument(
        '--query',
        help='Generic web search query'
    )
    search_group.add_argument(
        '--card-name',
        help='Search for specific card (MTG-optimized)'
    )
    search_group.add_argument(
        '--deck-archetype',
        help='Search for deck archetype (e.g., "Frog Tribal")'
    )
    search_group.add_argument(
        '--commander',
        help='Search for commander decklists'
    )

    # Optional parameters
    parser.add_argument(
        '--max-results',
        type=int,
        default=5,
        help='Maximum number of results (default: 5)'
    )
    parser.add_argument(
        '--allowed-domains',
        nargs='+',
        help='Restrict search to these domains'
    )
    parser.add_argument(
        '--blocked-domains',
        nargs='+',
        help='Exclude these domains from results'
    )
    parser.add_argument(
        '--output',
        help='Output file for results JSON (default: stdout)'
    )

    args = parser.parse_args()

    try:
        # Determine search type and execute
        if args.query:
            result = search_web(
                args.query,
                args.max_results,
                args.allowed_domains,
                args.blocked_domains
            )
        elif args.card_name or args.deck_archetype or args.commander:
            result = search_cards(
                args.card_name,
                args.deck_archetype,
                args.commander
            )
        else:
            raise ValueError("No search parameters provided")

        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Search params saved to: {args.output}", file=sys.stderr)

        # Print result summary
        print("\n" + "=" * 70, file=sys.stderr)
        print("🔍 WEB SEARCH PREPARED", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n📝 Query: {result['query']}", file=sys.stderr)
        print(f"   Type: {result['search_type']}", file=sys.stderr)
        print(f"   Max Results: {result['max_results']}", file=sys.stderr)

        if result.get('allowed_domains'):
            print(f"\n🎯 Target Domains: {len(result['allowed_domains'])} specified", file=sys.stderr)
            for domain in result['allowed_domains'][:3]:
                print(f"   • {domain}", file=sys.stderr)

        if result.get('note'):
            print(f"\n📌 {result['note']}", file=sys.stderr)

        print("=" * 70, file=sys.stderr)

        # Output to stdout for skill chaining (A2A protocol)
        format_success_output(result)

    except Exception as e:
        format_error_output(
            f"Web search preparation failed: {str(e)}",
            exit_code=COMMAND_ERROR,
            context={
                "query": args.query,
                "card_name": args.card_name,
                "exception": str(e)
            }
        )


if __name__ == '__main__':
    main()
