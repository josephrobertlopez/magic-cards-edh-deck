# Data Model Specification

**Feature**: 012 Hellcube Proxy Generator
**Phase**: 1 (Design Artifacts)
**Date**: 2025-11-16

---

## Overview

This document defines all data entities, their attributes, relationships, validation rules, and state transitions for the Hellcube Proxy Generator feature.

---

## Entity Catalog

1. **Card** - MTG custom card with parsed attributes
2. **LayoutState** - MCTS search state (partial card layout)
3. **MCTSNode** - MCTS tree node with visit statistics
4. **LayoutAction** - Element placement decision
5. **PlacedElement** - Positioned card element with rendering info
6. **CardElement** - Unpositional element waiting to be placed
7. **BoundingBox** - Rectangle region in pixels
8. **TemplateRegions** - VLM-detected template regions (Pydantic)
9. **LayoutQuality** - VLM layout evaluation (Pydantic)
10. **ManaCost** - Parsed mana casting cost

---

## Entity Definitions

### 1. Card

**Description**: Represents a single MTG custom card with all attributes needed for proxy generation.

**Attributes**:

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `name` | `str` | ✅ | - | len > 0 | Card name (without mana cost) |
| `mana_cost` | `ManaCost` | ✅ | - | - | Parsed casting cost |
| `color` | `str` | ✅ | inferred | in [W, U, B, R, G, C, Multicolor] | Inferred from mana symbols |
| `type` | `str` | ✅ | - | len > 0 | Primary card type (Creature, Planeswalker, etc.) |
| `legendary` | `bool` | ✅ | False | - | True if "Legendary" keyword in Types field |
| `subtypes` | `List[str]` | ✅ | [] | - | Extracted from Types field after dash |
| `abilities` | `List[str]` | ✅ | [] | - | Ordered list of ability texts |
| `flavor_text` | `str` | ❌ | None | - | Optional flavor text |
| `power_toughness` | `str` | ❌ | None | pattern: `\d+/\d+` | For creatures (e.g., "2/4") |
| `author` | `str` | ❌ | None | - | Card designer name |
| `artwork_url` | `str` | ❌ | None | URL format | Custom artwork download URL |

**Validation Rules**:
```python
from pydantic import BaseModel, Field, validator

class Card(BaseModel):
    name: str = Field(..., min_length=1, description="Card name without mana cost")
    mana_cost: 'ManaCost'
    color: str = Field(..., pattern="^(W|U|B|R|G|C|Multicolor)$")
    type: str = Field(..., min_length=1)
    legendary: bool = False
    subtypes: List[str] = Field(default_factory=list)
    abilities: List[str] = Field(default_factory=list)
    flavor_text: Optional[str] = None
    power_toughness: Optional[str] = Field(None, pattern=r"^\d+/\d+$")
    author: Optional[str] = None
    artwork_url: Optional[HttpUrl] = None

    @validator('type')
    def validate_type(cls, v):
        valid_types = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment',
                       'Instant', 'Sorcery', 'Land']
        base_type = v.split('-')[0].strip()
        if base_type not in valid_types:
            raise ValueError(f"Invalid card type: {base_type}")
        return v
```

**Relationships**:
- Has one `ManaCost` (composition)
- Belongs to zero or one template (via `infer_template_file()`)

**State Transitions**: Immutable (no state changes after parsing)

---

### 2. LayoutState

**Description**: Represents a partial card layout during MCTS search.

**Attributes**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `placed_elements` | `List[PlacedElement]` | ✅ | [] | Elements already positioned |
| `remaining_elements` | `List[CardElement]` | ✅ | [] | Elements still to be placed |
| `template_regions` | `Dict[str, BoundingBox]` | ✅ | {} | VLM-detected template regions |
| `quality_score` | `float` | ❌ | None | VLM evaluation score (0.0-1.0) |

