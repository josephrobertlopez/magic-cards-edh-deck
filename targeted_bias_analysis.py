#!/usr/bin/env python3
"""
Targeted MTG Bias Analysis - Strategic sample for fast meaningful results
"""

from card_bias_detector import MTGBiasDetector
import json

def main():
    print("🎯 TARGETED MTG BIAS ANALYSIS")
    print("Strategic sample for meaningful bias detection")
    print("=" * 50)

    # Strategic sample - enough for significance, fast enough to complete
    diverse_representation = [
        # Known LGBTQ+/diverse cards with good tag data
        "Bearscape",  # SLD - achillean, trans male, romantic couple, bears
        "Alesha, Who Smiles at Death",  # Trans representation
        "Ashiok, Nightmare Weaver",  # Nonbinary (they/them)
        "Kynaios and Tiro of Meletis",  # Gay couple commanders
        "Hallar, the Firefletcher",  # Gay couple (lore)
        "Chandra, Torch of Defiance",  # Lesbian representation
        "Ral Zarek",  # Gay male planeswalker
        "Ajani, Caller of the Pride",  # Anthropomorphic cat person
        "Marisi, Breaker of the Coil",  # Anthropomorphic cat person
        "Raksha Golden Cub",  # Cat lord
        "Angrath, the Flame-Chained",  # Minotaur (larger body type)
        "Hurloon Minotaur",  # Classic minotaur
    ]

    control_group = [
        # Iconic cards with minimal representation diversity
        "Lightning Bolt",
        "Counterspell",
        "Swords to Plowshares",
        "Path to Exile",
        "Wrath of God",
        "Serra Angel",
        "Shivan Dragon",
        "Sol Ring",
        "Command Tower",
        "Rampant Growth",
        "Shock",
        "Negate",
    ]

    print(f"Sample composition:")
    print(f"  Diverse representation: {len(diverse_representation)} cards")
    print(f"  Control group: {len(control_group)} cards")
    print(f"  Total: {len(diverse_representation + control_group)} cards")

    all_cards = diverse_representation + control_group

    detector = MTGBiasDetector(random_state=42)

    # Collect data
    print(f"\n🔍 Collecting targeted card data...")
    df = detector.collect_card_data(all_cards)

    print(f"\n✅ Collected data for {len(df)} cards")

    # Show representation distribution
    print(f"\n📊 REPRESENTATION DISTRIBUTION:")
    for group in detector.representation_groups.keys():
        if f'is_{group}' in df.columns:
            count = df[f'is_{group}'].sum()
            percentage = count / len(df) * 100
            if count > 0:
                print(f"  {group:20s}: {count:2d} cards ({percentage:4.1f}%)")

    # Targeted bias analysis
    print(f"\n⚡ POWER LEVEL BIAS ANALYSIS")
    print("=" * 35)
    power_results = detector.analyze_representation_bias(df, 'power_score')

    print(f"\n🧠 COMPLEXITY BIAS ANALYSIS")
    print("=" * 30)
    complexity_results = detector.analyze_representation_bias(df, 'complexity_score')

    print(f"\n💰 MANA COST BIAS ANALYSIS")
    print("=" * 25)
    cmc_results = detector.analyze_representation_bias(df, 'cmc')

    # Detailed mechanical analysis
    print(f"\n🔧 MECHANICAL BIAS ANALYSIS")
    print("=" * 30)
    mechanic_analysis = detector.detailed_mechanic_analysis(df)

    # Find high-impact cards for deck building
    print(f"\n🏆 HIGH-IMPACT DIVERSE CARDS")
    print("=" * 35)

    diverse_cards = []
    for _, card in df.iterrows():
        # Check if card has any representation
        has_representation = any(
            card.get(f'is_{group}', False)
            for group in detector.representation_groups.keys()
        )

        if has_representation:
            diverse_cards.append({
                'name': card['name'],
                'power_score': card.get('power_score', 0),
                'complexity_score': card.get('complexity_score', 0),
                'cmc': card.get('cmc', 0),
                'representation_types': [
                    group for group in detector.representation_groups.keys()
                    if card.get(f'is_{group}', False)
                ]
            })

    # Sort by power score
    diverse_cards.sort(key=lambda x: x['power_score'], reverse=True)

    print("Top diverse cards by power level:")
    for card in diverse_cards[:8]:
        rep_str = ", ".join(card['representation_types'])
        print(f"  {card['name']:30s}: {card['power_score']:4.1f} power ({rep_str})")

    # Calculate bias summary statistics
    all_results = power_results + complexity_results + cmc_results
    bias_detected = [r for r in all_results if r.point_estimate < 0.8 or r.point_estimate > 1.25]

    # Save results
    output_data = {
        'sample_info': {
            'total_cards': len(df),
            'diverse_cards': len(diverse_cards),
            'control_cards': len(df) - len(diverse_cards)
        },
        'bias_summary': {
            'total_tests': len(all_results),
            'biased_results': len(bias_detected),
            'bias_rate': len(bias_detected) / len(all_results) if all_results else 0
        },
        'bias_details': [
            {
                'group': r.representation_group,
                'metric': r.metric_name,
                'disparate_impact': r.point_estimate,
                'confidence_interval': r.confidence_interval,
                'bias_type': 'favorable' if r.point_estimate > 1.25 else 'adverse' if r.point_estimate < 0.8 else 'none',
                'group_stats': r.group_stats
            } for r in all_results
        ],
        'high_impact_diverse_cards': diverse_cards,
        'mechanic_patterns': mechanic_analysis
    }

    timestamp = int(__import__('time').time())
    output_file = f"targeted_bias_analysis_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    # Executive Summary
    print(f"\n🎯 EXECUTIVE SUMMARY")
    print("=" * 25)

    if bias_detected:
        print(f"🚨 BIAS DETECTED: {len(bias_detected)}/{len(all_results)} tests show systematic bias")
        print(f"Bias rate: {len(bias_detected)/len(all_results)*100:.1f}%")

        print(f"\nKey findings:")
        for result in bias_detected:
            bias_type = "favorable" if result.point_estimate > 1.25 else "adverse"
            metric_name = result.metric_name.split('_')[2] if '_' in result.metric_name else result.metric_name
            print(f"  {result.representation_group} shows {bias_type} {metric_name} bias (DI={result.point_estimate:.2f})")
    else:
        print("✅ No systematic bias detected in this sample")

    # Specific insights for furry/LGBTQ+ deck building
    lgbtq_cards = [c for c in diverse_cards if 'lgbtq_plus' in c['representation_types']]
    anthro_cards = [c for c in diverse_cards if 'anthropomorphic' in c['representation_types']]

    if lgbtq_cards:
        avg_power = sum(c['power_score'] for c in lgbtq_cards) / len(lgbtq_cards)
        print(f"\n🏳️‍🌈 LGBTQ+ cards average {avg_power:.1f}/10.0 power level")
        best_lgbtq = max(lgbtq_cards, key=lambda x: x['power_score'])
        print(f"  Strongest LGBTQ+ card: {best_lgbtq['name']} ({best_lgbtq['power_score']:.1f} power)")

    if anthro_cards:
        avg_power = sum(c['power_score'] for c in anthro_cards) / len(anthro_cards)
        print(f"\n🐾 Anthropomorphic cards average {avg_power:.1f}/10.0 power level")
        best_anthro = max(anthro_cards, key=lambda x: x['power_score'])
        print(f"  Strongest anthro card: {best_anthro['name']} ({best_anthro['power_score']:.1f} power)")

    # Deck building recommendations
    print(f"\n🎲 DECK BUILDING RECOMMENDATIONS")
    print("=" * 35)

    high_power_diverse = [c for c in diverse_cards if c['power_score'] >= 5.0]
    if high_power_diverse:
        print(f"High-power diverse cards for competitive play:")
        for card in high_power_diverse:
            print(f"  {card['name']} - {card['power_score']:.1f} power, {card['cmc']:.0f} mana")
    else:
        print("Consider supplementing with high-power staples for competitive viability")

    print(f"\nFor maximum representation with playable power level:")
    balanced_diverse = [c for c in diverse_cards if c['power_score'] >= 3.0 and c['cmc'] <= 6]
    for card in balanced_diverse[:5]:
        rep_str = ", ".join(card['representation_types'])
        print(f"  {card['name']} - {rep_str}")

if __name__ == "__main__":
    main()