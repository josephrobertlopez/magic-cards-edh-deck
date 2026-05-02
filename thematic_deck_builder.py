#!/usr/bin/env python3
"""
Thematic EDH Deck Builder using Scryfall Tagger Community Tags

Constructs Magic: The Gathering EDH decks based on community artwork/card tags.
Supports theme-driven card selection with configurable tag weights and representation priorities.
"""

import json
import yaml
import requests
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TagTheme:
    """Configuration for a thematic deck build."""
    name: str
    description: str
    colors: List[str]
    tag_weights: Dict[str, float]
    min_relevance_threshold: float = 0.3
    min_lgbtq_cards: int = 0
    min_furry_cards: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'colors': self.colors,
            'tag_weights': self.tag_weights,
            'min_relevance_threshold': self.min_relevance_threshold,
            'min_lgbtq_cards': self.min_lgbtq_cards,
            'min_furry_cards': self.min_furry_cards,
        }


class ThematicDeckBuilder:
    """Builds thematic EDH decks using Scryfall Tagger community tags."""

    def __init__(self, tagger_api=None, scryfall_api=None):
        """Initialize deck builder with optional API clients."""
        self.tagger_api = tagger_api or self._init_tagger_api()
        self.scryfall_api = scryfall_api or self._init_scryfall_api()
        self.card_cache: Dict[str, Dict] = {}
        self.tag_cache: Dict[str, Optional[Dict]] = {}
        self.themes: Dict[str, Dict] = {}
        self.untagged_cards: List[str] = []

    def _init_tagger_api(self):
        """Initialize Scryfall Tagger API client."""
        try:
            from scryfall_tagger_api import ScryfallTaggerAPI
            return ScryfallTaggerAPI()
        except ImportError:
            logger.warning("ScryfallTaggerAPI not available, using stub")
            return None

    def _init_scryfall_api(self):
        """Initialize Scryfall API client."""
        return None  # Use requests directly

    @staticmethod
    def _extract_all_tag_names(tags_data):
        """Extract all tag names including ancestors from tag data."""
        if not tags_data:
            return []

        all_tags = set()

        # Add direct artwork tags
        for tag in tags_data.get('artwork_tags', []):
            all_tags.add(tag['name'])
            # Add ancestor tags
            for ancestor in tag.get('ancestor_tags', []):
                all_tags.add(ancestor['name'])

        # Add direct card tags
        for tag in tags_data.get('card_tags', []):
            all_tags.add(tag['name'])
            # Add ancestor tags
            for ancestor in tag.get('ancestor_tags', []):
                all_tags.add(ancestor['name'])

        return list(all_tags)

    def find_cards_by_tag(self, tag_name: str) -> List[Dict]:
        """Find cards with a specific tag, sorted by relevance."""
        logger.info(f"Searching for cards with tag: {tag_name}")

        # Search Scryfall for likely candidates
        candidates = self._search_scryfall_all()
        results = []

        for card in candidates[:150]:  # Limit search scope
            try:
                tags_data = self._fetch_card_tags(card['set'], card['collector_number'])
                tag_weight = self._calculate_tag_weight(tags_data, tag_name)

                if tag_weight > 0:
                    results.append({
                        'name': card['name'],
                        'set': card['set'],
                        'collector_number': card['collector_number'],
                        'tags': tags_data or {},
                        'tag_weight': tag_weight,
                        'type': card.get('type_line', ''),
                        'mana_cost': card.get('mana_cost', ''),
                        'cmc': card.get('cmc', 0),
                        'color_identity': card.get('color_identity', []),
                    })
                    time.sleep(0.05)  # Rate limiting
            except Exception as e:
                logger.debug(f"Failed to fetch tags for {card.get('name')}: {e}")

        # Sort by tag weight (descending)
        results.sort(key=lambda x: x['tag_weight'], reverse=True)
        logger.info(f"Found {len(results)} cards with tag '{tag_name}'")
        return results

    def find_cards_by_tags(self, tags: List[str], match_mode: str = "all") -> List[Dict]:
        """Find cards matching multiple tags with AND/OR logic."""
        logger.info(f"Searching for cards with tags: {tags}, mode: {match_mode}")

        if match_mode == "all":
            # AND logic - find cards with ALL tags
            candidates = self._search_scryfall_all()
            results = []

            for card in candidates[:200]:
                try:
                    tags_data = self._fetch_card_tags(card['set'], card['collector_number'])

                    # Check if card has all requested tags
                    card_tags = set()
                    if tags_data:
                        for tag_list in [tags_data.get('artwork_tags', []), tags_data.get('card_tags', [])]:
                            for tag in tag_list:
                                card_tags.add(tag['name'].lower())

                    query_tags = set(t.lower() for t in tags)
                    if query_tags.issubset(card_tags):
                        score = sum(self._calculate_tag_weight(tags_data, tag) for tag in tags)
                        results.append({
                            'name': card['name'],
                            'set': card['set'],
                            'collector_number': card['collector_number'],
                            'tags': tags_data or {},
                            'relevance_score': score,
                            'type': card.get('type_line', ''),
                            'mana_cost': card.get('mana_cost', ''),
                            'cmc': card.get('cmc', 0),
                            'color_identity': card.get('color_identity', []),
                        })
                        time.sleep(0.05)
                except Exception as e:
                    logger.debug(f"Failed processing {card.get('name')}: {e}")

            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results
        else:
            # OR logic - find cards with ANY tag
            all_results = {}
            for tag in tags:
                for card in self.find_cards_by_tag(tag):
                    if card['name'] not in all_results:
                        all_results[card['name']] = card
                    else:
                        all_results[card['name']]['relevance_score'] = \
                            all_results[card['name']].get('relevance_score', 0) + card['tag_weight']

            results = list(all_results.values())
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return results

    def _search_scryfall_all(self) -> List[Dict]:
        """Get a diverse set of cards from Scryfall for tag analysis."""
        url = "https://api.scryfall.com/cards/search"
        params = {
            "q": "-is:reserved",  # Exclude reserved list
            "order": "edhrec",
            "unique": "cards"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Scryfall search failed: {e}")
            return []

    def _fetch_card_tags(self, set_code: str, collector_number: str) -> Optional[Dict]:
        """Fetch card tags from Scryfall Tagger API."""
        cache_key = f"{set_code}_{collector_number}"
        if cache_key in self.tag_cache:
            return self.tag_cache[cache_key]

        if not self.tagger_api:
            return None

        try:
            result = self.tagger_api.fetch_card_tags(set_code, collector_number)
            if result:
                tag_info = self.tagger_api.extract_community_tags(result)
                self.tag_cache[cache_key] = tag_info
                time.sleep(0.1)  # Rate limiting
                return tag_info
            else:
                self.tag_cache[cache_key] = None
        except Exception as e:
            logger.debug(f"Failed to fetch tags for {set_code}/{collector_number}: {e}")
            self.tag_cache[cache_key] = None

        return None

    def _calculate_tag_weight(self, tags_data: Optional[Dict], tag_name: str) -> float:
        """Calculate weight for a specific tag on a card."""
        if not tags_data:
            return 0.0

        weight = 0.0
        tag_lower = tag_name.lower().replace(' ', '_')

        for tag_list in [tags_data.get('artwork_tags', []), tags_data.get('card_tags', [])]:
            for tag in tag_list:
                tag_check = tag['name'].lower().replace(' ', '_')
                if tag_check == tag_lower:
                    weight += tag.get('weight', 1.0)

        return weight

    def build_thematic_deck(self, theme: str, color_identity: List[str] = None,
                           tag_weights: Dict[str, float] = None,
                           allow_untagged: bool = True) -> List[Dict]:
        """Build a complete 100-card thematic EDH deck."""
        logger.info(f"Building deck for theme: {theme}, colors: {color_identity}")

        # Load theme configuration
        theme_configs = self.load_theme_config("tag_themes.yaml")
        theme_config = theme_configs.get(theme)
        if not theme_config:
            logger.warning(f"Theme {theme} not found, using defaults")
            theme_config = {'colors': color_identity or ['R', 'W'], 'tag_weights': {}}

        # Resolve color identity
        if not color_identity:
            color_identity = theme_config.get('colors', ['R', 'W'])

        # Resolve tag weights
        if not tag_weights:
            tag_weights = theme_config.get('tag_weights', {})

        deck = []
        selected_names = set()
        rep_count = {'lgbtq': 0, 'furry': 0}

        # Step 1: Find and add commander
        commander = self._select_commander(theme, color_identity, tag_weights)
        if commander:
            deck.append(commander)
            selected_names.add(commander['name'])
            logger.info(f"Commander: {commander['name']}")

        # Step 2: Build rest of deck
        candidates = self._get_thematic_candidates(color_identity, tag_weights, allow_untagged)

        for card in candidates:
            if len(deck) >= 100:
                break

            # Skip if already selected
            if card['name'] in selected_names:
                continue

            # Singleton rule: only basic lands can repeat
            if 'Land' not in card.get('type', ''):
                if card['name'] in selected_names:
                    continue

            deck.append(card)
            selected_names.add(card['name'])

            # Track representation
            tags_found = card.get('tags_found', [])
            if any(t in ['achillean', 'trans male', 'romantic couple'] for t in tags_found):
                rep_count['lgbtq'] += 1
            if any(t in ['bear', 'cat', 'wolf', 'anthropomorphic', 'furry'] for t in tags_found):
                rep_count['furry'] += 1

        # Step 3: Fill with lands if needed
        if len(deck) < 100:
            lands_needed = 100 - len(deck)
            deck.extend(self._generate_basic_lands(color_identity, lands_needed))

        logger.info(f"Deck complete: {len(deck)} cards | LGBTQ+: {rep_count['lgbtq']} | Furry: {rep_count['furry']}")

        return deck[:100]

    def _select_commander(self, theme: str, colors: List[str],
                         tag_weights: Dict[str, float]) -> Optional[Dict]:
        """Find and select a thematic commander."""
        logger.info(f"Searching for commander with colors: {colors}")

        commanders = self._find_commanders(colors, tag_weights)
        if commanders:
            return commanders[0]
        return None

    def _find_commanders(self, colors: List[str], tag_weights: Dict[str, float]) -> List[Dict]:
        """Find legendary creatures in specified colors."""
        color_str = ''.join(colors)
        url = "https://api.scryfall.com/cards/search"
        params = {
            "q": f"type:legendary type:creature color<={color_str}",
            "order": "edhrec"
        }

        commanders = []
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            for card in data.get('data', [])[:50]:
                try:
                    tags = self._fetch_card_tags(card['set'], card['collector_number'])
                    score = self._score_card_by_tags(tags, tag_weights)

                    commanders.append({
                        'name': card['name'],
                        'set': card['set'],
                        'collector_number': card['collector_number'],
                        'type': card.get('type_line', ''),
                        'mana_cost': card.get('mana_cost', ''),
                        'cmc': card.get('cmc', 0),
                        'color_identity': colors,
                        'tags': tags or {},
                        'thematic_score': score,
                        'is_legendary': True,
                        'tags_found': self._extract_all_tag_names(tags),
                    })
                    time.sleep(0.05)
                except Exception as e:
                    logger.debug(f"Error processing commander {card.get('name')}: {e}")

            commanders.sort(key=lambda x: x['thematic_score'], reverse=True)
            return commanders
        except Exception as e:
            logger.error(f"Commander search failed: {e}")
            return []

    def _get_thematic_candidates(self, colors: List[str],
                                tag_weights: Dict[str, float],
                                allow_untagged: bool) -> List[Dict]:
        """Get candidate cards for deck building, scored by theme relevance."""
        color_str = ''.join(colors)
        url = "https://api.scryfall.com/cards/search"
        params = {
            "q": f"color<={color_str} -is:reserved",
            "order": "edhrec"
        }

        candidates = []
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            for card in data.get('data', [])[:250]:
                try:
                    tags = self._fetch_card_tags(card['set'], card['collector_number'])
                    score = self._score_card_by_tags(tags, tag_weights)

                    if score > 0 or allow_untagged:
                        candidate = {
                            'name': card['name'],
                            'set': card['set'],
                            'collector_number': card['collector_number'],
                            'type': card.get('type_line', ''),
                            'mana_cost': card.get('mana_cost', ''),
                            'cmc': card.get('cmc', 0),
                            'color_identity': card.get('color_identity', []),
                            'tags': tags or {},
                            'thematic_score': score,
                            'tags_found': self._extract_all_tag_names(tags),
                        }
                        candidates.append(candidate)
                        if not tags:
                            self.untagged_cards.append(card['name'])
                        time.sleep(0.05)
                except Exception as e:
                    logger.debug(f"Error processing candidate {card.get('name')}: {e}")

            candidates.sort(key=lambda x: x['thematic_score'], reverse=True)
            return candidates
        except Exception as e:
            logger.error(f"Candidate search failed: {e}")
            return []

    def _score_card_by_tags(self, tags_data: Optional[Dict],
                            tag_weights: Dict[str, float]) -> float:
        """Calculate thematic relevance score for a card."""
        if not tags_data or not tag_weights:
            return 0.0

        score = 0.0
        card_tags_list = tags_data.get('artwork_tags', []) + tags_data.get('card_tags', [])

        for tag in card_tags_list:
            tag_name = tag['name'].lower().replace(' ', '_')
            for weight_name, weight_value in tag_weights.items():
                weight_check = weight_name.lower().replace(' ', '_')
                if tag_name == weight_check:
                    score += weight_value * tag.get('weight', 1.0)

        return score

    def find_commander(self, deck: List[Dict]) -> Optional[Dict]:
        """Find a legal EDH commander in the deck."""
        for card in deck:
            if 'Legendary Creature' in card.get('type', ''):
                return card
        return deck[0] if deck else None

    def export_decklist_with_tags(self, deck: List[Dict]) -> str:
        """Export deck as decklist with tag annotations."""
        lines = []
        card_counts = defaultdict(int)
        card_tags_map = {}

        # Count cards and collect tag info
        for card in deck:
            name = card['name']
            card_counts[name] += 1
            if name not in card_tags_map:
                tags = card.get('tags_found', [])[:3]  # Limit to 3 tags
                card_tags_map[name] = tags

        # Build decklist lines
        for name, count in sorted(card_counts.items()):
            tags = card_tags_map.get(name, [])
            tag_str = ""
            if tags:
                tag_str = " [" + ", ".join(tags) + "]"
            lines.append(f"{count} {name}{tag_str}")

        return "\n".join(lines)

    def load_theme_config(self, yaml_path: str) -> Dict[str, Dict]:
        """Load theme configurations from YAML file."""
        try:
            if not Path(yaml_path).exists():
                logger.warning(f"Config file not found: {yaml_path}")
                return {}

            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('themes', {})
        except Exception as e:
            logger.error(f"Failed to load theme config: {e}")
            return {}

    def _generate_basic_lands(self, colors: List[str], count: int) -> List[Dict]:
        """Generate basic land cards to fill out deck."""
        land_names = {
            'W': 'Plains',
            'U': 'Island',
            'B': 'Swamp',
            'R': 'Mountain',
            'G': 'Forest',
        }

        lands = []
        for i in range(count):
            color = colors[i % len(colors)]
            lands.append({
                'name': land_names.get(color, 'Plains'),
                'type': 'Basic Land',
                'mana_cost': '',
                'cmc': 0,
                'color_identity': [color],
                'tags': {},
                'thematic_score': 0,
                'tags_found': [],
            })

        return lands


class DeckValidator:
    """Validates EDH deck format compliance."""

    def validate_deck(self, deck: List[Dict]) -> Dict:
        """Validate a complete deck."""
        violations = []

        # Check card count
        card_count = len(deck)
        if card_count != 100:
            violations.append(f"Wrong card count: {card_count} (expected 100)")

        # Check singleton rule
        card_names = [c['name'] for c in deck]
        non_land_names = [n for n in card_names if 'Land' not in next((c for c in deck if c['name'] == n), {}).get('type', '')]
        if len(non_land_names) != len(set(non_land_names)):
            violations.append("Singleton rule violated (non-basic lands repeated)")

        return {
            'card_count': card_count,
            'is_singleton': len(non_land_names) == len(set(non_land_names)),
            'color_identity_valid': True,
            'edh_legal': len(violations) == 0,
            'violations': violations,
        }

    def validate_color_identity(self, deck: List[Dict], colors: List[str]) -> bool:
        """Validate all cards match the color identity."""
        return all(self._card_matches_colors(card, colors) for card in deck)

    def validate_edh_legality(self, card: Dict) -> bool:
        """Check if a card is legal in EDH format."""
        # Simplified check - in reality would need comprehensive ban list
        return True

    def _card_matches_colors(self, card: Dict, colors: List[str]) -> bool:
        """Check if card's color identity is subset of allowed colors."""
        card_colors = set(card.get('color_identity', []))
        allowed_colors = set(colors)
        return card_colors.issubset(allowed_colors)


class ThemeSuggester:
    """Suggests commanders and deck themes."""

    def suggest_commanders(self, theme: str, colors: str) -> List[Dict]:
        """Suggest commanders for a theme."""
        builder = ThematicDeckBuilder()

        # Map color names to codes
        color_map = {
            'Boros': ['R', 'W'],
            'Grixis': ['U', 'B', 'R'],
            'Abzan': ['W', 'B', 'G'],
            'Temur': ['U', 'R', 'G'],
            'Sultai': ['U', 'B', 'G'],
        }
        color_list = color_map.get(colors, [])
        tag_weights = {}  # Default empty weights

        commanders = builder._find_commanders(color_list, tag_weights)

        return [{
            'name': cmd['name'],
            'tags_matched': cmd.get('tags_found', []),
            'thematic_score': cmd.get('thematic_score', 0),
            'is_legendary': True,
            'reason': f"Legendary {cmd['type'].replace('Legendary Creature ', '')}",
        } for cmd in commanders[:3]]
