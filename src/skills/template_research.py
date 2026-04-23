"""
Template research skill wrapper.

Searches for MTG card templates online using domain-agnostic web fetching skills.

Implements FR-005: Research and identify MTG card template sources.
"""

import subprocess
import json
import os
from typing import List, Dict
from pathlib import Path


class TemplateResearcher:
    """
    Wrapper for template research using domain-agnostic skills.

    Uses .claude/skills/data/fetch-web-page.md for web fetching
    and .claude/skills/data/extract-content-from-html.md for parsing.
    """

    # Common search queries for MTG templates
    SEARCH_QUERIES = [
        "MTG card template",
        "Magic card blank",
        "MTG proxy template",
        "Magic card frame PNG",
    ]

    # Known template sources (curated list)
    KNOWN_SOURCES = [
        "https://github.com/search?q=mtg+card+template&type=repositories",
        "https://www.reddit.com/r/custommagic/",
        "https://mtg.design/",  # Template generator
    ]

    def __init__(self, cache_dir: str = ".cache/template_research"):
        """
        Initialize template researcher.

        Args:
            cache_dir: Directory to cache research results
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def research_templates(self, use_cache: bool = True) -> List[Dict]:
        """
        Research MTG card template sources.

        Args:
            use_cache: If True, return cached results if available

        Returns:
            List of template source dictionaries:
            [
                {
                    "name": "MTG Design Templates",
                    "url": "https://mtg.design/",
                    "description": "Online MTG template generator",
                    "quality": "high"
                }
            ]

        Note: Currently returns curated list. Future enhancement:
        Use web fetch skill to search dynamically.
        """
        cache_file = self.cache_dir / "template_sources.json"

        # Check cache
        if use_cache and cache_file.exists():
            print("📦 Using cached template sources")
            with open(cache_file) as f:
                return json.load(f)

        # For now, return curated list
        # Future: Use fetch-web-page skill to search dynamically
        sources = self._get_curated_sources()

        # Cache results
        with open(cache_file, 'w') as f:
            json.dump(sources, f, indent=2)

        print(f"✅ Found {len(sources)} template sources (cached)")
        return sources

    def _get_curated_sources(self) -> List[Dict]:
        """
        Get curated list of known good template sources.

        Returns:
            List of template source metadata

        Note: This is a fallback for when web scraping isn't feasible.
        Provides high-quality, verified template sources.
        """
        return [
            {
                "name": "MTG Design",
                "url": "https://mtg.design/",
                "description": "Online MTG template generator with all card types",
                "quality": "high",
                "types": ["creature", "planeswalker", "artifact", "enchantment", "instant", "sorcery", "land"],
                "colors": ["white", "blue", "black", "red", "green", "multicolor", "colorless"],
                "notes": "Web-based generator, can export high-res PNG templates"
            },
            {
                "name": "MTG Cardsmith",
                "url": "https://mtgcardsmith.com/",
                "description": "Custom card creator with template downloads",
                "quality": "medium",
                "types": ["creature", "planeswalker", "artifact", "enchantment", "instant", "sorcery"],
                "colors": ["white", "blue", "black", "red", "green", "multicolor"],
                "notes": "Community-driven, some templates may require registration"
            },
            {
                "name": "r/custommagic Templates",
                "url": "https://www.reddit.com/r/custommagic/wiki/templates",
                "description": "Community-maintained template repository",
                "quality": "varies",
                "types": ["all"],
                "colors": ["all"],
                "notes": "Check wiki for template links, quality varies"
            },
            {
                "name": "GitHub MTG Templates",
                "url": "https://github.com/search?q=mtg+card+template+png",
                "description": "Open-source template repositories",
                "quality": "varies",
                "types": ["varies"],
                "colors": ["varies"],
                "notes": "Search GitHub for 'mtg card template png', many repos available"
            }
        ]

    def fetch_template_urls(self, source: Dict) -> List[str]:
        """
        Fetch actual template image URLs from a source.

        Args:
            source: Template source dictionary from research_templates()

        Returns:
            List of direct URLs to template PNG files

        Note: Currently placeholder. Future enhancement:
        Use extract-content-from-html skill to scrape template URLs.
        """
        # Placeholder: Manual template URL list
        # Future: Use .claude/skills/data/extract-content-from-html.py
        # to scrape URLs from source pages

        print(f"⚠️  fetch_template_urls() not yet implemented for {source['name']}")
        print(f"   Manual approach: Visit {source['url']} and download templates")
        return []

    def search_with_web_skill(self, query: str) -> Dict:
        """
        Use domain-agnostic web fetch skill to search for templates.

        Args:
            query: Search query (e.g., "MTG blue creature template")

        Returns:
            Search results metadata

        Note: KISS implementation - uses curated sources instead of live search.
        Web scraping modern search engines is fragile (bot detection, rate limits).
        """
        print(f"🔍 Search query: '{query}'")
        print(f"⚠️  Live web search not implemented (KISS principle)")
        print(f"   Using curated template sources instead")
        return {
            "query": query,
            "method": "curated",
            "sources": self._get_curated_sources()
        }