**Methods**:
```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class LayoutState:
    placed_elements: List['PlacedElement'] = field(default_factory=list)
    remaining_elements: List['CardElement'] = field(default_factory=list)
    template_regions: Dict[str, 'BoundingBox'] = field(default_factory=dict)
    quality_score: Optional[float] = None

    def is_terminal(self) -> bool:
        """Check if all elements have been placed"""
        return len(self.remaining_elements) == 0

    def has_overlap(self) -> bool:
        """Check if any placed elements overlap"""
        for i, elem1 in enumerate(self.placed_elements):
            box1 = elem1.get_bounding_box()
            for elem2 in self.placed_elements[i+1:]:
                box2 = elem2.get_bounding_box()
                if box1.overlaps(box2):
                    return True
        return False

    def copy(self) -> 'LayoutState':
        """Create deep copy for simulation"""
        return LayoutState(
            placed_elements=list(self.placed_elements),
            remaining_elements=list(self.remaining_elements),
            template_regions=dict(self.template_regions),
            quality_score=self.quality_score
        )
```

**Validation Rules**:
- `quality_score` must be in [0.0, 1.0] if not None
- `placed_elements` + `remaining_elements` must equal total card elements (5-8)
- `template_regions` must contain at minimum: `name_box`, `mana_cost_box`, `type_line_box`, `text_box_1`

**State Transitions**:
```
Initial State (empty layout):
  placed_elements = []
  remaining_elements = [name, mana_cost, type_line, ability_1, ...]
  quality_score = None
  ↓
Intermediate State (partial layout):
  placed_elements = [name, mana_cost]
  remaining_elements = [type_line, ability_1, ...]
  quality_score = None
  ↓
Terminal State (complete layout):
  placed_elements = [name, mana_cost, type_line, ability_1, ...]
  remaining_elements = []
  quality_score = 0.85 (VLM evaluated)
```

---

### 3. MCTSNode

**Description**: MCTS tree node storing partial layout state and UCB1 visit statistics.

**Attributes**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `state` | `LayoutState` | ✅ | - | Partial layout at this node |
| `parent` | `MCTSNode` | ❌ | None | Parent node (None for root) |
| `children` | `List[MCTSNode]` | ✅ | [] | Child nodes (expanded actions) |
| `visits` | `int` | ✅ | 0 | Number of rollouts through this node |
| `total_reward` | `float` | ✅ | 0.0 | Sum of all VLM scores from rollouts |
| `untried_actions` | `List[LayoutAction]` | ✅ | [] | Actions not yet expanded |

**Methods**:
```python
@dataclass
class MCTSNode:
    state: 'LayoutState'
    parent: Optional['MCTSNode'] = None
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_actions: List['LayoutAction'] = field(default_factory=list)

    def is_fully_expanded(self) -> bool:
        """Check if all actions have been tried"""
        return len(self.untried_actions) == 0

    def is_terminal(self) -> bool:
        """Check if this is a terminal state"""
        return self.state.is_terminal()

    def get_average_reward(self) -> float:
        """Get average reward (Q-value)"""
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def get_ucb1_score(self, exploration_constant: float = 1.414) -> float:
        """Calculate UCB1 score for selection

        UCB1 = Q(node) + C × sqrt(ln(N_parent) / N_node)
        """
        if self.visits == 0:
            return float('inf')  # Unvisited nodes have infinite priority

        exploitation = self.get_average_reward()
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration
```

**Invariants**:
- `visits` == sum of all children's visits (for non-leaf nodes)
- `total_reward` <= `visits` (since VLM scores are in [0.0, 1.0])
- Root node has `parent == None`
- Leaf nodes have `children == []`

---

### 4. LayoutAction

**Description**: Represents a positioning decision for one card element.

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `element` | `CardElement` | ✅ | Element to place |
| `region` | `str` | ✅ | Template region name (e.g., "text_box_1") |
| `position` | `Tuple[int, int]` | ✅ | (x, y) top-left corner within region |
| `font_size` | `int` | ✅ | Font size in points [8-20] |
| `alignment` | `str` | ✅ | Text alignment: "left", "center", "right" |

**Methods**:
```python
@dataclass
class LayoutAction:
    element: 'CardElement'
    region: str
    position: Tuple[int, int]  # (x, y)
    font_size: int  # 8-20pt
    alignment: str  # 'left', 'center', 'right'

    def apply_to_state(self, state: 'LayoutState') -> 'LayoutState':
        """Apply this action to a state, returning new state"""
        new_state = state.copy()

        # Remove element from remaining
        new_state.remaining_elements = [
            e for e in state.remaining_elements
            if e.element_type != self.element.element_type
        ]

        # Calculate text size
        text_width = estimate_text_width(self.element.text_content, self.font_size)
        text_height = estimate_text_height(self.element.text_content, self.font_size)

        # Create placed element
        placed = PlacedElement(
            element_type=self.element.element_type,
            text_content=self.element.text_content,
            position=self.position,
            size=(text_width, text_height),
            font_size=self.font_size,
            alignment=self.alignment
        )

        new_state.placed_elements.append(placed)
        return new_state
```

