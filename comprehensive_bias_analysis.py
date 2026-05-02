#!/usr/bin/env python3
"""
Comprehensive MTG Card Design Bias Analysis
Expanded dataset targeting furry, LGBTQ+, and representation patterns
"""

from card_bias_detector import MTGBiasDetector
import json

def main():
    print("🎯 COMPREHENSIVE MTG DESIGN BIAS ANALYSIS")
    print("Targeting furry, LGBTQ+, and anthropomorphic representation")
    print("=" * 60)

    # Expanded dataset for statistical significance
    # Based on known representation from Scryfall Tagger community

    lgbtq_cards = [
        # Confirmed LGBTQ+ representation
        "Bearscape",  # SLD - achillean, trans male, romantic couple
        "Alesha, Who Smiles at Death",  # Trans woman representation
        "Ashiok, Nightmare Weaver",  # They/them nonbinary
        "Hallar, the Firefletcher",  # First canonical gay couple (backstory)
        "Kynaios and Tiro of Meletis",  # Gay male couple commanders
        "Saheeli Rai",  # WoC lesbian representation
        "Chandra, Torch of Defiance",  # Canonical lesbian
        "Niko Aris",  # Nonbinary planeswalker
        "Ral Zarek",  # Gay male representation
        "Vraska, Golgari Queen",  # Relationship with Jace (bi rep)
        "Aminatou, the Fateshifter",  # Young black girl
        "Huatli, Radiant Champion",  # Latina lesbian
        "Narset, Parter of Veils",  # Autistic representation
        "Elspeth, Sun's Champion",  # Complex trauma rep
        "Kaya, Ghost Assassin",  # Black woman representation
    ]

    anthropomorphic_cards = [
        # Known furry/anthropomorphic tags
        "Ajani, Caller of the Pride",  # Cat person
        "Ajani, Adversary of Tyrants",  # Cat person
        "Ajani, Mentor of Heroes",  # Cat person
        "Jedit Ojanen of Efrava",  # Cat warrior
        "Raksha Golden Cub",  # Cat lord
        "Marisi, Breaker of the Coil",  # Cat person
        "Kemba, Kha Regent",  # Cat person
        "Mirri, Weatherlight Duelist",  # Cat warrior
        "White Sun's Zenith",  # Cat token creator
        "Pride of Lions",  # Cat creature
        "Leonin Warleader",  # Cat soldier
        "Qasali Pridemage",  # Cat wizard
        "Brimaz, King of Oreskos",  # Cat soldier legend
        "Jareth, Leonin Titan",  # Cat legend
        "Kaheera, the Orphanguard",  # Cat beast
        "Nahiri, the Lithomancer",  # Kor (humanoid race)
    ]

    body_diversity_cards = [
        # Cards potentially tagged with body diversity
        "Angrath, the Flame-Chained",  # Minotaur - larger body type
        "Hurloon Minotaur",  # Classic minotaur
        "Kragma Butcher",  # Minotaur warrior
        "Boros Reckoner",  # Minotaur wizard
        "Neheb, the Eternal",  # Minotaur warrior
        "Sethron, Hurloon's Champion",  # Minotaur lord
        "Didgeridoo",  # Minotaur support
        "Raging Minotaur",  # Minotaur creature
        "Minotaur Explorer",  # Minotaur creature
        "Talruum Minotaur",  # Classic minotaur
    ]

    control_cards_iconic = [
        # Iconic spells - no representation diversity
        "Lightning Bolt",
        "Counterspell",
        "Swords to Plowshares",
        "Path to Exile",
        "Dark Ritual",
        "Giant Growth",
        "Shock",
        "Negate",
        "Duress",
        "Rampant Growth",
        "Sol Ring",
        "Command Tower",
        "Arcane Signet",
        "Chromatic Lantern",
        "Sensei's Divining Top",
    ]

    control_cards_generic = [
        # Generic creatures - minimal representation
        "Serra Angel",
        "Shivan Dragon",
        "Prodigal Sorcerer",
        "Llanowar Elves",
        "Birds of Paradise",
        "Wrath of God",
        "Damnation",
        "Terminate",
        "Hero's Downfall",
        "Beast Within",
        "Cultivate",
        "Kodama's Reach",
        "Farseek",
        "Nature's Lore",
        "Skullclamp",
    ]

    print(f"Dataset composition:")
    print(f"  LGBTQ+ representation: {len(lgbtq_cards)} cards")
    print(f"  Anthropomorphic: {len(anthropomorphic_cards)} cards")
    print(f"  Body diversity: {len(body_diversity_cards)} cards")
    print(f"  Control (iconic): {len(control_cards_iconic)} cards")
    print(f"  Control (generic): {len(control_cards_generic)} cards")
    print(f"  Total: {len(lgbtq_cards + anthropomorphic_cards + body_diversity_cards + control_cards_iconic + control_cards_generic)} cards")

    all_cards = lgbtq_cards + anthropomorphic_cards + body_diversity_cards + control_cards_iconic + control_cards_generic

    detector = MTGBiasDetector(random_state=42)

    # Collect comprehensive data
    print(f"\n🔍 Collecting comprehensive card data...")
    df = detector.collect_card_data(all_cards)

    if len(df) < 20:
        print("❌ Insufficient data for comprehensive analysis")
        return

    print(f"\n✅ Collected data for {len(df)} cards")

    # Show representation distribution
    print(f"\n📊 REPRESENTATION DISTRIBUTION:")
    for group in detector.representation_groups.keys():
        if f'is_{group}' in df.columns:
            count = df[f'is_{group}'].sum()
            percentage = count / len(df) * 100
            print(f"  {group:20s}: {count:2d} cards ({percentage:4.1f}%)")

    # Comprehensive bias analysis across all metrics
    metrics_to_analyze = {
        'power_score': 'Card Power Level',
        'complexity_score': 'Design Complexity',
        'cmc': 'Mana Cost'
    }

    all_results = []

    for metric_key, metric_name in metrics_to_analyze.items():
        if metric_key not in df.columns:
            continue

        print(f"\n📊 {metric_name.upper()} BIAS ANALYSIS")
        print("=" * 50)

        results = detector.analyze_representation_bias(df, metric_key)
        all_results.extend(results)

    # Advanced mechanic analysis
    print(f"\n🔧 COMPREHENSIVE MECHANICAL ANALYSIS")
    print("=" * 50)
    mechanic_analysis = detector.detailed_mechanic_analysis(df)

    # Intersectionality analysis - cards with multiple representation types
    print(f"\n🌈 INTERSECTIONALITY ANALYSIS")
    print("=" * 35)

    intersectional_cards = []
    for _, card in df.iterrows():
        rep_groups = []
        for group in detector.representation_groups.keys():
            if f'is_{group}' in df.columns and card[f'is_{group}']:
                rep_groups.append(group)

        if len(rep_groups) > 1:
            intersectional_cards.append({
                'name': card['name'],
                'groups': rep_groups,
                'power_score': card.get('power_score', 0),
                'complexity_score': card.get('complexity_score', 0)
            })

    if intersectional_cards:
        print(f"Found {len(intersectional_cards)} cards with multiple representation types:")
        for card in intersectional_cards:
            groups_str = " + ".join(card['groups'])
            print(f"  {card['name']:30s}: {groups_str}")
            print(f"    Power: {card['power_score']:.1f}, Complexity: {card['complexity_score']:.1f}")

    # Power level distribution analysis
    print(f"\n⚡ POWER LEVEL DISTRIBUTION ANALYSIS")
    print("=" * 40)

    for group in detector.representation_groups.keys():
        if f'is_{group}' in df.columns and df[f'is_{group}'].sum() >= 3:
            group_data = df[df[f'is_{group}'] == True]
            control_data = df[df[f'is_{group}'] == False]

            print(f"\n{group.upper()}:")
            print(f"  Group (n={len(group_data)}):")
            print(f"    Power score:    {group_data['power_score'].mean():.2f} ± {group_data['power_score'].std():.2f}")
            print(f"    Complexity:     {group_data['complexity_score'].mean():.2f} ± {group_data['complexity_score'].std():.2f}")
            print(f"    Mana cost:      {group_data['cmc'].mean():.2f} ± {group_data['cmc'].std():.2f}")

            print(f"  Control (n={len(control_data)}):")
            print(f"    Power score:    {control_data['power_score'].mean():.2f} ± {control_data['power_score'].std():.2f}")
            print(f"    Complexity:     {control_data['complexity_score'].mean():.2f} ± {control_data['complexity_score'].std():.2f}")
            print(f"    Mana cost:      {control_data['cmc'].mean():.2f} ± {control_data['cmc'].std():.2f}")

    # Save comprehensive results
    output_data = {
        'analysis_metadata': {
            'total_cards_analyzed': len(df),
            'cards_by_representation': {
                group: int(df[f'is_{group}'].sum())
                for group in detector.representation_groups.keys()
                if f'is_{group}' in df.columns
            },
            'metrics_analyzed': list(metrics_to_analyze.keys())
        },
        'bias_results': [
            {
                'group': r.representation_group,
                'metric': r.metric_name,
                'disparate_impact': r.point_estimate,
                'confidence_interval': r.confidence_interval,
                'group_stats': r.group_stats,
                'bias_detected': r.point_estimate < 0.8 or r.point_estimate > 1.25
            } for r in all_results
        ],
        'mechanic_analysis': mechanic_analysis,
        'intersectional_cards': intersectional_cards,
        'power_distributions': {
            group: {
                'group_power_mean': float(df[df[f'is_{group}'] == True]['power_score'].mean()) if df[f'is_{group}'].sum() > 0 else None,
                'control_power_mean': float(df[df[f'is_{group}'] == False]['power_score'].mean()) if df[f'is_{group}'].sum() < len(df) else None,
                'sample_size': int(df[f'is_{group}'].sum())
            }
            for group in detector.representation_groups.keys()
            if f'is_{group}' in df.columns and df[f'is_{group}'].sum() > 0
        }
    }

    output_file = f"comprehensive_bias_analysis_{int(__import__('time').time())}.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Comprehensive results saved to: {output_file}")

    # Executive summary
    print(f"\n🎯 EXECUTIVE SUMMARY")
    print("=" * 25)

    bias_detected = [r for r in all_results if r.point_estimate < 0.8 or r.point_estimate > 1.25]

    if bias_detected:
        print(f"🚨 SYSTEMATIC BIAS DETECTED: {len(bias_detected)} group/metric combinations show bias")
        for result in bias_detected[:5]:  # Top 5 most biased
            bias_type = "favorable" if result.point_estimate > 1.25 else "adverse"
            bias_magnitude = result.point_estimate if result.point_estimate > 1 else 1/result.point_estimate
            print(f"  {result.representation_group} × {result.metric_name.split('_')[2]}: {bias_type} bias ({bias_magnitude:.1f}x difference)")
    else:
        print("✅ No systematic bias detected in card design across representation groups")

    print(f"\n🏳️‍🌈 REPRESENTATION INSIGHTS:")
    if intersectional_cards:
        print(f"  {len(intersectional_cards)} cards have multiple representation types")

    total_diverse = sum(df[f'is_{group}'].sum() for group in detector.representation_groups.keys() if f'is_{group}' in df.columns)
    diversity_rate = total_diverse / len(df) * 100
    print(f"  {diversity_rate:.1f}% of analyzed cards have representation diversity")

    # Specific findings for user's interests
    if 'is_anthropomorphic' in df.columns:
        anthro_cards = df[df['is_anthropomorphic'] == True]
        if len(anthro_cards) > 0:
            avg_power = anthro_cards['power_score'].mean()
            print(f"  Anthropomorphic cards average {avg_power:.1f}/10 power score")

    if 'is_lgbtq_plus' in df.columns:
        lgbtq_cards = df[df['is_lgbtq_plus'] == True]
        if len(lgbtq_cards) > 0:
            avg_complexity = lgbtq_cards['complexity_score'].mean()
            print(f"  LGBTQ+ cards average {avg_complexity:.1f}/10 complexity score")

if __name__ == "__main__":
    main()