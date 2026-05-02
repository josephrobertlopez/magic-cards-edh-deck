#!/usr/bin/env python3
"""
MTG Card Design Bias Detection using Hiring Bias POC algorithms.

Adapts hiring bias detection to analyze systematic bias in card design
based on demographic representation in artwork/lore.

Production-ready module with:
- Division by zero protection
- Custom representation profiles
- JSON/CSV export engines
- Recommendation engine for inclusive deck building
"""

import pandas as pd
import numpy as np
import re
import json
import csv
import time
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
from io import StringIO


@dataclass(frozen=True)
class RepresentationProfile:
    """A custom representation profile with tags and metadata."""
    name: str
    tags: List[str]
    description: str = ""
    color: str = ""  # For visualization


@dataclass
class CardBiasResult:
    """Result of card design bias analysis."""
    representation_group: str
    metric_name: str
    point_estimate: float
    confidence_interval: Tuple[float, float]
    group_stats: Dict[str, Any]
    cards_analyzed: int


class CardProcessor:
    """Process MTG card oracle text to extract mechanical features.

    Adapted from hiring bias POC ResumeProcessor.
    """

    def __init__(self):
        # MTG mechanical vocabulary (similar to tech skills in hiring bias)
        self.mechanics = [
            # Core abilities
            "flying", "trample", "lifelink", "vigilance", "haste", "hexproof",
            "deathtouch", "first strike", "double strike", "flash", "menace",
            "reach", "indestructible", "ward", "protection", "shroud",

            # Card advantage
            "draw", "scry", "surveil", "mill", "search", "tutor", "cascade",
            "discover", "explore", "investigate", "manifest", "foretell",

            # Resource mechanics
            "mana", "treasure", "energy", "experience", "loyalty", "charge",
            "poison", "food", "clue", "blood", "gold", "powerstone",

            # Removal & interaction
            "destroy", "exile", "sacrifice", "counter", "tap", "untap",
            "bounce", "return", "discard", "mill", "burn", "deal damage",

            # Tribal/creature mechanics
            "changeling", "evolve", "adapt", "monstrosity", "bloodthirst",
            "devour", "undying", "persist", "unleash", "battalion", "pack tactics",

            # Artifact/enchantment mechanics
            "equipment", "vehicle", "fortification", "aura", "saga", "class",
            "planeswalker", "legendary", "historic", "artifact", "enchantment",

            # Advanced mechanics
            "convoke", "delve", "emerge", "madness", "flashback", "retrace",
            "storm", "split second", "suspend", "rebound", "cipher", "overload",

            # Mana mechanics
            "kicker", "multikicker", "escalate", "strive", "replicate", "buyback",
            "echo", "cumulative upkeep", "morph", "megamorph", "transform",

            # Timing mechanics
            "instant", "sorcery", "activated ability", "triggered ability",
            "enter", "leave", "dies", "attack", "block", "end step", "upkeep"
        ]

        # Power level indicators
        self.power_indicators = {
            "high": ["destroy", "exile", "counter", "draw", "search", "extra turn", "infinite"],
            "medium": ["damage", "tap", "return", "discard", "sacrifice"],
            "low": ["scry", "gain life", "+1/+1", "vigilance", "reach"]
        }

    def extract_mechanics(self, oracle_text: str) -> List[str]:
        """Extract mechanics from card oracle text."""
        if not oracle_text:
            return []

        text = oracle_text.lower()
        found_mechanics = []

        for mechanic in self.mechanics:
            if mechanic in text:
                found_mechanics.append(mechanic)

        return found_mechanics

    def calculate_complexity_score(self, oracle_text: str) -> float:
        """Calculate design complexity score based on oracle text."""
        if not oracle_text:
            return 0.0

        # Word count
        word_count = len(oracle_text.split())

        # Number of abilities (rough heuristic)
        ability_count = oracle_text.count(',') + oracle_text.count('.') + oracle_text.count(':')

        # Keywords that indicate complexity
        complex_keywords = ['when', 'whenever', 'if', 'instead', 'unless', 'choose', 'may']
        complexity_keywords = sum(1 for keyword in complex_keywords if keyword in oracle_text.lower())

        # Normalize to 0-10 scale
        complexity = (word_count * 0.1) + (ability_count * 0.5) + (complexity_keywords * 1.0)
        return min(complexity, 10.0)

    def calculate_power_score(self, oracle_text: str, mana_cost: str = "",
                            power: str = "", toughness: str = "") -> float:
        """Calculate power level score."""
        score = 0.0

        if not oracle_text:
            return score

        text = oracle_text.lower()

        # Check for high-power indicators
        for indicator in self.power_indicators["high"]:
            if indicator in text:
                score += 3.0

        for indicator in self.power_indicators["medium"]:
            if indicator in text:
                score += 1.5

        for indicator in self.power_indicators["low"]:
            if indicator in text:
                score += 0.5

        # Factor in mana cost efficiency
        try:
            if mana_cost and '{' in mana_cost:
                cmc = len(re.findall(r'\{[^}]+\}', mana_cost))
                if cmc > 0:
                    score = score / max(cmc, 1) * 2  # Efficiency bonus for low cost
        except:
            pass

        return min(score, 10.0)


