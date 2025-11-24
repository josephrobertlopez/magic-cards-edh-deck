#!/usr/bin/env python3
"""
Proxy Generator CLI
End-to-end orchestration for generating MTG proxy cards.
"""

import argparse
from pathlib import Path
from typing import Optional

from src.models.card import Card
from src.models.mana_cost import parse_mana_cost
from src.parsers.color_inference import infer_color_from_mana_cost
from src.matching.template_decision_tree import TemplateDecisionTree
from src.download.scryfall_downloader import ScryfallDownloader, ArtworkDownloader, CardArtworkError, TemplateBlank
from src.cache.template_cache import TemplateCacheManager
from src.cache.vlm_region_cache import VLMRegionCacheManager
from src.layout.simple_heuristic import SimpleLayoutEngine
from src.layout.mcts_layout_engine import MCTSLayoutEngine
from src.compositor.card_compositor import CardCompositor
from src.organization.folder_organizer import FolderOrganizer
from src.vlm.layout_scorer import VLMLayoutScorer
from src.batch.batch_processor import BatchProcessor


def main(
    excel_path: Optional[Path] = None,
    output_dir: Path = Path("output/proxies"),
    single_card: Optional[int] = None,
    organize_by: Optional[list[str]] = None,
    use_mcts: bool = True,
    max_rollouts: int = 100,
    skip_existing: bool = True
):
    """
    Generate proxy cards from Hellcube spreadsheet.

    Pipeline (T028 + T062-T065 + T066-T068):
    1. Parse one row (or all rows) from Excel
    2. Download template via decision tree (T062: with VLM region detection)
    3. Download artwork (T068: skip card on error, log and continue)
    4. Optimize layout with MCTS (T063: MCTSLayoutEngine)
    5. Composite card (T064: accepts PlacedElement layouts)
    6. Validate quality with VLM (T065: score final layout)
    7. Save PNG to organized folder (T067: multi-strategy voting)
    8. Batch processing with progress reporting (T066)

    Args:
        excel_path: Path to Hellcube AJ.xlsx (if None, uses test card)
        output_dir: Base output directory for generated PNGs
        single_card: If set, only process row at this index (0-based)
        organize_by: List of organization strategies (T067: color/type/set/custom)
                    Default: ['color'] if None
        use_mcts: Whether to use MCTS layout optimization (default True)
        max_rollouts: MCTS rollout budget (default 100, production 300)
        skip_existing: Skip cards that already have generated PNGs (default True)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # T066: Batch processing mode if Excel file provided
    if excel_path and excel_path.exists():
        print(f"📊 Batch processing mode: {excel_path}")
        processor = BatchProcessor(
            excel_path=excel_path,
            output_dir=output_dir,
            organize_by=organize_by,
            use_mcts=use_mcts,
            max_rollouts=max_rollouts,
            skip_existing=skip_existing,
            single_card=single_card
        )
        results = processor.process_batch()
        return results

    # Initialize components
    decision_tree = TemplateDecisionTree()
    scryfall_downloader = ScryfallDownloader()  # T062: VLM region detection integrated
    artwork_downloader = ArtworkDownloader()
    cache_manager = TemplateCacheManager()
    region_cache = VLMRegionCacheManager()  # T062: VLM region caching

    # T063: MCTS layout engine or simple fallback
    if use_mcts:
        print(f"🎯 Using MCTS layout optimization (max_rollouts={max_rollouts})")
        layout_engine = MCTSLayoutEngine(max_rollouts=max_rollouts)
    else:
        print(f"📐 Using simple heuristic layout")
        layout_engine = SimpleLayoutEngine()

    compositor = CardCompositor()  # T064: accepts PlacedElement layouts
    template_blanker = TemplateBlank()
    folder_organizer = FolderOrganizer(base_dir=output_dir)

    # T065: VLM layout quality scorer
    vlm_scorer = VLMLayoutScorer(use_vlm=True)

    # TODO: Implement Excel parser (T012-T017)
    # For now, use test card
    print("⚠️  Excel parser not implemented yet (T012-T017 pending)")
    print("Using test card instead...")

    # Create test card
    test_mana = parse_mana_cost("(Bu,Bu)(1)")
    test_card = Card(
        name="Test Proxy Card",
        type="Creature",
        mana_cost=test_mana,
        color=infer_color_from_mana_cost(test_mana),
        legendary=False,
        subtypes=["Human", "Wizard"],
        abilities=["Flying", "When this creature enters the battlefield, draw a card."],
        power_toughness="2/3",
        flavor_text="A test card for the proxy generator.",
        author="Unknown Artist"
    )

    print(f"\n📋 Processing card: {test_card.name}")
    print(f"   Type: {test_card.type}")
    print(f"   Color: {test_card.color}")
    print(f"   Mana Cost: {test_card.mana_cost.symbols} (CMC {test_card.mana_cost.cmc})")

    # Step 1: Select template
    print(f"\n🎨 Selecting template...")
    card_type, color_code, legendary = decision_tree.select_template(test_card)
    print(f"   Template: {card_type} / {color_code} / Legendary={legendary}")

    # Step 2: Download template (check cache first)
    print(f"\n⬇️  Downloading template...")
    template_metadata = cache_manager.find_by_attributes(test_card.color, test_card.type, test_card.legendary)

    if template_metadata:
        print(f"   ✓ Found in cache: {template_metadata.file_path}")
        # T062: Load VLM regions from cache
        if template_metadata.sha256_hash:
            regions = region_cache.get_cached_regions(template_metadata.sha256_hash)
            if regions:
                template_metadata.regions = regions
                print(f"   ✓ VLM regions loaded from cache")
    else:
        print(f"   Downloading from Scryfall...")
        template_metadata = scryfall_downloader.download_template_by_attributes(
            test_card.color,
            test_card.type,
            test_card.legendary
        )

        if template_metadata:
            print(f"   ✓ Downloaded: {template_metadata.file_path}")
            cache_manager.cache_template(template_metadata.file_path, template_metadata)
        else:
            print(f"   ✗ Failed to download template")
            return

    # Step 2.5: Blank out text regions using VLM and capture detected regions
    print(f"\n🎨 Blanking template text regions...")
    blank_template_path, detected_regions = template_blanker.blank_template(template_metadata.file_path)
    template_metadata.file_path = blank_template_path  # Use blanked version

    # Convert detected regions dict to TemplateRegions object
    if detected_regions:
        from src.models.template_regions import TemplateRegions
        from src.models.bounding_box import BoundingBox

        # Build TemplateRegions from detected regions dict
        regions_dict = {}
        for region_name, (x, y, width, height) in detected_regions.items():
            regions_dict[region_name] = BoundingBox(x=x, y=y, width=width, height=height)

        # Map region names to TemplateRegions fields
        template_metadata.regions = TemplateRegions(
            template_hash=template_metadata.sha256_hash,
            name_box=regions_dict.get('name_box'),
            mana_cost_box=regions_dict.get('mana_box') or regions_dict.get('mana_cost_box'),
            type_line_box=regions_dict.get('type_box') or regions_dict.get('type_line_box'),
            text_boxes=[regions_dict['text_box']] if 'text_box' in regions_dict else [],
            pt_box=regions_dict.get('pt_box'),
            flavor_box=regions_dict.get('flavor_box')
        )

    # Step 3: Download artwork (T068: error handling - skip card on failure)
    artwork_path = None
    if test_card.artwork_url:
        print(f"\n🖼️  Downloading artwork...")
        try:
            artwork_path = artwork_downloader.download_artwork(
                str(test_card.artwork_url),
                test_card.name
            )
            print(f"   ✓ Downloaded: {artwork_path}")
        except CardArtworkError as e:
            # T068: Log error with card name + URL, skip card, continue batch
            print(f"   ✗ Artwork download failed for '{test_card.name}'")
            print(f"      URL: {test_card.artwork_url}")
            print(f"      Error: {e}")
            print(f"   ⚠️  Skipping card due to artwork error...")
            # In batch processing, this would continue to next card
            # For single test card, we'll still generate without artwork
            artwork_path = None

    # Step 4: Generate layout (HARD FAIL - no fallbacks)
    print(f"\n📐 Generating layout...")

    # T063: MCTS requires VLM regions - hard fail if missing
    if not hasattr(template_metadata, 'regions') or not template_metadata.regions:
        raise ValueError(f"Template missing VLM regions - cannot generate MCTS layout")

    # Convert TemplateRegions to Dict[str, BoundingBox] for MCTS
    # Map text_boxes list to individual ability regions (ability_1, ability_2, etc.)
    # Filter out None regions
    template_regions = {}
    if template_metadata.regions.name_box:
        template_regions['name_box'] = template_metadata.regions.name_box
    if template_metadata.regions.mana_cost_box:
        template_regions['mana_cost_box'] = template_metadata.regions.mana_cost_box
    if template_metadata.regions.type_line_box:
        template_regions['type_line_box'] = template_metadata.regions.type_line_box
    if template_metadata.regions.pt_box:
        template_regions['pt_box'] = template_metadata.regions.pt_box
    if template_metadata.regions.flavor_box:
        template_regions['flavor_box'] = template_metadata.regions.flavor_box

    # Map each text box to numbered regions (text_box_1, text_box_2, etc.)
    for i, text_box in enumerate(template_metadata.regions.text_boxes, 1):
        template_regions[f'text_box_{i}'] = text_box

    # Add fallback 'text_boxes' pointing to first text box for ability overflow
    if template_metadata.regions.text_boxes:
        template_regions['text_boxes'] = template_metadata.regions.text_boxes[0]

    layout = layout_engine.optimize_layout(
        test_card,
        template_regions,
        max_rollouts=max_rollouts
    )

    print(f"   Layout elements: {list(layout.keys())}")

    # Step 5: Composite card with organized output path (T067)
    print(f"\n🎴 Compositing card...")

    # Use folder organizer to determine output path
    if organize_by:
        print(f"   📁 Organizing by: {organize_by}")
        output_path = folder_organizer.organize_card(test_card, strategies=organize_by)
    else:
        # Default: organize by color
        output_path = folder_organizer.organize_card(test_card, strategies=['color'])

    final_path = compositor.composite_card(
        test_card,
        template_metadata.file_path,
        layout,
        output_path
    )
    print(f"   ✓ Generated: {final_path}")

    # T065: VLM layout quality validation
    print(f"\n🔍 Validating layout quality with VLM...")
    from PIL import Image
    from src.models.layout_state import LayoutState
    from src.models.placed_element import PlacedElement

    # Create LayoutState from final composite for VLM scoring
    # Load generated image and create state with placed elements
    final_image = Image.open(final_path)

    # Convert layout dict to placed elements list
    if use_mcts and isinstance(next(iter(layout.values()), None), PlacedElement):
        # MCTS layout is already Dict[str, PlacedElement]
        placed_elements = list(layout.values())
    else:
        # Simple layout is Dict[str, Tuple[int, int]] - convert to PlacedElement
        placed_elements = []
        for element_type, position in layout.items():
            if isinstance(position, PlacedElement):
                placed_elements.append(position)
            elif isinstance(position, tuple):
                x, y = position
                # Get text content from card
                text_content = ""
                if element_type == "name":
                    text_content = test_card.name
                elif element_type == "type_line":
                    text_content = test_card.type
                elif element_type == "mana_cost":
                    text_content = str(test_card.mana_cost.symbols) if test_card.mana_cost else ""
                elif element_type == "abilities":
                    text_content = "\n".join(test_card.abilities) if test_card.abilities else ""
                elif element_type == "power_toughness":
                    text_content = test_card.power_toughness or ""
                elif element_type == "flavor_text":
                    text_content = test_card.flavor_text or ""

                placed_elements.append(PlacedElement(
                    element_type=element_type,
                    text_content=text_content,
                    position=(x, y),
                    size=(100, 30),  # Approximate size
                    font_size=12,
                    alignment='left'
                ))

    # Create layout state for VLM scoring
    layout_state = LayoutState(
        placed_elements=placed_elements,
        remaining_elements=[],
        template_regions=template_regions if use_mcts else {}
    )

    # Score layout with VLM
    quality_result = vlm_scorer.score_layout_detailed(layout_state)

    print(f"   Overall Score: {quality_result.overall_score:.3f}")
    print(f"   - Readability: {quality_result.readability_score:.3f}")
    print(f"   - Convention: {quality_result.convention_compliance:.3f}")
    print(f"   - Aesthetic: {quality_result.aesthetic_balance:.3f}")
    print(f"   - No Overflow: {quality_result.no_overflow}")

    if quality_result.issues:
        print(f"   Issues: {', '.join(quality_result.issues)}")
    if quality_result.reasoning:
        print(f"   Reasoning: {quality_result.reasoning}")

    # T065: Warn if quality below threshold
    if quality_result.overall_score < 0.8:
        print(f"   ⚠️  Low quality layout (score < 0.8)")
        print(f"   Consider re-running with increased --max-rollouts")

    print(f"\n✅ Done! Proxy card saved to: {final_path}")
    print(f"   Quality Score: {quality_result.overall_score:.3f}/1.0")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MTG proxy cards from Hellcube spreadsheet")
    parser.add_argument("--input", type=Path, help="Path to Hellcube AJ.xlsx")
    parser.add_argument("--output", type=Path, default=Path("output/proxies"), help="Output directory")
    parser.add_argument("--single-card", type=int, help="Process only this row index (0-based)")
    parser.add_argument(
        "--organize-by",
        type=str,
        nargs='+',
        help="Organization strategies (T067): color, type, set, or custom. "
             "Example: --organize-by color type (creates nested folders)"
    )
    parser.add_argument(
        "--use-mcts",
        action="store_true",
        default=True,
        help="Use MCTS layout optimization (T063, default: True)"
    )
    parser.add_argument(
        "--no-mcts",
        action="store_false",
        dest="use_mcts",
        help="Use simple heuristic layout instead of MCTS"
    )
    parser.add_argument(
        "--max-rollouts",
        type=int,
        default=100,
        help="MCTS rollout budget (default: 100, production: 300)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip cards that already have generated PNGs (T066, default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Regenerate all cards even if PNGs already exist"
    )

    args = parser.parse_args()

    main(
        excel_path=args.input,
        output_dir=args.output,
        single_card=args.single_card,
        organize_by=args.organize_by,
        use_mcts=args.use_mcts,
        max_rollouts=args.max_rollouts,
        skip_existing=args.skip_existing
    )
