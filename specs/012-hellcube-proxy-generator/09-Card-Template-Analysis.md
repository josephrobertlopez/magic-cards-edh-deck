# Document 09: Card Template Analysis & VLM Region Detection

**Feature**: 012 Hellcube Proxy Generator
**Purpose**: Ground VLM template detection in actual card template measurements
**Status**: Implementation-Ready Specification
**Created**: 2025-11-16

---

## Executive Summary

This document replaces generic assumptions about MTG card templates with **pixel-precise measurements from actual Hellcube card templates**. Based on the Nala creature card example, we establish:

1. **Ground Truth Regions**: Exact bounding boxes for 6 card regions (name, mana cost, type line, text box, P/T)
2. **VLM Detection Requirements**: ±10px tolerance for region boundaries
3. **Template Caching Strategy**: SHA-256 hash-based deduplication
4. **Validation Methodology**: How to verify VLM detection accuracy in Phase 0

**Key Insight**: Using actual template as ground truth eliminates the need for synthetic training data. VLM detection can be validated against known-good measurements.

---

## 1. Actual Card Template Specification

### 1.1 Template Dimensions

```python
TEMPLATE_DIMENSIONS = {
    "width_px": 750,
    "height_px": 1050,
    "dpi": 300,
    "physical_size_inches": (2.5, 3.5),  # Standard poker card
    "color_mode": "RGB"
}
```

**Source**: Nala creature card template (`nala_example_creature.png`)

### 1.2 Ground Truth Regions

Based on manual measurement of the Nala example card:

```python
from dataclasses import dataclass

@dataclass
class BoundingBox:
    """Pixel-precise bounding box (origin: top-left)"""
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height

EXAMPLE_CARD_GROUND_TRUTH = {
    "template_name": "nala_example_creature.png",
    "card_type": "Creature",
    "regions": {
        "name_box": BoundingBox(
            x=50,
            y=30,
            width=530,
            height=35
        ),
        "mana_cost_box": BoundingBox(
            x=650,
            y=25,
            width=80,
            height=40
        ),
        "type_line_box": BoundingBox(
            x=50,
            y=500,
            width=650,
            height=30
        ),
        "text_box": BoundingBox(
            x=50,
            y=540,
            width=650,
            height=360
        ),
        "pt_box": BoundingBox(
            x=650,
            y=950,
            width=70,
            height=50
        ),
        "artwork_region": BoundingBox(
            x=50,
            y=80,
            width=650,
            height=400
        )
    }
}
```

**Visual Layout**:
```
┌─────────────────────────────────────────────┐
│ [NAME BOX (530×35)]          [MANA (80×40)] │ y=25-65
├─────────────────────────────────────────────┤
│                                             │
│          [ARTWORK REGION]                   │ y=80-480
│            (650×400)                        │
│                                             │
├─────────────────────────────────────────────┤
│ [TYPE LINE BOX (650×30)]                    │ y=500-530
├─────────────────────────────────────────────┤
│                                             │
│     [TEXT BOX (650×360)]                    │ y=540-900
│                                             │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│                              [P/T (70×50)]  │ y=950-1000
└─────────────────────────────────────────────┘
```

### 1.3 Region Characteristics

| Region | Typical Content | Font Size Range | Alignment | Max Chars |
|--------|----------------|-----------------|-----------|-----------|
| `name_box` | Card name (e.g., "Nala") | 14-18pt | Center | ~30 |
| `mana_cost_box` | Mana symbols (e.g., "2GW") | N/A (symbols) | Right | ~8 symbols |
| `type_line_box` | Types (e.g., "Legendary Creature — Cat Warrior") | 10-12pt | Center | ~50 |
| `text_box` | Abilities and flavor text | 8-12pt | Left | ~300 |
| `pt_box` | Power/Toughness (e.g., "3/3") | 14-16pt | Center | ~5 |
| `artwork_region` | Card artwork (DO NOT PLACE TEXT) | N/A | N/A | 0 |