class MTGBiasDetector:
    """Detect design bias in MTG cards based on representation groups.

    Uses fairness metrics from hiring bias POC to analyze whether cards
    depicting certain demographic groups are systematically designed differently.
    """

    def __init__(self, random_state: int = None, n_bootstrap: int = 1000):
        self.random_state = np.random.RandomState(random_state) if random_state else np.random.RandomState()
        self.n_bootstrap = n_bootstrap
        self.processor = CardProcessor()

        # Define default representation groups based on Scryfall Tagger tags
        self.representation_groups = {
            'lgbtq_plus': ['achillean', 'trans male', 'trans female', 'romantic couple',
                          'lgbtq', 'queer', 'sapphic', 'nonbinary', 'transgender'],
            'person_of_color': ['person of color', 'black person', 'asian person',
                              'indigenous person', 'latinx person'],
            'anthropomorphic': ['anthropomorphic', 'furry', 'animal people', 'beast',
                              'cat', 'bear', 'wolf', 'minotaur', 'leonin'],
            'body_diversity': ['musclegut', 'bear (body type)', 'plus size', 'fat',
                             'thin', 'muscular', 'overweight'],
            'gender_diverse': ['male', 'female', 'nonbinary', 'androgynous', 'masculine',
                             'feminine', 'trans male', 'trans female'],
            # Built-in "furry gay male uwu" profile
            'furry_gay_uwu': ['anthropomorphic', 'achillean', 'lgbtq', 'bear (body type)',
                            'furry', 'sapphic', 'nonbinary']
        }

    def add_representation_profile(self, profile: RepresentationProfile) -> None:
        """Add a custom representation profile."""
        self.representation_groups[profile.name] = profile.tags

    def collect_card_data(self, card_names: List[str]) -> pd.DataFrame:
        """Collect comprehensive data for bias analysis.

        NOTE: This is a stub for integration with actual Scryfall/tagging APIs.
        Use collect_card_data_mock for testing.
        """
        # Import these at runtime to avoid circular dependencies
        from generate_deck import fetch_card_from_scryfall
        from analyze_tags import analyze_card_batch

        print(f"🎯 Collecting data for {len(card_names)} cards...")

        cards_data = []

        for i, card_name in enumerate(card_names):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(card_names)}")

            try:
                # Get Scryfall data
                scryfall_data = fetch_card_from_scryfall(card_name)
                if not scryfall_data:
                    continue

                # Get tag data
                tag_result = analyze_card_batch([card_name])
                if not tag_result:
                    continue

                tag_data = tag_result[0]

                # Extract oracle text
                oracle_text = scryfall_data.get('oracle_text', '')

                # Calculate metrics
                mechanics = self.processor.extract_mechanics(oracle_text)
                complexity = self.processor.calculate_complexity_score(oracle_text)
                power_score = self.processor.calculate_power_score(
                    oracle_text,
                    scryfall_data.get('mana_cost', ''),
                    scryfall_data.get('power', ''),
                    scryfall_data.get('toughness', '')
                )

                # Determine representation groups
                all_tags = (tag_data['tags'].get('artwork', []) +
                           tag_data['tags'].get('card', []) +
                           tag_data['tags'].get('inherited_artwork', []) +
                           tag_data['tags'].get('inherited_card', []))

                card_info = {
                    'name': card_name,
                    'oracle_text': oracle_text,
                    'mana_cost': scryfall_data.get('mana_cost', ''),
                    'cmc': scryfall_data.get('cmc', 0),
                    'type_line': scryfall_data.get('type_line', ''),
                    'power': scryfall_data.get('power', ''),
                    'toughness': scryfall_data.get('toughness', ''),
                    'rarity': scryfall_data.get('rarity', ''),
                    'set': scryfall_data.get('set', ''),
                    'mechanics': mechanics,
                    'complexity_score': complexity,
                    'power_score': power_score,
                    'all_tags': all_tags
                }

                # Add representation group flags
                for group_name, group_tags in self.representation_groups.items():
                    card_info[f'is_{group_name}'] = any(tag in group_tags for tag in all_tags)

                cards_data.append(card_info)

            except Exception as e:
                print(f"  ⚠️ Error processing {card_name}: {e}")

            time.sleep(0.1)  # Rate limiting

        df = pd.DataFrame(cards_data)
        print(f"✅ Collected data for {len(df)} cards")
        return df

    def collect_card_data_mock(self, card_names: List[str],
                              mock_scryfall: Dict[str, Any],
                              mock_tags: Dict[str, Any]) -> pd.DataFrame:
        """Collect card data using mock data (for testing)."""
        print(f"🎯 Collecting mock data for {len(card_names)} cards...")

        cards_data = []

        for card_name in card_names:
            if card_name not in mock_scryfall or card_name not in mock_tags:
                continue

            scryfall_data = mock_scryfall[card_name]
            tag_data = mock_tags[card_name]

            oracle_text = scryfall_data.get('oracle_text', '')

            # Calculate metrics
            mechanics = self.processor.extract_mechanics(oracle_text)
            complexity = self.processor.calculate_complexity_score(oracle_text)
            power_score = self.processor.calculate_power_score(
                oracle_text,
                scryfall_data.get('mana_cost', ''),
                scryfall_data.get('power', ''),
                scryfall_data.get('toughness', '')
            )

            # Get all tags
            all_tags = (tag_data['tags'].get('artwork', []) +
                       tag_data['tags'].get('card', []) +
                       tag_data['tags'].get('inherited_artwork', []) +
                       tag_data['tags'].get('inherited_card', []))

            card_info = {
                'name': card_name,
                'oracle_text': oracle_text,
                'mana_cost': scryfall_data.get('mana_cost', ''),
                'cmc': scryfall_data.get('cmc', 0),
                'type_line': scryfall_data.get('type_line', ''),
                'power': scryfall_data.get('power', ''),
                'toughness': scryfall_data.get('toughness', ''),
                'rarity': scryfall_data.get('rarity', ''),
                'set': scryfall_data.get('set', ''),
                'mechanics': mechanics,
                'complexity_score': complexity,
                'power_score': power_score,
                'all_tags': all_tags
            }

            # Add representation group flags
            for group_name, group_tags in self.representation_groups.items():
                card_info[f'is_{group_name}'] = any(tag in group_tags for tag in all_tags)

            cards_data.append(card_info)

        df = pd.DataFrame(cards_data)
        print(f"✅ Collected mock data for {len(df)} cards")
        return df

    def analyze_representation_bias(self, df: pd.DataFrame,
                                  outcome_metric: str = 'power_score') -> List[CardBiasResult]:
        """Analyze bias across representation groups.

        Includes protection against division by zero.
        """
        results = []

        print(f"\n📊 REPRESENTATION BIAS ANALYSIS")
        print("=" * 50)

        for group_name in self.representation_groups.keys():
            group_col = f'is_{group_name}'
            if group_col not in df.columns:
                continue

            # Get group membership
            group_mask = df[group_col] == True
            control_mask = df[group_col] == False

            if group_mask.sum() < 5 or control_mask.sum() < 5:
                print(f"⚠️ {group_name}: Too few samples ({group_mask.sum()}/{control_mask.sum()})")
                continue

            # Calculate group statistics
            group_values = df[group_mask][outcome_metric]
            control_values = df[control_mask][outcome_metric]

            group_mean = group_values.mean()
            control_mean = control_values.mean()

            # Calculate disparate impact ratio with DIVISION BY ZERO PROTECTION
            # DI = min(group_rate, control_rate) / max(group_rate, control_rate)
            if group_mean == 0.0 and control_mean == 0.0:
                # Both zero - equal performance
                di_ratio = 1.0
            elif group_mean == 0.0 or control_mean == 0.0:
                # One is zero - only count the non-zero
                di_ratio = min(group_mean, control_mean) / max(group_mean, control_mean) if max(group_mean, control_mean) > 0 else 1.0
            else:
                # Normal case
                di_ratio = min(group_mean, control_mean) / max(group_mean, control_mean)

            # Bootstrap confidence interval
            bootstrap_dis = []
            for _ in range(self.n_bootstrap):
                boot_group = self.random_state.choice(group_values, size=len(group_values), replace=True)
                boot_control = self.random_state.choice(control_values, size=len(control_values), replace=True)

                boot_group_mean = boot_group.mean()
                boot_control_mean = boot_control.mean()

                # Apply same zero protection to bootstrap
                if boot_group_mean == 0.0 and boot_control_mean == 0.0:
                    boot_di = 1.0
                elif boot_group_mean == 0.0 or boot_control_mean == 0.0:
                    boot_di = min(boot_group_mean, boot_control_mean) / max(boot_group_mean, boot_control_mean) if max(boot_group_mean, boot_control_mean) > 0 else 1.0
                else:
                    boot_di = min(boot_group_mean, boot_control_mean) / max(boot_group_mean, boot_control_mean)

                bootstrap_dis.append(boot_di)

            ci_lower = np.percentile(bootstrap_dis, 2.5)
            ci_upper = np.percentile(bootstrap_dis, 97.5)

            # Calculate effect size with protection
            denominator = np.sqrt(((group_values.std()**2 + control_values.std()**2) / 2))
            if denominator > 0:
                effect_size = (group_mean - control_mean) / denominator
            else:
                effect_size = 0.0

            result = CardBiasResult(
                representation_group=group_name,
                metric_name=f"disparate_impact_{outcome_metric}",
                point_estimate=di_ratio,
                confidence_interval=(ci_lower, ci_upper),
                group_stats={
                    'group_mean': float(group_mean),
                    'control_mean': float(control_mean),
                    'group_count': int(group_mask.sum()),
                    'control_count': int(control_mask.sum()),
                    'effect_size': float(effect_size)
                },
                cards_analyzed=len(df)
            )

            results.append(result)

            # Report findings
            print(f"\n🏳️‍🌈 {group_name.upper()} BIAS ANALYSIS:")
            print(f"  Disparate Impact Ratio: {di_ratio:.3f} (95% CI: {ci_lower:.3f}-{ci_upper:.3f})")
            print(f"  Group mean {outcome_metric}: {group_mean:.2f} (n={group_mask.sum()})")
            print(f"  Control mean {outcome_metric}: {control_mean:.2f} (n={control_mask.sum()})")
            print(f"  Effect size: {effect_size:.3f}")

            # Flag potential bias (using EEOC 4/5ths rule)
            if di_ratio < 0.8:
                print(f"  🚨 POTENTIAL BIAS DETECTED: DI < 0.8 threshold")
            elif di_ratio > 1.25:
                print(f"  📈 Potential favorable bias: DI > 1.25")
            else:
                print(f"  ✅ No systematic bias detected")

        return results

    def detailed_mechanic_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze mechanical differences across representation groups."""
        print(f"\n🔧 MECHANICAL DESIGN ANALYSIS")
        print("=" * 40)

        mechanic_analysis = {}

        for group_name in self.representation_groups.keys():
            group_col = f'is_{group_name}'
            if group_col not in df.columns:
                continue

            group_cards = df[df[group_col] == True]
            control_cards = df[df[group_col] == False]

            if len(group_cards) < 5:
                continue

            # Aggregate mechanics
            group_mechanics = [m for mechanics_list in group_cards['mechanics'] for m in mechanics_list]
            control_mechanics = [m for mechanics_list in control_cards['mechanics'] for m in mechanics_list]

            group_mechanic_freq = Counter(group_mechanics)
            control_mechanic_freq = Counter(control_mechanics)

            # Find over/under-represented mechanics
            group_total = len(group_mechanics) or 1
            control_total = len(control_mechanics) or 1

            mechanic_diffs = {}
            all_mechanics = set(group_mechanic_freq.keys()) | set(control_mechanic_freq.keys())

            for mechanic in all_mechanics:
                group_rate = group_mechanic_freq.get(mechanic, 0) / group_total
                control_rate = control_mechanic_freq.get(mechanic, 0) / control_total

                if control_rate > 0:
                    ratio = group_rate / control_rate
                    mechanic_diffs[mechanic] = {
                        'group_rate': group_rate,
                        'control_rate': control_rate,
                        'ratio': ratio
                    }

            # Find most biased mechanics
            significant_diffs = {k: v for k, v in mechanic_diffs.items()
                               if v['ratio'] > 1.5 or v['ratio'] < 0.67}

            mechanic_analysis[group_name] = {
                'total_cards': len(group_cards),
                'avg_mechanics_per_card': len(group_mechanics) / len(group_cards),
                'significant_differences': significant_diffs
            }

            print(f"\n{group_name.upper()}:")
            print(f"  Cards: {len(group_cards)}, Avg mechanics/card: {len(group_mechanics) / len(group_cards):.1f}")

            if significant_diffs:
                print("  Mechanic bias:")
                for mechanic, diff in sorted(significant_diffs.items(),
                                           key=lambda x: abs(x[1]['ratio'] - 1.0), reverse=True)[:5]:
                    if diff['ratio'] > 1:
                        print(f"    Over-represented: {mechanic} ({diff['ratio']:.1f}x more common)")
                    else:
                        print(f"    Under-represented: {mechanic} ({1/diff['ratio']:.1f}x less common)")

        return mechanic_analysis


class ExportEngine:
    """Export bias analysis results in multiple formats."""

    def __init__(self, detector: MTGBiasDetector):
        self.detector = detector
        self.timestamp = datetime.now().isoformat()

    def export_to_json(self, results: List[CardBiasResult],
                      mechanic_analysis: Dict[str, Any],
                      df: pd.DataFrame) -> str:
        """Export results to JSON string."""
        output_data = {
            'timestamp': self.timestamp,
            'bias_results': [
                {
                    'group': r.representation_group,
                    'metric': r.metric_name,
                    'disparate_impact': float(r.point_estimate),
                    'confidence_interval': [float(r.confidence_interval[0]), float(r.confidence_interval[1])],
                    'group_stats': r.group_stats
                } for r in results
            ],
            'mechanic_analysis': {
                k: {
                    'total_cards': v['total_cards'],
                    'avg_mechanics_per_card': float(v['avg_mechanics_per_card']),
                    'significant_differences': {
                        mk: {
                            'group_rate': float(mv['group_rate']),
                            'control_rate': float(mv['control_rate']),
                            'ratio': float(mv['ratio'])
                        }
                        for mk, mv in v['significant_differences'].items()
                    }
                }
                for k, v in mechanic_analysis.items()
            },
            'dataset_summary': {
                'total_cards': len(df),
                'cards_by_group': {group: int(df[f'is_{group}'].sum())
                                 for group in self.detector.representation_groups.keys()
                                 if f'is_{group}' in df.columns}
            }
        }

        return json.dumps(output_data, indent=2)

    def export_to_csv(self, results: List[CardBiasResult]) -> str:
        """Export results to CSV string."""
        output = StringIO()
        fieldnames = [
            'representation_group',
            'metric',
            'disparate_impact',
            'ci_lower',
            'ci_upper',
            'group_mean',
            'control_mean',
            'group_count',
            'control_count',
            'effect_size'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow({
                'representation_group': result.representation_group,
                'metric': result.metric_name,
                'disparate_impact': f"{result.point_estimate:.4f}",
                'ci_lower': f"{result.confidence_interval[0]:.4f}",
                'ci_upper': f"{result.confidence_interval[1]:.4f}",
                'group_mean': f"{result.group_stats['group_mean']:.4f}",
                'control_mean': f"{result.group_stats['control_mean']:.4f}",
                'group_count': result.group_stats['group_count'],
                'control_count': result.group_stats['control_count'],
                'effect_size': f"{result.group_stats['effect_size']:.4f}"
            })

        return output.getvalue()


class RecommendationEngine:
    """Generate deck recommendations based on bias analysis."""

    def __init__(self):
        pass

    def generate_recommendations(self, df: pd.DataFrame,
                                analysis_finding: str = None) -> List[Dict[str, Any]]:
        """Generate upgrade recommendations to address identified bias.

        Args:
            df: DataFrame with card data and representation tags
            analysis_finding: Type of bias finding (e.g., 'lgbtq_plus_low_power')

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        if analysis_finding == "lgbtq_plus_low_power":
            # Find LGBTQ+ cards with high power scores as upgrades
            lgbtq_high_power = df[(df['is_lgbtq_plus'] == True) & (df['power_score'] > 7.0)]

            for _, card in lgbtq_high_power.iterrows():
                recommendations.append({
                    'card_name': card.get('name', ''),
                    'reason': 'High-power LGBTQ+ representation - addresses design bias',
                    'power_score': card.get('power_score', 0),
                    'representation_group': 'lgbtq_plus'
                })

        return recommendations


