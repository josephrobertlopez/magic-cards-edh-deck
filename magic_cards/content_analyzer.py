"""
Content Analyzer: Protocol-first composition analysis for any content type

Analyzes manifest data to understand collection characteristics.
Works with any content domain via schema-based categorization.

Use cases:
- Trading cards: Color identity, types, rarity
- Pokemon: Types, evolution stages
- Product images: Categories, tags, brands
- Documents: File types, authors, topics
- Generic resources: Any categorical breakdown
"""

import json
from typing import Dict, List, Any, Optional, Callable
from collections import Counter


# ===== ANALYSIS STRATEGIES =====

def analyze_by_category_patterns(items: List[Dict[str, Any]],
                                  category_patterns: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Categorize items by name pattern matching.

    Args:
        items: List of manifest items
        category_patterns: Dict mapping category names to search patterns
                          Example: {"Type_A": ["Fire", "Flame"], "Type_B": ["Water", "Ice"]}

    Returns:
        Dict with category counts and detected categories
    """
    item_names = [item["name"] for item in items]

    category_counts = {}
    detected_categories = []

    for category, patterns in category_patterns.items():
        count = sum(1 for name in item_names if any(p in name for p in patterns))
        if count > 0:
            category_counts[category] = count
            detected_categories.append(category)

    return {
        "categories": detected_categories,
        "category_counts": category_counts
    }


def analyze_by_frequency(items: List[Dict[str, Any]], top_n: int = 5) -> Dict[str, Any]:
    """
    Analyze most common items in collection.

    Args:
        items: List of manifest items
        top_n: Number of top items to return

    Returns:
        Dict with frequency analysis
    """
    item_names = [item["name"] for item in items]
    counter = Counter(item_names)
    most_common = counter.most_common(top_n)

    return {
        "most_common": [{"name": name, "count": count} for name, count in most_common],
        "has_duplicates": any(count > 1 for _, count in counter.items())
    }


# ===== DOMAIN-SPECIFIC STRATEGIES =====
# NOTE: Strategies now loaded from .config/strategies/*.json
# Use load_strategy_configs() from config_loader module


def detect_domain(items: List[Dict[str, Any]],
                  strategies: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Detect content domain using strategy pattern matching.

    Args:
        items: List of manifest items
        strategies: List of domain strategy definitions

    Returns:
        Matched strategy dict or None
    """
    item_names = [item["name"] for item in items]

    for strategy in strategies:
        detection_patterns = strategy.get("detection_patterns", {})

        for pattern_group, patterns in detection_patterns.items():
            # Check if any pattern matches
            if any(any(p in name for p in patterns) for name in item_names):
                return strategy

    return None


def apply_inference_rules(items: List[Dict[str, Any]],
                          inference_rules: List[Dict[str, Any]]) -> Optional[List[str]]:
    """
    Execute inference rules to determine categories when explicit matches fail.

    Args:
        items: List of manifest items with 'name' field
        inference_rules: List of rule definitions from strategy config
                        Example: [{"condition": {"any_name_contains": ["Dragon", "Wyvern"]},
                                   "infer_categories": ["Fire", "Flying"],
                                   "rationale": "Dragons typically associated with fire/air"}]

    Returns:
        List of inferred category names, or None if no rules match

    Supported Condition Types:
        - any_name_contains: Match if ANY item name contains ANY of the keywords
        - all_names_contain: Match if ALL item names contain at least one keyword
    """
    item_names = [item["name"] for item in items]

    for rule in inference_rules:
        condition = rule.get("condition", {})

        # Condition type: any_name_contains
        if "any_name_contains" in condition:
            keywords = condition["any_name_contains"]
            if any(any(kw in name for kw in keywords) for name in item_names):
                return rule["infer_categories"]

        # Condition type: all_names_contain (future extension)
        elif "all_names_contain" in condition:
            keywords = condition["all_names_contain"]
            if all(any(kw in name for kw in keywords) for name in item_names):
                return rule["infer_categories"]

    return None


# ===== CORE ANALYSIS FUNCTIONS =====

def analyze_manifest(manifest_path: str,
                     analysis_schema: Optional[Dict[str, Any]] = None,
                     custom_strategies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Analyze content collection from manifest.

    Args:
        manifest_path: Path to fetch manifest JSON
        analysis_schema: Optional schema defining analysis parameters
                        Example: {"category_field": "type", "top_n": 10}
        custom_strategies: Optional list of custom domain strategies

    Returns:
        Analysis dict with composition breakdown
    """
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    items = manifest.get("items", [])
    successful_items = [item for item in items if item.get("status") == "success"]

    if not successful_items:
        return {"error": "No successful items in manifest"}

    # Basic stats
    analysis = {
        "total_items": len(successful_items),
        "unique_items": len(set(item["name"] for item in successful_items)),
        "item_names": [item["name"] for item in successful_items]
    }

    # Add frequency analysis
    top_n = analysis_schema.get("top_n", 5) if analysis_schema else 5
    analysis.update(analyze_by_frequency(successful_items, top_n))

    # Detect domain using strategies (FR-007: Load from .config/)
    all_strategies = custom_strategies or []

    # Load builtin strategies from config files
    from magic_cards.config_loader import load_strategy_configs
    strategy_configs = load_strategy_configs()
    all_strategies.extend(strategy_configs.values())

    detected_strategy = detect_domain(successful_items, all_strategies)

    if detected_strategy:
        analysis["detected_domain"] = detected_strategy["domain"]
        analysis["strategy"] = detected_strategy

        # Apply domain-specific analysis
        if "category_patterns" in detected_strategy:
            category_analysis = analyze_by_category_patterns(
                successful_items,
                detected_strategy["category_patterns"]
            )
            analysis.update(category_analysis)

            # Map categories to higher-level grouping (e.g., lands → colors)
            if "category_mapping" in detected_strategy:
                mapping = detected_strategy["category_mapping"]
                categories = category_analysis.get("categories", [])

                # If no categories found, apply inference rules from config
                if not categories and "inference_rules" in detected_strategy:
                    inferred = apply_inference_rules(
                        successful_items,
                        detected_strategy["inference_rules"]
                    )
                    if inferred:
                        categories = inferred
                        analysis["categories"] = categories
                        analysis["inferred_from"] = "inference_rules"

                # Map to groups
                mapped_groups = [mapping[cat] for cat in categories]
                analysis["mapped_groups"] = mapped_groups

                # Build group identity notation (if configured)
                if "group_notation" in detected_strategy and mapped_groups:
                    notation = detected_strategy["group_notation"]
                    identity = "".join(notation.get(g, g[0]) for g in mapped_groups)
                    analysis["group_identity"] = identity
    else:
        analysis["detected_domain"] = "generic"

    return analysis


def get_fill_recommendations(analysis: Dict[str, Any],
                            slots_needed: int,
                            fill_config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Recommend items to fill empty slots based on analysis.

    Args:
        analysis: Content analysis from analyze_manifest()
        slots_needed: Number of empty slots to fill
        fill_config: Optional fill configuration override
                    Example: {"strategy": "repeat_first", "template": "Placeholder"}

    Returns:
        List of recommended item names
    """
    # Check for custom fill config
    if fill_config:
        strategy_name = fill_config.get("strategy", "repeat_first")
    else:
        # Use detected domain strategy
        detected_strategy = analysis.get("strategy", {})
        strategy_name = detected_strategy.get("fill_strategy", "repeat_first")

    # === FILL STRATEGIES ===

    if strategy_name == "distribute_by_category":
        # Distribute fills across detected categories
        categories = analysis.get("categories", [])

        if not categories:
            # Fallback to first item
            first_item = analysis.get("item_names", ["Placeholder"])[0]
            return [first_item] * slots_needed

        # Get category mapping (e.g., Forest → Green)
        category_mapping = analysis.get("strategy", {}).get("category_mapping", {})
        mapped_groups = analysis.get("mapped_groups", categories)

        # Distribute slots evenly across categories
        items_per_category = slots_needed // len(categories)
        remainder = slots_needed % len(categories)

        recommendations = []
        for i, category in enumerate(categories):
            count = items_per_category + (1 if i < remainder else 0)
            recommendations.extend([category] * count)

        return recommendations

    elif strategy_name == "repeat_template":
        # Use a template item (e.g., "Energy Card")
        template = fill_config.get("template") if fill_config else None
        if not template:
            template = analysis.get("strategy", {}).get("fill_template", "Placeholder")
        return [template] * slots_needed

    elif strategy_name == "repeat_most_common":
        # Repeat the most common item
        most_common = analysis.get("most_common", [])
        if most_common:
            most_common_name = most_common[0]["name"]
            return [most_common_name] * slots_needed
        else:
            first_item = analysis.get("item_names", ["Placeholder"])[0]
            return [first_item] * slots_needed

    else:  # "repeat_first" or unknown
        # Default: repeat first item
        first_item = analysis.get("item_names", ["Placeholder"])[0]
        return [first_item] * slots_needed


def print_analysis(analysis: Dict[str, Any]):
    """Pretty-print content analysis."""
    print("\n" + "=" * 70)
    print("🔍 CONTENT ANALYSIS")
    print("=" * 70)

    print(f"\n📊 Composition:")
    print(f"   Total items: {analysis.get('total_items', 0)}")
    print(f"   Unique items: {analysis.get('unique_items', 0)}")
    print(f"   Detected domain: {analysis.get('detected_domain', 'unknown')}")

    if analysis.get("most_common"):
        print(f"\n🔥 Most common items:")
        for item in analysis["most_common"][:3]:
            print(f"   {item['name']}: {item['count']}x")

    if analysis.get("mapped_groups"):
        groups_str = ', '.join(analysis['mapped_groups'])
        print(f"\n🏷️  Detected groups: {groups_str}")
        if analysis.get("group_identity"):
            print(f"   Group identity: {analysis['group_identity']}")

    if analysis.get("category_counts"):
        print(f"\n📦 Category breakdown:")
        for category, count in analysis["category_counts"].items():
            if count > 0:
                print(f"   {category}: {count}")

    print("=" * 70)