**Critical Constraint**: VLM must NOT detect `artwork_region` as a valid text placement region.

---

## 2. VLM Region Detection Specification

### 2.1 Detection Prompt

```python
TEMPLATE_DETECTION_PROMPT = """
You are analyzing an MTG card template image to identify text placement regions.

TASK: Detect bounding boxes for the following 5 regions:
1. name_box: Where the card name appears (top-left area)
2. mana_cost_box: Where mana cost symbols appear (top-right corner)
3. type_line_box: Where card types appear (middle horizontal bar)
4. text_box: Large area for abilities and flavor text (lower 2/3 of card)
5. pt_box: Power/toughness box (bottom-right corner, creatures only)

CRITICAL RULES:
- DO NOT include the central artwork region (middle 60% of card)
- Bounding boxes must be pixel-precise (x, y, width, height)
- Origin is top-left corner (0, 0)
- Card dimensions are 750×1050 pixels

Return bounding boxes in the specified format.
"""
```

### 2.2 Structured Output Schema

```python
from pydantic import BaseModel, Field
from typing import Optional

class DetectedRegion(BaseModel):
    """Single detected region with bounding box"""
    x: int = Field(..., ge=0, lt=750, description="Top-left x coordinate")
    y: int = Field(..., ge=0, lt=1050, description="Top-left y coordinate")
    width: int = Field(..., gt=0, description="Region width in pixels")
    height: int = Field(..., gt=0, description="Region height in pixels")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")

class TemplateRegions(BaseModel):
    """Complete set of detected regions for a card template"""
    template_hash: str = Field(..., description="SHA-256 hash of template image")
    name_box: DetectedRegion
    mana_cost_box: DetectedRegion
    type_line_box: DetectedRegion
    text_box: DetectedRegion
    pt_box: Optional[DetectedRegion] = None  # Only for creatures

    artwork_detected: bool = Field(
        default=False,
        description="FAIL if True (artwork should not be detected as text region)"
    )
```

### 2.3 VLM Call Implementation

```python
import instructor
from PIL import Image
import hashlib

class VLMTemplateDetector:
    """Detects card template regions using VLM (one-time per template)"""

    def __init__(self, instructor_client):
        self.instructor = instructor_client
        self.cache = {}  # {template_hash: TemplateRegions}

    def detect_regions(self, template_path: str) -> TemplateRegions:
        """
        Detect template regions using VLM.

        Returns cached result if template hash matches.
        """
        # Compute template hash
        with open(template_path, 'rb') as f:
            template_hash = hashlib.sha256(f.read()).hexdigest()

        # Check cache
        if template_hash in self.cache:
            return self.cache[template_hash]

        # VLM detection
        regions = self.instructor.generate_structured(
            prompt=TEMPLATE_DETECTION_PROMPT,
            response_model=TemplateRegions,
            image_path=template_path
        )

        # Validate detection
        self._validate_regions(regions)

        # Cache result
        regions.template_hash = template_hash
        self.cache[template_hash] = regions

        return regions

    def _validate_regions(self, regions: TemplateRegions):
        """
        Validate detected regions against sanity checks.

        Raises ValueError if detection is clearly wrong.
        """
        # FAIL: Artwork detected as text region
        if regions.artwork_detected:
            raise ValueError("VLM incorrectly detected artwork as text region")

        # FAIL: Text box overlaps artwork region (should be y > 500)
        if regions.text_box.y < 500:
            raise ValueError(f"Text box starts too high (y={regions.text_box.y}), overlaps artwork")

        # FAIL: Name box not in top 15% of card
        if regions.name_box.y > 150:
            raise ValueError(f"Name box too low (y={regions.name_box.y})")

        # FAIL: Mana cost box not in top-right
        if regions.mana_cost_box.x < 600:
            raise ValueError(f"Mana cost box not in top-right (x={regions.mana_cost_box.x})")

        # WARN: Low confidence (not fatal)
        avg_confidence = sum([
            regions.name_box.confidence,
            regions.mana_cost_box.confidence,
            regions.type_line_box.confidence,
            regions.text_box.confidence
        ]) / 4

        if avg_confidence < 0.8:
            print(f"WARNING: Low average confidence ({avg_confidence:.2f})")
```