def main():
    """Run MTG card bias analysis."""
    print("🎯 MTG CARD DESIGN BIAS ANALYSIS")
    print("Using hiring bias detection algorithms on card oracle text")
    print("=" * 60)

    # Sample card list (user can customize)
    sample_cards = [
        # Known diverse representation cards
        "Bearscape", "Ajani, Caller of the Pride", "Alesha, Who Smiles at Death",
        "Ashiok, Nightmare Weaver", "Firesong and Sunspeaker", "Hallar, the Firefletcher",
        "Kynaios and Tiro of Meletis", "Narset, Parter of Veils", "Aminatou, the Fateshifter",
        "Ral Zarek", "Chandra, Torch of Defiance", "Vraska, Swarm's Eminence",
        # Control group - iconic cards
        "Lightning Bolt", "Counterspell", "Serra Angel", "Shivan Dragon",
        "Wrath of God", "Ancestral Recall", "Black Lotus", "Mox Sapphire",
        "Sol Ring", "Command Tower", "Path to Exile", "Swords to Plowshares"
    ]

    detector = MTGBiasDetector(random_state=42)

    # Collect data
    df = detector.collect_card_data(sample_cards)

    if len(df) < 10:
        print("❌ Insufficient data for bias analysis")
        return

    # Run bias analysis on multiple metrics
    metrics = ['power_score', 'complexity_score', 'cmc']

    all_results = []
    for metric in metrics:
        if metric in df.columns:
            print(f"\n📊 Analyzing bias in: {metric}")
            results = detector.analyze_representation_bias(df, metric)
            all_results.extend(results)

    # Detailed mechanic analysis
    mechanic_analysis = detector.detailed_mechanic_analysis(df)

    # Export results
    export_engine = ExportEngine(detector)
    json_output = export_engine.export_to_json(all_results, mechanic_analysis, df)
    csv_output = export_engine.export_to_csv(all_results)

    output_file = f"card_bias_analysis_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        f.write(json_output)

    csv_file = f"card_bias_analysis_{int(time.time())}.csv"
    with open(csv_file, 'w') as f:
        f.write(csv_output)

    print(f"\n💾 Results saved:")
    print(f"   JSON: {output_file}")
    print(f"   CSV: {csv_file}")

    # Summary
    print(f"\n🎯 SUMMARY")
    print("=" * 30)
    biased_groups = [r for r in all_results if r.point_estimate < 0.8 or r.point_estimate > 1.25]

    if biased_groups:
        print(f"⚠️ Potential bias detected in {len(biased_groups)} group/metric combinations")
        for result in biased_groups:
            bias_type = "favorable" if result.point_estimate > 1.25 else "adverse"
            print(f"  {result.representation_group} - {result.metric_name}: {bias_type} bias (DI={result.point_estimate:.3f})")
    else:
        print("✅ No systematic design bias detected across representation groups")


if __name__ == "__main__":
    main()
