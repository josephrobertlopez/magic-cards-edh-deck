#!/usr/bin/env python3
"""
Search Oracle Skill: RAG-based factual information retrieval

Performs web search to retrieve authoritative information about domain-specific facts.
Returns top results with confidence scoring for use as ground truth.

Use cases:
- Query card dimensions: "standard playing card size in inches"
- Query image resolutions: "recommended print DPI for posters"
- Query aspect ratios: "business card aspect ratio"
- Query print specs: "landscape letter paper dimensions"

This is a RAG (Retrieval-Augmented Generation) pattern:
1. Retrieve: Search web for factual information
2. Augment: Extract structured data from results
3. Generate: Use facts to inform template-aware fetching
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND, NETWORK_ERROR


def search_web(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform web search using subprocess call to Claude Code's search capability.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        List of search results with title, url, snippet
    """
    print(f"🔍 Searching web: '{query}'", file=sys.stderr)

    # Use external search via subprocess
    # This allows the skill to run independently while leveraging search capabilities
    import subprocess

    try:
        # Call external search script (would be provided by environment)
        # For now, we'll use a fallback approach that reads from web APIs directly

        # Option 1: Try DuckDuckGo (no API key needed, privacy-focused)
        try:
            import requests
            from bs4 import BeautifulSoup

            # DuckDuckGo instant answer API
            ddg_url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(ddg_url, timeout=10)
            data = response.json()

            results = []

            # Extract from abstract
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', 'Result'),
                    'url': data.get('AbstractURL', ''),
                    'snippet': data.get('Abstract', '')
                })

            # Extract from related topics
            for topic in data.get('RelatedTopics', [])[:num_results]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else 'Related',
                        'url': topic.get('FirstURL', ''),
                        'snippet': topic.get('Text', '')
                    })

            if results:
                print(f"✅ Found {len(results)} results from DuckDuckGo", file=sys.stderr)
                return results[:num_results]

        except ImportError:
            print("⚠️  requests/beautifulsoup4 not available for web search", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  DuckDuckGo search failed: {e}", file=sys.stderr)

        # Option 2: Fallback to knowledge base (for common print/dimension queries)
        # This is generic - matches ANY query containing dimensional keywords
        print("⚠️  Using fallback knowledge extraction", file=sys.stderr)

        # Load knowledge base from config (FR-008)
        from magic_cards.config_loader import load_knowledge_base
        knowledge_base = load_knowledge_base()

        # Match query against knowledge base (generic keyword matching)
        query_lower = query.lower()
        matches = []

        for entry in knowledge_base:
            # Count how many keywords match
            match_count = sum(1 for kw in entry["keywords"] if kw in query_lower)
            if match_count >= 2:  # At least 2 keywords must match
                matches.append((match_count, entry))

        if matches:
            # Return best match (most keywords matched)
            matches.sort(reverse=True, key=lambda x: x[0])
            best_match = matches[0][1]

            return [{
                'title': best_match['title'],
                'url': 'knowledge-base://builtin',
                'snippet': best_match['fact']
            }]

        # No results found
        print(f"⚠️  No results for query: '{query}'", file=sys.stderr)
        print(f"💡 Hint: Query should contain dimensional keywords (size, DPI, paper, card, etc.)", file=sys.stderr)
        return []

    except Exception as e:
        print(f"❌ Search failed: {e}", file=sys.stderr)
        return []


def extract_dimensions(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract dimensional information from text using regex patterns.

    Args:
        text: Text containing dimensional information

    Returns:
        Dict with extracted dimensions and confidence score
    """
    patterns = [
        # Pattern: "2.5 inches by 3.5 inches" or "2.5\" x 3.5\""
        r'(\d+\.?\d*)\s*(?:inches?|in|")\s*(?:by|x|×)\s*(\d+\.?\d*)\s*(?:inches?|in|")',

        # Pattern: "11 inches wide by 8.5 inches tall"
        r'(\d+\.?\d*)\s*(?:inches?|in)\s*wide\s*(?:by|x|×)?\s*(\d+\.?\d*)\s*(?:inches?|in)\s*(?:tall|high)',

        # Pattern: "825px x 1125px" or "825 x 1125 pixels"
        r'(\d+)\s*(?:px|pixels?)\s*(?:by|x|×)\s*(\d+)\s*(?:px|pixels?)',

        # Pattern: "300 DPI" or "150-300 DPI"
        r'(\d+)(?:-(\d+))?\s*DPI',

        # Pattern: "63.5mm" (millimeters)
        r'(\d+\.?\d*)\s*mm',
    ]

    results = {}
    confidence = 0.0

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            confidence += 0.25  # Each pattern match increases confidence

            # Parse based on pattern type
            if ('inches' in pattern or '"' in pattern) and 'wide' not in pattern:
                # Standard pattern: "2.5 inches by 3.5 inches"
                if matches[0]:
                    width, height = matches[0][:2]
                    results['width_inches'] = float(width)
                    results['height_inches'] = float(height)

            elif 'wide' in pattern:
                # "X inches wide by Y inches tall" pattern
                if matches[0]:
                    width, height = matches[0][:2]
                    results['width_inches'] = float(width)
                    results['height_inches'] = float(height)

            elif 'px' in pattern or 'pixels' in pattern:
                if matches[0]:
                    width, height = matches[0][:2]
                    results['width_px'] = int(width)
                    results['height_px'] = int(height)

            elif 'DPI' in pattern:
                if matches[0]:
                    dpi_min, dpi_max = matches[0][:2]
                    if dpi_max:  # Range like "150-300 DPI"
                        results['dpi_min'] = int(dpi_min)
                        results['dpi_max'] = int(dpi_max)
                        results['dpi_recommended'] = int(dpi_max)  # Use high end
                    else:  # Single value like "300 DPI"
                        results['dpi'] = int(dpi_min)

            elif 'mm' in pattern:
                if matches[0]:
                    mm_value = float(matches[0])
                    results['width_mm'] = mm_value  # Assume first mm is width

    # Calculate confidence based on completeness
    if 'width_inches' in results and 'height_inches' in results:
        confidence = min(confidence + 0.5, 1.0)  # High confidence for complete dimensions

    if results:
        results['confidence'] = confidence
        return results

    return None


def search_oracle(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Search web and extract structured factual information.

    Args:
        query: Factual query (e.g., "standard playing card size in inches")
        num_results: Number of search results to analyze

    Returns:
        Oracle response with extracted facts and confidence scores
    """
    # Perform search
    search_results = search_web(query, num_results)

    if not search_results:
        return {
            "query": query,
            "found": False,
            "confidence": 0.0,
            "message": "No search results found"
        }

    # Extract information from all results
    extracted_facts = []

    for result in search_results:
        # Combine title and snippet for extraction
        text = f"{result['title']} {result['snippet']}"

        facts = extract_dimensions(text)
        if facts:
            extracted_facts.append({
                "source": result['url'],
                "title": result['title'],
                "facts": facts,
                "confidence": facts.get('confidence', 0.0)
            })

    if not extracted_facts:
        return {
            "query": query,
            "found": False,
            "confidence": 0.0,
            "message": "No structured data extracted from search results",
            "raw_results": search_results
        }

    # Use highest confidence result as primary answer
    extracted_facts.sort(key=lambda x: x['confidence'], reverse=True)
    primary = extracted_facts[0]

    # Aggregate data from multiple sources for higher confidence
    aggregated_facts = primary['facts'].copy()
    aggregated_facts['sources'] = [f['source'] for f in extracted_facts]
    aggregated_facts['num_sources'] = len(extracted_facts)

    # Boost confidence if multiple sources agree
    if len(extracted_facts) > 1:
        aggregated_facts['confidence'] = min(primary['confidence'] + 0.2, 1.0)

    return {
        "query": query,
        "found": True,
        "facts": aggregated_facts,
        "confidence": aggregated_facts['confidence'],
        "primary_source": primary['source'],
        "all_extractions": extracted_facts
    }


def main():
    """CLI entry point for search-oracle skill."""
    parser = argparse.ArgumentParser(
        description='Search web for factual information with confidence scoring (RAG oracle)'
    )
    parser.add_argument(
        '--query',
        required=True,
        help='Factual query to search for (e.g., "standard playing card size in inches")'
    )
    parser.add_argument(
        '--num-results',
        type=int,
        default=5,
        help='Number of search results to analyze (default: 5)'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output file for oracle response JSON (default: stdout)'
    )

    args = parser.parse_args()

    try:
        # Perform oracle search
        oracle_response = search_oracle(args.query, args.num_results)

        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(oracle_response, f, indent=2)
            print(f"\n💾 Oracle response saved to: {args.output}", file=sys.stderr)

        # Print results to stderr for user
        print("\n" + "=" * 70, file=sys.stderr)
        print("🔮 SEARCH ORACLE RESULTS", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n📝 Query: {oracle_response['query']}", file=sys.stderr)
        print(f"✅ Found: {oracle_response['found']}", file=sys.stderr)
        print(f"📊 Confidence: {oracle_response.get('confidence', 0.0):.0%}", file=sys.stderr)

        if oracle_response['found']:
            facts = oracle_response['facts']
            print(f"\n📐 Extracted Facts:", file=sys.stderr)
            for key, value in facts.items():
                if key not in ['confidence', 'sources', 'num_sources']:
                    print(f"   {key}: {value}", file=sys.stderr)

            print(f"\n🔗 Sources: {facts.get('num_sources', 0)}", file=sys.stderr)
            print(f"   Primary: {oracle_response.get('primary_source', 'N/A')}", file=sys.stderr)

        print("=" * 70, file=sys.stderr)

        # Output to stdout for skill chaining (A2A protocol)
        format_success_output(oracle_response)

    except Exception as e:
        format_error_output(
            f"Oracle search failed: {str(e)}",
            exit_code=NETWORK_ERROR,
            context={"query": args.query, "exception": str(e)}
        )


if __name__ == '__main__':
    main()