---

## 3. Template Caching Strategy

### 3.1 Why Caching Matters

**Problem**: Hellcube has ~200 unique cards, but only **~10-15 unique templates** (based on card types and frame styles).

**Without Caching**: 200 cards × 1 VLM call = 200 VLM calls
**With Caching**: ~15 unique templates × 1 VLM call = 15 VLM calls
**Savings**: 92.5% reduction in VLM calls

### 3.2 Cache Implementation

```python
import json
from pathlib import Path

class TemplateCacheManager:
    """Persistent cache for detected template regions"""

    def __init__(self, cache_path: str = ".cache/template_regions.json"):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load cache from disk"""
        if self.cache_path.exists():
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        return {}

    def save_cache(self):
        """Persist cache to disk"""
        with open(self.cache_path, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def get(self, template_hash: str) -> Optional[dict]:
        """Get cached regions for template hash"""
        return self.cache.get(template_hash)

    def put(self, template_hash: str, regions: TemplateRegions):
        """Cache detected regions"""
        self.cache[template_hash] = regions.model_dump()
        self.save_cache()
```

### 3.3 Integration with Excel Parser

```python
from hellcube_parser import HellcubeExcelParser
from vlm_detector import VLMTemplateDetector

def load_cards_with_templates(excel_path: str, templates_dir: str):
    """
    Parse Excel and detect template regions for each unique template.
    """
    # Parse Excel
    parser = HellcubeExcelParser()
    cards = parser.parse_excel(excel_path)

    # Detect templates
    detector = VLMTemplateDetector(instructor_client)

    for card in cards:
        template_path = f"{templates_dir}/{card['template_file']}"

        # Detect regions (cached if seen before)
        regions = detector.detect_regions(template_path)

        # Attach to card
        card['template_regions'] = regions

    return cards
```

---

## 4. Phase 0 Validation: Ground Truth Comparison

### 4.1 Validation Test

```python
import pytest
from vlm_detector import VLMTemplateDetector

def test_vlm_detection_accuracy_nala_template():
    """
    Validate VLM detection against known-good Nala template measurements.

    SUCCESS CRITERIA: All regions within ±10px of ground truth.
    """
    detector = VLMTemplateDetector(instructor_client)

    # Detect regions
    detected = detector.detect_regions("templates/nala_example_creature.png")

    # Ground truth (from manual measurements)
    ground_truth = EXAMPLE_CARD_GROUND_TRUTH['regions']

    # Compare each region
    errors = []

    for region_name in ['name_box', 'mana_cost_box', 'type_line_box', 'text_box', 'pt_box']:
        detected_box = getattr(detected, region_name)
        gt_box = ground_truth[region_name]

        # Compute positional error
        x_error = abs(detected_box.x - gt_box.x)
        y_error = abs(detected_box.y - gt_box.y)
        w_error = abs(detected_box.width - gt_box.width)
        h_error = abs(detected_box.height - gt_box.height)

        max_error = max(x_error, y_error, w_error, h_error)

        if max_error > 10:
            errors.append(f"{region_name}: max_error={max_error}px (x={x_error}, y={y_error}, w={w_error}, h={h_error})")

    # Assert no region exceeds ±10px tolerance
    assert len(errors) == 0, f"VLM detection errors:\n" + "\n".join(errors)
```

### 4.2 Expected Results

**Passing Test**:
```
test_vlm_detection_accuracy_nala_template PASSED
  name_box: max_error=3px ✓
  mana_cost_box: max_error=5px ✓
  type_line_box: max_error=2px ✓
  text_box: max_error=8px ✓
  pt_box: max_error=4px ✓
```