**Validation Rules**:
- `font_size` in range [8, 20]
- `alignment` in ["left", "center", "right"]
- `region` must exist in `state.template_regions`
- `position` must be within region bounds

---

### 5. PlacedElement

**Description**: Card element that has been positioned with rendering information.

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `element_type` | `str` | ✅ | Element type ID (e.g., "name", "ability_1") |
| `text_content` | `str` | ✅ | Actual text to render |
| `position` | `Tuple[int, int]` | ✅ | (x, y) top-left corner |
| `size` | `Tuple[int, int]` | ✅ | (width, height) in pixels |
| `font_size` | `int` | ✅ | Font size in points |
| `alignment` | `str` | ✅ | Text alignment |

**Methods**:
```python
@dataclass
class PlacedElement:
    element_type: str
    text_content: str
    position: Tuple[int, int]  # (x, y)
    size: Tuple[int, int]  # (width, height)
    font_size: int
    alignment: str

    def get_bounding_box(self) -> 'BoundingBox':
        """Get bounding box for overlap checking"""
        x, y = self.position
        width, height = self.size
        return BoundingBox(x, y, width, height)
```

---

### 6. CardElement

**Description**: Card element waiting to be placed (no position information yet).

**Attributes**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `element_type` | `str` | ✅ | - | Type ID (name, mana_cost, type_line, ability_N, p_t, flavor) |
| `text_content` | `str` | ✅ | - | Text to render |
| `required` | `bool` | ✅ | True | Must be placed (False for optional flavor text) |

**Element Types**:
- `name` - Card name
- `mana_cost` - Mana symbols (rendered as images)
- `type_line` - Card types and subtypes
- `ability_1`, `ability_2`, `ability_3` - Ability texts
- `p_t` - Power/toughness (creatures only)
- `flavor` - Flavor text (optional)

---

### 7. BoundingBox

**Description**: Rectangle region in pixels (used for template regions and overlap detection).

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | `int` | ✅ | Top-left x coordinate |
| `y` | `int` | ✅ | Top-left y coordinate |
| `width` | `int` | ✅ | Box width in pixels |
| `height` | `int` | ✅ | Box height in pixels |

**Methods**:
```python
@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    def contains_point(self, px: int, py: int) -> bool:
        """Check if point (px, py) is inside box"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this box overlaps with another"""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)
```

---

### 8. TemplateRegions (Pydantic)

**Description**: VLM-detected template regions for a card template.

**Pydantic Schema**:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class TemplateRegions(BaseModel):
    """VLM-detected template regions"""
    template_hash: str = Field(..., description="SHA-256 hash of template image")
    name_box: BoundingBox = Field(..., description="Card name region")
    mana_cost_box: BoundingBox = Field(..., description="Mana cost region (top-right)")
    type_line_box: BoundingBox = Field(..., description="Type line region")
    text_boxes: List[BoundingBox] = Field(..., description="1-3 ability text regions")
    pt_box: Optional[BoundingBox] = Field(None, description="Power/toughness (creatures only)")
    flavor_box: Optional[BoundingBox] = Field(None, description="Flavor text region")
    artwork_detected: bool = Field(
        default=False,
        description="FAIL if True (artwork should not be detected as text region)"
    )

    class Config:
        schema_extra = {
            "example": {
                "template_hash": "a3f5e8c9d2b1...",
                "name_box": {"x": 50, "y": 30, "width": 530, "height": 35},
                "mana_cost_box": {"x": 650, "y": 25, "width": 80, "height": 40},
                "type_line_box": {"x": 50, "y": 500, "width": 650, "height": 30},
                "text_boxes": [{"x": 50, "y": 540, "width": 650, "height": 360}],
                "pt_box": {"x": 650, "y": 950, "width": 70, "height": 50},
                "flavor_box": None,
                "artwork_detected": False
            }
        }
