# VLM Evaluators Contract

**Module**: `../monorepo/agentic/algorithms/mcts/vlm_evaluators.py`
**Purpose**: VLM-based template detection and layout quality evaluation

---

## Class: VLMTemplateDetector

**Purpose**: One-time detection of template regions using VLM

---

### __init__()

**Signature**:
```python
def __init__(self, instructor_client, percept_interface=None):
    """
    Initialize VLM template detector.

    Args:
        instructor_client: Instructor framework client
        percept_interface: Optional PerceptInterface for VLM backend

    Attributes:
        self.cache: Dict[str, TemplateRegions] (template_hash → regions)
    """
```

---

### detect_regions()

**Signature**:
```python
def detect_regions(self, template_path: str) -> TemplateRegions:
    """
    Detect template regions using VLM (cached by SHA-256 hash).

    Args:
        template_path: Absolute path to template image (750×1050px PNG)

    Returns:
        TemplateRegions: Pydantic model with detected bounding boxes

    Raises:
        FileNotFoundError: If template image doesn't exist
        VLMDetectionError: If VLM fails to detect regions or detects artwork as text region
        ValidationError: If detected regions fail sanity checks

    Caching:
        - Computes SHA-256 hash of template image
        - Returns cached result if hash matches
        - Saves to persistent cache (.cache/template_regions.json)
    """
```

**Input Example**:
```python
detector = VLMTemplateDetector(instructor_client)
regions = detector.detect_regions("templates/blue_creature.png")
```

**Output Example**:
```python
TemplateRegions(
    template_hash="a3f5e8c9d2b1...",
    name_box=BoundingBox(x=48, y=32, width=532, height=34),
    mana_cost_box=BoundingBox(x=652, y=26, width=78, height=38),
    type_line_box=BoundingBox(x=51, y=501, width=648, height=29),
    text_boxes=[BoundingBox(x=52, y=542, width=652, height=358)],
    pt_box=BoundingBox(x=648, y=952, width=72, height=48),
    flavor_box=None,
    artwork_detected=False  # MUST be False
)
```

**VLM Prompt**:
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

**Implementation**:
```python
def detect_regions(self, template_path: str) -> TemplateRegions:
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
    self.save_cache()

    return regions
```

---

### _validate_regions() (private)

**Signature**:
```python
def _validate_regions(self, regions: TemplateRegions):
    """
    Validate detected regions against sanity checks.

    Args:
        regions: VLM-detected template regions

    Raises:
        VLMDetectionError: If detection is clearly wrong

    Checks:
        - artwork_detected == False (FAIL if artwork detected as text)
        - text_box.y > 500 (should not overlap artwork region)
        - name_box.y < 150 (must be in top 15% of card)
        - mana_cost_box.x > 600 (must be in top-right)
        - Average confidence >= 0.8 (warn if lower)
    """
```

---

### save_cache() / _load_cache()

**Signature**:
```python
def save_cache(self):
    """Persist cache to .cache/template_regions.json"""

def _load_cache(self) -> dict:
    """Load cache from disk (called in __init__)"""
```

**Cache Format** (JSON):
```json
{
  "a3f5e8c9d2b1...": {
    "name_box": {"x": 50, "y": 30, "width": 530, "height": 35},
    "mana_cost_box": {"x": 650, "y": 25, "width": 80, "height": 40},
    "type_line_box": {"x": 50, "y": 500, "width": 650, "height": 30},
    "text_boxes": [{"x": 50, "y": 540, "width": 650, "height": 360}],
    "pt_box": {"x": 650, "y": 950, "width": 70, "height": 50},
    "flavor_box": null,
    "artwork_detected": false
  }
}
```

---

## Class: VLMLayoutEvaluator

**Purpose**: Score completed layouts using VLM (called every MCTS rollout)

---

### __init__()

**Signature**:
```python
def __init__(self, instructor_client, percept_interface=None):
    """
    Initialize VLM layout evaluator.

    Args:
        instructor_client: Instructor framework client
        percept_interface: Optional PerceptInterface for VLM backend
    """
```

---

### score_layout()

**Signature**:
```python
def score_layout(self, layout_state: LayoutState, card_data: Dict = None) -> float:
    """
    Score a completed layout using VLM.

    Args:
        layout_state: MCTS terminal state (all elements placed)
        card_data: Optional card context for prompt (name, abilities, etc.)

    Returns:
        float: Overall quality score [0.0-1.0]

    Raises:
        ValueError: If layout_state is not terminal (remaining_elements not empty)
        VLMEvaluationError: If VLM fails to score layout

    Performance:
        - VLM latency: ~0.2s per call (Ollama llava-1.5)
        - Called 100-300 times per card (every MCTS rollout)
    """
```

