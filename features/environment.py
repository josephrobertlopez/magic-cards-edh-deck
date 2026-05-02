"""
Behave test environment setup with mock data for testing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def before_feature(context, feature):
    """Setup before each feature."""
    context.test_data = {
        'sample_cards': [
            {
                'name': 'Ajani, Adversary of Tyrants',
                'set': 'm19',
                'collector_number': '3',
                'type': 'Legendary Planeswalker — Ajani',
                'mana_cost': '{1}{W}{W}',
                'cmc': 3,
                'color_identity': ['W'],
                'tags': {},
                'tags_found': ['achillean', 'smile'],
            },
            {
                'name': 'Mountain',
                'set': 'ltr',
                'collector_number': '278',
                'type': 'Basic Land — Mountain',
                'mana_cost': '',
                'cmc': 0,
                'color_identity': ['R'],
                'tags': {},
                'tags_found': [],
            },
            {
                'name': 'Plains',
                'set': 'ltr',
                'collector_number': '277',
                'type': 'Basic Land — Plains',
                'mana_cost': '',
                'cmc': 0,
                'color_identity': ['W'],
                'tags': {},
                'tags_found': [],
            },
        ]
    }