```

---

### 9. LayoutQuality (Pydantic)

**Description**: VLM evaluation of a completed card layout.

**Pydantic Schema**:
```python
class LayoutQuality(BaseModel):
    """VLM layout quality evaluation"""
    readability_score: float = Field(..., ge=0.0, le=1.0, description="Text legibility")
    convention_compliance: float = Field(..., ge=0.0, le=1.0, description="MTG layout standards")
    aesthetic_balance: float = Field(..., ge=0.0, le=1.0, description="Visual harmony")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Weighted average")
    no_overflow: bool = Field(..., description="True if no text exceeds region boundaries")
    issues: List[str] = Field(default_factory=list, description="Specific problems found")
    reasoning: str = Field(..., max_length=200, description="Brief explanation of score")

    class Config:
        schema_extra = {
            "example": {
                "readability_score": 0.92,
                "convention_compliance": 0.88,
                "aesthetic_balance": 0.85,
                "overall_score": 0.88,
                "no_overflow": True,
                "issues": [],
                "reasoning": "Well-balanced layout with good spacing and readability"
            }
        }
```

---

### 10. ManaCost

**Description**: Parsed representation of a card's mana casting cost.

**Attributes**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `symbols` | `List[Tuple[str, int]]` | ✅ | [] | List of (symbol, count) pairs |
| `cmc` | `int` | ✅ | 0 | Converted mana cost (total) |

**Symbol Types**: W (white), U (blue), B (black), R (red), G (green), C (colorless), Generic (numbered)

**Example**:
```python
# Input: "(Bu,Bu)(1)" → 2 blue mana + 1 generic
mana_cost = ManaCost(
    symbols=[('U', 2), ('Generic', 1)],
    cmc=3
)
```

**Parsing Function**:
```python
def parse_mana_cost(cost_string: str) -> ManaCost:
    """Parse mana cost from parenthetical notation

    Examples:
        "(Bu,Bu)(1)" → ManaCost(symbols=[('U', 2), ('Generic', 1)], cmc=3)
        "(Wt,Wt,Bu)" → ManaCost(symbols=[('W', 2), ('U', 1)], cmc=3)
    """
    MANA_SYMBOL_MAP = {
        'Wt': 'W',  # White
        'Bu': 'U',  # Blue
        'Bk': 'B',  # Black
        'Rd': 'R',  # Red
        'Gn': 'G',  # Green
        'Cl': 'C',  # Colorless
    }

    symbols = []
    cmc = 0

    # Extract all groups in parentheses
    groups = re.findall(r'\(([^)]+)\)', cost_string)

    for group in groups:
        parts = [p.strip() for p in group.split(',')]
        for part in parts:
            if part.isdigit():
                # Generic mana
                count = int(part)
                symbols.append(('Generic', count))
                cmc += count
            elif part in MANA_SYMBOL_MAP:
                # Colored mana
                color = MANA_SYMBOL_MAP[part]
                symbols.append((color, 1))
                cmc += 1

    return ManaCost(symbols=symbols, cmc=cmc)
```

---

## Entity Relationships Diagram

```
Card (1) ──has──> (1) ManaCost
  │
  └──references──> Template (inferred by type/color)

LayoutState (1) ──contains──> (0-8) PlacedElement
            │
            └──contains──> (0-8) CardElement
            │
            └──references──> (1) TemplateRegions

MCTSNode (1) ──has──> (1) LayoutState
         │
         ├──has──> (0-1) MCTSNode (parent)
         │
         ├──has──> (0-N) MCTSNode (children)
         │
         └──has──> (0-N) LayoutAction (untried)

LayoutAction (1) ──operates on──> (1) CardElement
```

---

## Validation Summary

| Entity | Key Validation Rules |
|--------|---------------------|
| Card | Required: name, type; Pattern: power_toughness "\\d+/\\d+"; URL format: artwork_url |
| LayoutState | Range: quality_score [0.0, 1.0]; Consistency: placed + remaining = total elements |
| MCTSNode | Invariant: visits == sum(children.visits); Range: total_reward <= visits |
| LayoutAction | Range: font_size [8, 20]; Enum: alignment in ["left", "center", "right"] |
| TemplateRegions | Required: name_box, mana_cost_box, type_line_box, text_boxes; FAIL if artwork_detected |
| LayoutQuality | Range: all scores [0.0, 1.0]; Max length: reasoning 200 chars |
| ManaCost | Consistency: cmc == sum(symbol counts) |