**Input Example**:
```python
evaluator = VLMLayoutEvaluator(instructor_client)

layout_state = LayoutState(
    placed_elements=[
        PlacedElement(...),  # name
        PlacedElement(...),  # mana_cost
        # ... all elements placed
    ],
    remaining_elements=[],  # Terminal state
    quality_score=None
)

score = evaluator.score_layout(layout_state, card_data={'name': 'Grizzly Bears'})
# Returns: 0.88
```

**VLM Prompt**:
```python
LAYOUT_SCORING_PROMPT = """
You are evaluating the quality of text placement on an MTG card layout.

TASK: Score this layout on a 0.0 to 1.0 scale based on:
1. **Readability**: All text clearly visible, not cut off or overlapping
2. **Convention compliance**: MTG layout standards (name centered, abilities left-aligned)
3. **Aesthetic balance**: Professional appearance, balanced spacing

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

**Implementation**:
```python
def score_layout(self, layout_state: LayoutState, card_data: Dict = None) -> float:
    # Validate terminal state
    if not layout_state.is_terminal():
        raise ValueError("Layout must be terminal (all elements placed)")

    # Render layout to image
    rendered_image = self._render_layout(layout_state)

    # Format prompt with card context
    prompt = LAYOUT_SCORING_PROMPT.format(
        card_name=card_data.get('name', 'Unknown') if card_data else 'Unknown',
        mana_cost=str(card_data.get('mana_cost', '')) if card_data else '',
        types=card_data.get('type', '') if card_data else '',
        abilities=", ".join(card_data.get('abilities', [])) if card_data else '',
        pt=card_data.get('power_toughness', 'N/A') if card_data else 'N/A'
    )

    # VLM scoring
    quality = self.instructor.generate_structured(
        prompt=prompt,
        response_model=LayoutQuality,
        image_data=rendered_image  # PIL Image object
    )

    return quality.overall_score
```

---

### _render_layout() (private)

**Signature**:
```python
def _render_layout(self, layout_state: LayoutState) -> PIL.Image:
    """
    Render layout to PIL Image for VLM evaluation.

    Args:
        layout_state: Terminal layout state

    Returns:
        PIL.Image: 750×1050px RGB image with text composited onto template

    Uses:
        - PIL.ImageDraw for text rendering
        - Appropriate font sizes from PlacedElement.font_size
        - Text alignment from PlacedElement.alignment
    """
```

---

## Error Classes

```python
class VLMDetectionError(Exception):
    """Raised when VLM template detection fails or produces invalid results"""
    pass

class VLMEvaluationError(Exception):
    """Raised when VLM layout scoring fails"""
    pass
```

---

## Performance Contract

**VLMTemplateDetector**:
- **Calls per Feature**: ~15 (unique templates) for 200-card batch
- **Cache Hit Rate**: >90% (after first template of each type detected)
- **Latency**: 0.2s per detection (Ollama llava-1.5)

**VLMLayoutEvaluator**:
- **Calls per Card**: 100-300 (every MCTS rollout)
- **Calls per 200-Card Batch**: ~20,000
- **Latency**: 0.2s per evaluation (Ollama llava-1.5)
- **Total VLM Time**: ~1.1 hours for 200 cards (20,000 × 0.2s)

---

## Testing Contract

**Phase 0 Validation** (Ground Truth Comparison):
```python
def test_vlm_detection_accuracy_nala_template():
    """
    Validate VLM detection against Nala card ground truth.

    SUCCESS CRITERIA: All regions within ±10px of manual measurements
    """
    detector = VLMTemplateDetector(instructor_client)
    detected = detector.detect_regions("templates/nala_example_creature.png")

    ground_truth = EXAMPLE_CARD_GROUND_TRUTH['regions']

    for region_name in ['name_box', 'mana_cost_box', 'type_line_box', 'text_box', 'pt_box']:
        detected_box = getattr(detected, region_name)
        gt_box = ground_truth[region_name]

        max_error = max(
            abs(detected_box.x - gt_box.x),
            abs(detected_box.y - gt_box.y),
            abs(detected_box.width - gt_box.width),
            abs(detected_box.height - gt_box.height)
        )

        assert max_error <= 10, f"{region_name}: max_error={max_error}px"
```

**VLM Scoring Consistency**:
```python
def test_vlm_scoring_consistency():
    """
    Verify VLM scores same layout consistently.

    SUCCESS CRITERIA: Std dev ≤ 0.05 across 5 evaluations
    """
    evaluator = VLMLayoutEvaluator(instructor_client)
    layout_state = create_test_layout()  # Fixed layout

    scores = [evaluator.score_layout(layout_state) for _ in range(5)]
    std_dev = np.std(scores)

    assert std_dev <= 0.05, f"VLM scoring inconsistent (std={std_dev:.3f})"
```
