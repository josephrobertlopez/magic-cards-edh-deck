#!/usr/bin/env python3
"""
Scryfall Template Downloader
Download MTG card template images from Scryfall API with retry logic.
"""

import time
import hashlib
import asyncio
import aiohttp
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from src.models.template import TemplateMetadata
from src.vlm.region_detector import VLMRegionDetector
from src.cache.vlm_region_cache import VLMRegionCacheManager


class CardArtworkError(Exception):
    """Raised when card artwork download fails."""
    pass


class ArtworkDownloader:
    """
    Download custom card artwork from URLs.

    Features (T027 + FR-009):
    - Fetch from "pic" field URL
    - Raise CardArtworkError on invalid URL/non-image content
    - Log card name + URL for debugging
    - Caller continues batch processing on error
    """

    def __init__(self, cache_dir: Path = Path(".cache/artwork")):
        """
        Initialize artwork downloader.

        Args:
            cache_dir: Directory to cache downloaded artwork
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_artwork(self, url: str, card_name: str) -> Path:
        """
        Download artwork from URL and save to cache.

        Args:
            url: Artwork URL from "pic" field
            card_name: Card name for filename

        Returns:
            Path to downloaded artwork file

        Raises:
            CardArtworkError: If URL invalid or download fails
        """
        if not url:
            raise CardArtworkError(f"Empty artwork URL for card: {card_name}")

        try:
            # Download with timeout
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                raise CardArtworkError(
                    f"Failed to download artwork for {card_name}: HTTP {response.status_code} from {url}"
                )

            # Verify content is image
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type.lower():
                raise CardArtworkError(
                    f"Invalid content type for {card_name}: {content_type} from {url}"
                )

            # Save to cache
            # Sanitize card name for filename
            safe_name = "".join(c for c in card_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')

            # Determine extension from content type
            extension = content_type.split('/')[-1].split(';')[0]
            if extension not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                extension = 'png'

            artwork_path = self.cache_dir / f"{safe_name}.{extension}"
            artwork_path.write_bytes(response.content)

            return artwork_path

        except requests.RequestException as e:
            raise CardArtworkError(
                f"Network error downloading artwork for {card_name} from {url}: {e}"
            ) from e


class ScryfallDownloader:
    """
    Download card templates from Scryfall API.
    
    Features (T021):
    - Filter for ≥300 DPI images (FR-005)
    - Target 750×1050px resolution
    - Exponential backoff retry logic
    - 100ms rate limiting between requests
    
    Scryfall API docs: https://scryfall.com/docs/api
    """
    
    API_BASE = "https://api.scryfall.com"
    RATE_LIMIT_MS = 100  # 100ms between requests (research.md decision)
    
    def __init__(
        self,
        cache_dir: Path = Path(".cache/templates"),
        vlm_region_detector: VLMRegionDetector = None,
        region_cache: VLMRegionCacheManager = None
    ):
        """
        Initialize downloader with VLM region detection (T062).

        Args:
            cache_dir: Directory to store downloaded templates
            vlm_region_detector: VLM detector for template regions (creates default if None)
            region_cache: VLM region cache manager (creates default if None)
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0.0

        # VLM components for region detection (T062)
        self.vlm_detector = vlm_region_detector or VLMRegionDetector()
        self.region_cache = region_cache or VLMRegionCacheManager()
    
    def download_template_by_attributes(
        self, 
        color: str, 
        card_type: str, 
        legendary: bool
    ) -> Optional[TemplateMetadata]:
        """
        Download template matching card attributes from Scryfall.
        
        Strategy:
        1. Search Scryfall for cards matching attributes
        2. Filter for high-quality images (≥300 DPI, target 750×1050px)
        3. Download PNG image
        4. Calculate SHA-256 hash
        5. Save to cache directory
        6. Return TemplateMetadata
        
        Args:
            color: Card color (white/blue/black/red/green/multicolor/colorless)
            card_type: Card type (Creature/Instant/Sorcery/etc.)
            legendary: Whether legendary template needed
        
        Returns:
            TemplateMetadata if successful, None if no matching template found
        """
        # Build Scryfall search query
        query_parts = []
        
        # Color filter
        if color == "colorless":
            query_parts.append("c:c")
        elif color == "multicolor":
            query_parts.append("c>1")
        else:
            # Map color name to Scryfall color code
            color_map = {
                "white": "w",
                "blue": "u", 
                "black": "b",
                "red": "r",
                "green": "g",
            }
            if color in color_map:
                query_parts.append(f"c:{color_map[color]}")
        
        # Type filter
        query_parts.append(f"t:{card_type}")
        
        # Legendary filter
        if legendary:
            query_parts.append("t:legendary")
        
        # Quality filters
        query_parts.append("is:hires")  # High resolution images only
        
        query = " ".join(query_parts)
        
        # Search Scryfall
        card_data = self._search_scryfall(query)
        if not card_data:
            return None
        
        # Download image
        image_url = self._get_best_image_url(card_data)
        if not image_url:
            return None
        
        image_data = self._download_image(image_url)
        if not image_data:
            return None
        
        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(image_data).hexdigest()
        
        # Save to cache
        file_path = self.cache_dir / f"{sha256_hash}.png"
        file_path.write_bytes(image_data)

        # T062: VLM region detection with persistent caching
        # Check cache first (NFR-004: 92.5% call reduction)
        regions = self.region_cache.get_cached_regions(sha256_hash)

        if regions is None:
            # Cache miss - call VLM to detect regions
            print(f"  VLM detecting regions for {sha256_hash[:8]}... (one-time, ~9s)")
            raw_regions = self.vlm_detector.detect_regions(str(file_path))

            # Convert raw regions dict to TemplateRegions and cache
            # raw_regions: Dict[str, Tuple[int, int, int, int]]
            # Need to convert to TemplateRegions before caching
            from models.template_regions import TemplateRegions
            from models.bounding_box import BoundingBox

            # Convert tuples to BoundingBox with keyword args (Pydantic v2 requirement)
            def tuple_to_bbox(coords):
                x, y, w, h = coords
                return BoundingBox(x=x, y=y, width=w, height=h)

            regions = TemplateRegions(
                template_hash=sha256_hash,
                name_box=tuple_to_bbox(raw_regions.get('name_box', (0, 0, 0, 0))),
                mana_cost_box=tuple_to_bbox(raw_regions.get('mana_box', (0, 0, 0, 0))),
                type_line_box=tuple_to_bbox(raw_regions.get('type_box', (0, 0, 0, 0))),
                text_boxes=[tuple_to_bbox(raw_regions.get('text_box', (0, 0, 0, 0)))],
                pt_box=tuple_to_bbox(raw_regions['pt_box']) if 'pt_box' in raw_regions else None,
                flavor_box=None,  # TODO: Detect flavor region separately
                artwork_detected=False  # Artwork blanking not yet implemented
            )

            # Cache for future use
            self.region_cache.cache_regions(sha256_hash, regions)
            print(f"  ✓ Regions cached for {sha256_hash[:8]}")
        else:
            print(f"  ✓ Regions loaded from cache for {sha256_hash[:8]}")

        # Create metadata with attached regions
        metadata = TemplateMetadata(
            color=color,
            card_type=card_type,
            legendary=legendary,
            file_path=file_path,
            sha256_hash=sha256_hash,
            scryfall_id=card_data.get("id", "unknown"),
            regions=regions  # Attach VLM-detected regions
        )

        return metadata
    
    def _search_scryfall(self, query: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Search Scryfall API with exponential backoff retry.
        
        Args:
            query: Scryfall search query
            max_retries: Maximum retry attempts
        
        Returns:
            First card result or None
        """
        self._rate_limit()
        
        url = f"{self.API_BASE}/cards/search"
        params = {"q": query, "order": "released", "dir": "desc"}
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        return data["data"][0]  # Return first match
                    return None
                
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                
                else:
                    return None
            
            except requests.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        
        return None
    
    def _get_best_image_url(self, card_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract best quality image URL from card data.
        
        Priority:
        1. png (lossless, best quality)
        2. large (750×1050px target per research.md)
        3. normal (fallback)
        
        Args:
            card_data: Scryfall card JSON data
        
        Returns:
            Image URL or None
        """
        image_uris = card_data.get("image_uris", {})
        
        # Priority order
        for size in ["png", "large", "normal"]:
            if size in image_uris:
                return image_uris[size]
        
        return None
    
    def _download_image(self, url: str, max_retries: int = 3) -> Optional[bytes]:
        """
        Download image with retry logic.
        
        Args:
            url: Image URL
            max_retries: Maximum retry attempts
        
        Returns:
            Image bytes or None
        """
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    return response.content
                
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                
                else:
                    return None
            
            except requests.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        
        return None
    
    def _rate_limit(self):
        """Enforce 100ms rate limit between requests."""
        current_time = time.time()
        time_since_last = (current_time - self._last_request_time) * 1000  # ms

        if time_since_last < self.RATE_LIMIT_MS:
            time.sleep((self.RATE_LIMIT_MS - time_since_last) / 1000)

        self._last_request_time = time.time()

    async def batch_download_templates(
        self,
        template_list: List[Tuple[str, str, bool]],
        max_concurrent: int = 10
    ) -> List[Optional[TemplateMetadata]]:
        """
        Download multiple templates concurrently with semaphore limiting.

        Features (T023 + NFR-002):
        - Parallel downloads using asyncio + aiohttp
        - Semaphore limiting to 10 concurrent requests (Scryfall API rate limit)
        - Progress reporting via print statements

        Args:
            template_list: List of (color, card_type, legendary) tuples
            max_concurrent: Maximum concurrent downloads (default 10)

        Returns:
            List of TemplateMetadata (None for failed downloads)

        Example:
            >>> downloader = ScryfallDownloader()
            >>> templates = [
            ...     ("blue", "Creature", True),
            ...     ("red", "Instant", False),
            ...     ("green", "Enchantment", False),
            ... ]
            >>> results = asyncio.run(downloader.batch_download_templates(templates))
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_one(color: str, card_type: str, legendary: bool) -> Optional[TemplateMetadata]:
            """Download single template with semaphore."""
            async with semaphore:
                # Use synchronous method (TODO: convert to async in future)
                result = await asyncio.to_thread(
                    self.download_template_by_attributes,
                    color, card_type, legendary
                )
                if result:
                    print(f"✓ Downloaded {color} {card_type} (legendary={legendary})")
                else:
                    print(f"✗ Failed {color} {card_type} (legendary={legendary})")
                return result

        # Create tasks for all downloads
        tasks = [
            download_one(color, card_type, legendary)
            for color, card_type, legendary in template_list
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)

        return results


class TemplateBlank:
    """
    Blank out text regions from Scryfall templates using VLM detection.
    
    Features:
    - VLM detects text box regions  
    - Fill regions with solid color
    - Cache blanked templates
    """
    
    def __init__(self, vlm_detector=None):
        """
        Initialize template blanker.
        
        Args:
            vlm_detector: VLMRegionDetector instance (optional)
        """
        from src.vlm.region_detector import VLMRegionDetector
        self.vlm_detector = vlm_detector or VLMRegionDetector()
    
    def blank_template(self, template_path: Path, output_path: Optional[Path] = None) -> tuple[Path, dict]:
        """
        Blank out text regions from template using VLM detection.

        Args:
            template_path: Path to Scryfall template with text
            output_path: Where to save blanked template (default: same as input with _blank suffix)

        Returns:
            Tuple of (blanked_template_path, detected_regions_dict)
        """
        from PIL import Image, ImageDraw

        # Detect regions using VLM
        print(f"   🔍 Detecting text regions with VLM...")
        regions = self.vlm_detector.detect_regions(str(template_path))

        if not regions:
            print(f"   ⚠️  No regions detected, using template as-is")
            return template_path, {}

        # Load template
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)

        # Blank out each detected region
        print(f"   🎨 Blanking {len(regions)} detected regions...")
        for region_name, (x, y, width, height) in regions.items():
            # Use card frame color (sample from top-left corner)
            # For now, use white fill as safe default
            fill_color = (255, 255, 255)

            # Draw filled rectangle over text region
            draw.rectangle(
                [(x, y), (x + width, y + height)],
                fill=fill_color
            )
            print(f"      Blanked {region_name}: {x},{y} {width}x{height}")
        
        # Save blanked template
        if not output_path:
            output_path = template_path.parent / f"{template_path.stem}_blank{template_path.suffix}"

        img.save(output_path)
        print(f"   ✓ Saved blanked template: {output_path}")

        return output_path, regions