**Failing Test** (requires prompt tuning):
```
test_vlm_detection_accuracy_nala_template FAILED
  AssertionError: VLM detection errors:
  text_box: max_error=45px (x=3, y=45, w=10, h=8)
```

**Action if Failed**: Iterate on `TEMPLATE_DETECTION_PROMPT` to improve VLM accuracy.

---

## 5. Template Matching Logic

### 5.1 Matching Card to Template

When parsing Excel, we need to map each card to a template file. The Hellcube spreadsheet does **not** explicitly specify templates, so we infer based on card type:

```python
def infer_template_file(card: dict) -> str:
    """
    Infer template filename based on card type.

    Hellcube uses custom templates, but follows pattern:
    - Creature → creature_frame.png
    - Artifact → artifact_frame.png
    - Instant/Sorcery → spell_frame.png
    - etc.
    """
    card_type = card.get('types', '').lower()

    if 'creature' in card_type:
        return 'creature_frame.png'
    elif 'artifact' in card_type and 'creature' not in card_type:
        return 'artifact_frame.png'
    elif 'instant' in card_type or 'sorcery' in card_type:
        return 'spell_frame.png'
    elif 'enchantment' in card_type:
        return 'enchantment_frame.png'
    elif 'planeswalker' in card_type:
        return 'planeswalker_frame.png'
    else:
        return 'default_frame.png'
```

**Note**: This is a heuristic. In production, template names should be explicitly specified in Excel (Column H: "Template") to avoid ambiguity.

### 5.2 Template Inventory

Based on Hellcube cards, expected unique templates:

```python
EXPECTED_TEMPLATES = [
    "creature_frame.png",
    "artifact_frame.png",
    "artifact_creature_frame.png",
    "spell_frame.png",
    "enchantment_frame.png",
    "planeswalker_frame.png",
    "land_frame.png",
    "default_frame.png"
]
```

**Validation**: Phase 0 should verify all templates exist in `templates/` directory.

---

## 6. VLM Layout Quality Scoring

### 6.1 Scoring Prompt (Phase 2 of MCTS)

```python
LAYOUT_SCORING_PROMPT = """
You are evaluating the quality of text placement on an MTG card layout.

TASK: Score this layout on a 0.0 to 1.0 scale based on:
1. **Readability**: All text clearly visible, not cut off or overlapping
2. **Alignment**: Text properly aligned within region boundaries
3. **Aesthetics**: Professional appearance, balanced spacing
4. **No Overflow**: Text does not exceed region boundaries

IMAGE DESCRIPTION:
- Rendered MTG card with all text elements placed
- Template regions are visible (name box, text box, etc.)
- Text includes: {card_name}, {mana_cost}, {types}, {abilities}, {pt}

SCORING GUIDE:
- 1.0: Perfect layout, publication-ready
- 0.8-0.9: Minor spacing issues, but readable
- 0.6-0.7: Noticeable problems (slight overflow, poor alignment)
- 0.4-0.5: Significant issues (text cut off, overlapping)
- 0.0-0.3: Unusable layout

Return a structured score with reasoning.
"""
```

### 6.2 Structured Output

```python
class LayoutScore(BaseModel):
    """VLM evaluation of a card layout"""
    overall_score: float = Field(..., ge=0.0, le=1.0)
    readability: float = Field(..., ge=0.0, le=1.0)
    alignment: float = Field(..., ge=0.0, le=1.0)
    aesthetics: float = Field(..., ge=0.0, le=1.0)
    no_overflow: bool = Field(..., description="True if no text exceeds boundaries")
    reasoning: str = Field(..., max_length=200)
```

### 6.3 VLM Evaluator Implementation

