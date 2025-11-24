#!/usr/bin/env python3
"""
Batch Processor for Hellcube Proxy Generation

Processes full Hellcube dataset through MCTS proxy generation pipeline
with progress reporting and error handling.

Features (T066 + NFR-006):
- Parse all cards from Hellcube AJ.xlsx
- Process each card through full MCTS pipeline
- Progress reporting: [YYYY-MM-DD HH:MM:SS] Card N/Total: <name> - <duration>s
- Error handling: skip failed cards, continue batch
- Performance validation: 200-1500s per card expected (NFR-003)
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import time

from src.parsers.hellcube_parser import HellcubeExcelParser
from src.models.card import Card
from src.matching.template_decision_tree import TemplateDecisionTree
from src.download.scryfall_downloader import ScryfallDownloader, CardArtworkError, TemplateBlank
from src.download.scryfall_downloader import ArtworkDownloader
from src.cache.template_cache import TemplateCacheManager
from src.layout.simple_heuristic import SimpleLayoutEngine
from src.layout.mcts_layout_engine import MCTSLayoutEngine
from src.compositor.card_compositor import CardCompositor
from src.organization.folder_organizer import FolderOrganizer
from src.vlm.layout_scorer import VLMLayoutScorer


@dataclass
class BatchResult:
    """Results from batch processing run."""
    total_cards: int
    successful: int
    failed: int
    skipped: int
    total_duration: float
    avg_quality_score: float
    card_results: List[Dict[str, Any]]


@dataclass
class CardResult:
    """Result from processing single card."""
    card_name: str
    success: bool
    duration: float
    quality_score: Optional[float] = None
    output_path: Optional[Path] = None
    error: Optional[str] = None
    rollouts_used: Optional[int] = None
    converged: Optional[bool] = None


class BatchProcessor:
    """
    Batch processor for Hellcube proxy generation.

    Orchestrates full MCTS pipeline for all cards in dataset with
    progress reporting and error handling.

    Example:
        >>> processor = BatchProcessor(
        ...     excel_path=Path("data/Hellcube AJ.xlsx"),
        ...     output_dir=Path("output/proxies"),
        ...     use_mcts=True,
        ...     max_rollouts=300
        ... )
        >>> results = processor.process_batch()
        >>> print(f"Success: {results.successful}/{results.total_cards}")
    """

    def __init__(
        self,
        excel_path: Path,
        output_dir: Path = Path("output/proxies"),
        organize_by: Optional[List[str]] = None,
        use_mcts: bool = True,
        max_rollouts: int = 300,
        skip_existing: bool = True,
        single_card: Optional[int] = None
    ):
        """
        Initialize batch processor.

        Args:
            excel_path: Path to Hellcube AJ.xlsx
            output_dir: Base output directory for generated PNGs
            organize_by: Organization strategies (default: ['color'])
            use_mcts: Whether to use MCTS layout optimization
            max_rollouts: MCTS rollout budget (default 300)
            skip_existing: Skip cards that already have generated PNGs
            single_card: If set, only process card at this index (0-based)
        """
        self.excel_path = excel_path
        self.output_dir = output_dir
        self.organize_by = organize_by or ['color']
        self.use_mcts = use_mcts
        self.max_rollouts = max_rollouts
        self.skip_existing = skip_existing
        self.single_card = single_card

        # Initialize components
        self.parser = HellcubeExcelParser(str(excel_path))
        self.decision_tree = TemplateDecisionTree()
        self.scryfall_downloader = ScryfallDownloader()
        self.artwork_downloader = ArtworkDownloader()
        self.cache_manager = TemplateCacheManager()
        self.compositor = CardCompositor()
        self.template_blanker = TemplateBlank()
        self.folder_organizer = FolderOrganizer(base_dir=output_dir)

        # Layout engine selection
        if use_mcts:
            print(f"🎯 Using MCTS layout optimization (max_rollouts={max_rollouts})")
            self.layout_engine = MCTSLayoutEngine(max_rollouts=max_rollouts)
        else:
            print(f"📐 Using simple heuristic layout")
            self.layout_engine = SimpleLayoutEngine()

        # VLM scorer for quality validation
        self.vlm_scorer = VLMLayoutScorer(use_vlm=True)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

    def process_batch(self) -> BatchResult:
        """
        Process all cards from Excel file through MCTS pipeline.

        Returns:
            BatchResult with success/failure counts and card-level results

        Progress format (NFR-006):
            [YYYY-MM-DD HH:MM:SS] Card N/Total: <name> - <duration>s, quality=<score>, converged after <rollouts> rollouts
        """
        print(f"\n📊 Batch Processing Started")
        print(f"   Excel: {self.excel_path}")
        print(f"   Output: {self.output_dir}")
        print(f"   MCTS: {self.use_mcts} (rollouts={self.max_rollouts})")
        print(f"   Organization: {self.organize_by}\n")

        # Parse all cards from Excel with MCTS discovery
        print(f"📋 Parsing cards from Excel (MCTS discovery)...")
        start_time = time.time()
        cards = self.parser.parse_all_cards(use_mcts=True)
        parse_duration = time.time() - start_time
        print(f"✅ Parsed {len(cards)} cards in {parse_duration:.1f}s\n")

        # Filter to single card if requested
        if self.single_card is not None:
            if 0 <= self.single_card < len(cards):
                cards = [cards[self.single_card]]
                print(f"🎯 Processing only card {self.single_card}: {cards[0].name}\n")
            else:
                print(f"⚠️  Invalid card index {self.single_card} (total: {len(cards)}), processing all cards\n")

        # Process each card
        card_results = []
        successful = 0
        failed = 0
        skipped = 0
        quality_scores = []

        batch_start = time.time()

        for i, card in enumerate(cards, 1):
            result = self._process_single_card(card, i, len(cards))
            card_results.append(result)

            if result.success:
                successful += 1
                if result.quality_score:
                    quality_scores.append(result.quality_score)
            elif result.error and "already exists" in result.error:
                skipped += 1
            else:
                failed += 1

        batch_duration = time.time() - batch_start
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 Batch Processing Complete")
        print(f"{'='*60}")
        print(f"Total Cards: {len(cards)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Total Duration: {batch_duration:.1f}s ({batch_duration/60:.1f}m)")
        print(f"Avg Quality Score: {avg_quality:.3f}")
        if successful > 0:
            print(f"Avg Time per Card: {batch_duration/successful:.1f}s")
        print(f"{'='*60}\n")

        return BatchResult(
            total_cards=len(cards),
            successful=successful,
            failed=failed,
            skipped=skipped,
            total_duration=batch_duration,
            avg_quality_score=avg_quality,
            card_results=[vars(r) for r in card_results]
        )

    def _process_single_card(self, card: Card, index: int, total: int) -> CardResult:
        """
        Process single card through MCTS pipeline.

        Args:
            card: Card object to process
            index: Current card index (1-based)
            total: Total number of cards

        Returns:
            CardResult with processing outcome
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        card_start = time.time()

        try:
            # Check if card already exists
            output_path = self.folder_organizer.organize_card(card, strategies=self.organize_by)
            if self.skip_existing and output_path.exists():
                duration = time.time() - card_start
                print(f"[{timestamp}] Card {index}/{total}: {card.name} - SKIPPED (already exists)")
                return CardResult(
                    card_name=card.name,
                    success=False,
                    duration=duration,
                    error="Card already exists"
                )

            # Step 1: Select template
            card_type, color_code, legendary = self.decision_tree.select_template(card)

            # Step 2: Download template (check cache first)
            template_metadata = self.cache_manager.find_by_attributes(
                card.color, card.type, card.legendary
            )

            if not template_metadata:
                template_metadata = self.scryfall_downloader.download_template_by_attributes(
                    card.color, card.type, card.legendary
                )

                if not template_metadata:
                    raise ValueError("Failed to download template")

                self.cache_manager.cache_template(
                    template_metadata.file_path,
                    template_metadata
                )

            # Step 2.5: Blank out text regions and capture detected regions
            blank_template_path, detected_regions = self.template_blanker.blank_template(template_metadata.file_path)
            template_metadata.file_path = blank_template_path

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

            # Step 3: Download artwork (skip on error)
            artwork_path = None
            if card.artwork_url:
                try:
                    artwork_path = self.artwork_downloader.download_artwork(
                        str(card.artwork_url),
                        card.name
                    )
                except CardArtworkError as e:
                    print(f"   ⚠️  Artwork download failed: {e}")
                    artwork_path = None

            # Step 4: Generate layout (HARD FAIL - no fallbacks)
            if not hasattr(template_metadata, 'regions') or not template_metadata.regions:
                raise ValueError(f"Template missing VLM regions - cannot generate layout")

            # Map text_boxes list to individual ability regions
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

            layout = self.layout_engine.optimize_layout(
                card,
                template_regions,
                max_rollouts=self.max_rollouts
            )
            # TODO: Extract rollouts_used and converged from MCTS result
            rollouts_used = None
            converged = None

            # Step 5: Composite card
            final_path = self.compositor.composite_card(
                card,
                template_metadata.file_path,
                layout,
                output_path
            )

            # Step 6: VLM quality validation
            from PIL import Image
            from src.models.layout_state import LayoutState
            from src.models.placed_element import PlacedElement

            # Convert layout to LayoutState for scoring
            if self.use_mcts and isinstance(next(iter(layout.values()), None), PlacedElement):
                placed_elements = list(layout.values())
            else:
                # Convert simple layout tuples to PlacedElement
                placed_elements = self._convert_simple_layout(card, layout)

            layout_state = LayoutState(
                placed_elements=placed_elements,
                remaining_elements=[],
                template_regions=template_regions
            )

            quality_result = self.vlm_scorer.score_layout_detailed(layout_state)

            duration = time.time() - card_start

            # NFR-006 progress format
            progress_msg = (
                f"[{timestamp}] Card {index}/{total}: {card.name} - "
                f"{duration:.1f}s, quality={quality_result.overall_score:.3f}"
            )
            if converged is not None:
                progress_msg += f", converged after {rollouts_used} rollouts"

            print(progress_msg)

            # Warn if low quality
            if quality_result.overall_score < 0.8:
                print(f"   ⚠️  Low quality layout (score < 0.8)")

            return CardResult(
                card_name=card.name,
                success=True,
                duration=duration,
                quality_score=quality_result.overall_score,
                output_path=final_path,
                rollouts_used=rollouts_used,
                converged=converged
            )

        except Exception as e:
            duration = time.time() - card_start
            error_msg = str(e)
            print(f"[{timestamp}] Card {index}/{total}: {card.name} - FAILED ({error_msg})")

            return CardResult(
                card_name=card.name,
                success=False,
                duration=duration,
                error=error_msg
            )

    def _convert_simple_layout(
        self,
        card: Card,
        layout: Dict[str, tuple]
    ) -> List:
        """
        Convert simple layout (tuples) to PlacedElement list for VLM scoring.

        Args:
            card: Card object with text content
            layout: Dict mapping element_type to (x, y) position tuples

        Returns:
            List of PlacedElement objects
        """
        from src.models.placed_element import PlacedElement

        placed_elements = []
        for element_type, position in layout.items():
            if not isinstance(position, tuple):
                continue

            x, y = position

            # Extract text content from card
            text_content = ""
            if element_type == "name":
                text_content = card.name
            elif element_type == "type_line":
                text_content = card.type
            elif element_type == "mana_cost":
                text_content = str(card.mana_cost.symbols) if card.mana_cost else ""
            elif element_type == "abilities":
                text_content = "\n".join(card.abilities) if card.abilities else ""
            elif element_type == "power_toughness":
                text_content = card.power_toughness or ""
            elif element_type == "flavor_text":
                text_content = card.flavor_text or ""

            placed_elements.append(PlacedElement(
                element_type=element_type,
                text_content=text_content,
                position=(x, y),
                size=(100, 30),
                font_size=12,
                alignment='left'
            ))

        return placed_elements