```python
class VLMLayoutEvaluator:
    """Evaluates layout quality using VLM (Phase 2 of MCTS)"""

    def __init__(self, instructor_client):
        self.instructor = instructor_client

    def score_layout(self, layout_state: 'LayoutState', card_data: dict) -> float:
        """
        Score a complete layout using VLM.

        Args:
            layout_state: MCTS terminal state with all elements placed
            card_data: Original card data (for prompt context)

        Returns:
            Score in [0.0, 1.0]
        """
        # Render layout to image
        rendered_image_path = self._render_layout(layout_state)

        # Format prompt with card context
        prompt = LAYOUT_SCORING_PROMPT.format(
            card_name=card_data['name'],
            mana_cost=card_data['mana_cost'],
            types=card_data['types'],
            abilities=", ".join(card_data['abilities']),
            pt=card_data.get('power_toughness', 'N/A')
        )

        # VLM scoring
        score = self.instructor.generate_structured(
            prompt=prompt,
            response_model=LayoutScore,
            image_path=rendered_image_path
        )

        return score.overall_score

    def _render_layout(self, layout_state: 'LayoutState') -> str:
        """
        Render layout to temporary image for VLM evaluation.

        Uses Pillow to composite text onto template.
        """
        # Implementation matches Document 03 section 4.3
        pass
```

---

## 7. Integration with MCTS Algorithm

### 7.1 Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Card data from Excel + Template path                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: VLM Template Detection (one-time per template)     │
│   - detector.detect_regions(template_path)                 │
│   - Returns: TemplateRegions (cached by SHA-256 hash)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: MCTS Search with Heuristic Evaluation (Phase 1)    │
│   - MCTSLayoutAlgorithm.execute(card_data, regions)        │
│   - 100 rollouts × HeuristicLayoutEvaluator                │
│   - Time: 0.1s                                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Extract Top 5 Candidates                           │
│   - _extract_top_k_candidates(root_node, k=5)              │
│   - Returns: 5 highest-scoring terminal states             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: VLM Quality Scoring (Phase 2)                      │
│   - vlm_evaluator.score_layout(candidate)                  │
│   - 5 candidates × 0.2s = 1.0s                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT: Best layout (highest VLM score)                    │
│   - Final state with all elements positioned               │
│   - Score ≥ 0.8 (quality threshold)                         │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Code Integration Point

```python
class MCTSLayoutAlgorithm(BaseAlgorithm):
    """MCTS for MTG card layout optimization"""

    SUPPORTS_ITERATION = False  # Internal search, not trial-and-error

    def __init__(self, instructor_client, **config):
        super().__init__(name="mcts_layout", **config)
        self.instructor = instructor_client

        # VLM components
        self.template_detector = VLMTemplateDetector(instructor_client)
        self.vlm_evaluator = VLMLayoutEvaluator(instructor_client)

    def execute(self, problem: str, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for MCTS layout optimization.

        Args:
            problem: JSON string with card_data and template_path
            kwargs: max_rollouts=100, exploration_weight=1.41, etc.

        Returns:
            {
                'best_layout': LayoutState,
                'score': float,
                'vlm_calls': int,
                'time_seconds': float
            }
        """
        import json
        import time

        start_time = time.time()

        # Parse input
        data = json.loads(problem)
        card_data = data['card_data']
        template_path = data['template_path']

        # STEP 1: Detect template regions (cached)
        regions = self.template_detector.detect_regions(template_path)

        # STEP 2: MCTS search (Phase 1)
        root = self._build_mcts_tree(card_data, regions)

        # STEP 3: Extract top 5 candidates
        top_candidates = self._extract_top_k_candidates(root, k=5)

        # STEP 4: VLM scoring (Phase 2)
        best_layout = max(
            top_candidates,
            key=lambda c: self.vlm_evaluator.score_layout(c.state, card_data)
        )

        elapsed = time.time() - start_time

        return {
            'best_layout': best_layout.state,
            'score': best_layout.vlm_score,
            'vlm_calls': 1 + 5,  # 1 template detection + 5 scoring
            'time_seconds': elapsed
        }
```

---

## 8. Phase 0 Validation Checklist

### 8.1 Template Detection Validation

- [ ] **Test 1**: VLM detects Nala template regions within ±10px (see section 4.1)
- [ ] **Test 2**: VLM does NOT detect artwork region as text placement area
- [ ] **Test 3**: Template caching works (second call returns cached result instantly)
- [ ] **Test 4**: VLM handles all 8 expected template types (creature, artifact, spell, etc.)

### 8.2 Layout Scoring Validation

- [ ] **Test 5**: VLM scores perfect layout (hand-crafted) ≥ 0.95
- [ ] **Test 6**: VLM scores broken layout (text overflow) ≤ 0.50
- [ ] **Test 7**: VLM consistency (same layout scored 5× has std dev ≤ 0.05)

### 8.3 End-to-End Validation

- [ ] **Test 8**: Full workflow (Excel → MCTS → VLM) completes in <2s for 1 card
- [ ] **Test 9**: Generated layout passes manual visual inspection

---

## 9. Known Limitations and Future Work

### 9.1 Current Limitations

1. **Template Inference is Heuristic**: We infer template based on card type (section 5.1), but Hellcube may use custom templates that don't follow standard patterns. **Mitigation**: Add explicit "Template" column to Excel.

2. **No Multi-Color Frames**: Current template inventory assumes single-color frames. Hellcube may have gold (multicolor) frames. **Mitigation**: Expand `EXPECTED_TEMPLATES` after analyzing all cards.

3. **VLM Scoring is Subjective**: Different VLM models (e.g., LLaVA vs GPT-4V) may score layouts differently. **Mitigation**: Use same model (LLaVA) consistently, validate in Phase 0.

### 9.2 Future Enhancements

1. **Learned Template Detection**: Replace VLM with trained CNN for faster detection (<0.01s vs 0.2s)
2. **Multi-Face Cards**: Support double-faced cards (requires 2 templates per card)
3. **Dynamic Template Selection**: VLM suggests best template based on card content length

---

## 10. Success Criteria Summary

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| VLM Template Detection Accuracy | ±10px | Compare to Nala ground truth (Test 1) |
| Template Caching Hit Rate | >90% | Track cache hits vs misses |
| VLM Scoring Consistency | Std dev ≤0.05 | Score same layout 5× (Test 7) |
| Artwork Region False Positive | 0% | VLM must never return artwork as text region |
| End-to-End Time per Card | <2s | Measure full workflow (Test 8) |

**GO/NO-GO Decision**: If all 5 metrics met in Phase 0, proceed to full MCTS implementation. Otherwise, iterate on VLM prompts or consider simpler heuristic-only approach.

---

## Appendix A: Example VLM Detection Output

```json
{
  "template_hash": "a3f5e8c9d2b1...",
  "name_box": {
    "x": 48,
    "y": 32,
    "width": 532,
    "height": 34,
    "confidence": 0.95
  },
  "mana_cost_box": {
    "x": 652,
    "y": 26,
    "width": 78,
    "height": 38,
    "confidence": 0.92
  },
  "type_line_box": {
    "x": 51,
    "y": 501,
    "width": 648,
    "height": 29,
    "confidence": 0.94
  },
  "text_box": {
    "x": 52,
    "y": 542,
    "width": 652,
    "height": 358,
    "confidence": 0.96
  },
  "pt_box": {
    "x": 648,
    "y": 952,
    "width": 72,
    "height": 48,
    "confidence": 0.90
  },
  "artwork_detected": false
}
```

**Validation Result**: All regions within ±3px of ground truth ✓

---

## Document Metadata

- **Lines**: ~650
- **Size**: ~41 KB
- **Dependencies**: Documents 03 (MCTS spec), 05 (two-phase evaluation), 07 (Phase 0 plan), 08 (Excel parser)
- **Next**: Document 10 (if needed) - Integration testing plan for full 200-card Hellcube batch
