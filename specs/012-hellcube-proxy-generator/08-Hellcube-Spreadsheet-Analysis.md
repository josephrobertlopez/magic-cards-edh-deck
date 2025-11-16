# Document 08: Hellcube Spreadsheet Analysis & Excel Parser Specification
## Real-World Data Structure Analysis

**Version**: 1.0.0
**Date**: 2025-11-16
**Status**: ✅ Based on Actual Hellcube Data
**Supersedes**: Generic Excel parsing in Doc 04-06

---

## Executive Summary

Analysis of the actual Hellcube spreadsheet reveals a **well-structured but unconventional** data format that requires semantic parsing. This document provides the definitive specification for Excel parsing based on real data.

### Key Findings

✅ **Good News**: Data is more structured than expected
✅ **Columns clearly labeled**: `name`, `pic`, `Types`, `text`, `flavor`, `Stats`
✅ **Multi-column layout**: Cards organized by color in columns C, D, E, etc.
⚠️ **Challenge**: Multiple text rows per card (abilities split across rows)
⚠️ **Challenge**: Images embedded in cells (not URLs)
✅ **Solution**: Row-based adjacency detection with field labels

---

## Actual Spreadsheet Structure

### Column Organization

```
Column A (Labels):     Column B (Unused)    Column C (Card Data)    Column D (Card Data)
─────────────────────────────────────────────────────────────────────────────────
[empty]                                     AJ                      AJ
name bULK                                   Juicero (1)             [Card 2 name]
                                            [embedded image]        [embedded image]
pic
Types                                       Artifact Creature- Juicer
text                                        (Tap)(4) Make a food token
text
text
flavor                                      Its actually very affordable if you think about it
Stats                                       2/2
```

### Card Structure Pattern

Each card follows this vertical structure in columns C, D, E...:

```
Row N:    AJ (header marker - indicates card start)
Row N+1:  Card name with mana cost in parentheses
Row N+2:  Embedded image (in same cell as name or separate)
Row N+3:  "Types" label in column A
Row N+3:  Card types (e.g., "Artifact Creature- Juicer")
Row N+4:  "text" label → Ability 1
Row N+5:  "text" label → Ability 2 (if exists)
Row N+6:  "text" label → Ability 3 (if exists)
Row N+7:  "flavor" label → Flavor text
Row N+8:  "Stats" label → P/T (e.g., "2/2")
```

### Example Card 1: Juicero

```
Column A      Column C
─────────────────────────────
              AJ
name bULK     Juicero (1)
              [juicer image]
pic
Types         Artifact Creature- Juicer
text          (Tap)(4) Make a food token
text          [empty]
text          [empty]
flavor        Its actually very affordable if you think about it
Stats         2/2
```

**Parsed Data**:
```json
{
  "name": "Juicero",
  "mana_cost": "(1)",
  "image_ref": "embedded_cell_C60",
  "types": "Artifact Creature- Juicer",
  "abilities": ["(Tap)(4) Make a food token"],
  "flavor_text": "Its actually very affordable if you think about it",
  "power_toughness": "2/2"
}
```

### Example Card 2: Bernie the Forgotten Guide

```
Column A         Column C
──────────────────────────────────────
                 AJ
name politics    Bernie the forgotten guide (Wt,Wt,Bu)
                 [Bernie on throne image]
pic
Types            Legendary Creature- Human Guide
text             When a Creature under your control kills an opponents
                 creature that creature is exiled and their controller
                 gains 1 life
text             [empty]
text             (Wt) Untill your next Upkeep Phase when any player
                 heals you gain 1 life
text             [empty]
flavor           All this time I was asking for your support, I was
                 trying to give you mine.
Stats            2/3
```

**Parsed Data**:
```json
{
  "name": "Bernie the forgotten guide",
  "mana_cost": "(Wt,Wt,Bu)",
  "image_ref": "embedded_cell_C70",
  "types": "Legendary Creature- Human Guide",
  "abilities": [
    "When a Creature under your control kills an opponents creature that creature is exiled and their controller gains 1 life",
    "(Wt) Untill your next Upkeep Phase when any player heals you gain 1 life"
  ],
  "flavor_text": "All this time I was asking for your support, I was trying to give you mine.",
  "power_toughness": "2/3"
}
```

### Example Card 3: Batman Blue / Batman? Black

**Multi-column layout** (columns C and D contain different cards):

```
Column A    Column C                              Column D
──────────────────────────────────────────────────────────────────
            AJ                                    AJ
name        Batman Blue (Bu,Bu)(1)                Batman? Black (Bk)(1)
            [cartoon Batman image]                [gun Batman image]
pic
Types       Creature- Human, Batman, Hero         Creature- Human, Batman
text        When a Clue token is sacrificed you   Menace
            may put a Finality Counter on a
            Villain
text        (Bu) When you take combat damage       Deathtouch
            Batman Blue investigates.
text        When a clue token is sacrificed        When Batman? Black Kills a Creature
            Batman Blue gets +1/+1 till the end    its Controller Discards 1 or Pays 2 life
            of the turn.
flavor      tHe WoRlDs GrEaTeSt DeCtIvE            Wait batman doesnt kill. Is that Ben Afflec?
Stats       2/4                                    4/1
```

---

## Excel Parser Specification

### Parser Architecture

```python
class HellcubeExcelParser:
    """Semantic parser for Hellcube spreadsheet structure

    Strategy:
    1. Detect column headers (row 2: "Blue (Bu) Black (Bk) Green (Gn)")
    2. For each data column (C, D, E...), parse cards vertically
    3. Use column A labels ("name", "pic", "Types", "text", "flavor", "Stats")
       to identify field boundaries
    4. Group adjacent rows into single card
    """

    def __init__(self, xlsx_path: str):
        self.df = pd.read_excel(xlsx_path, header=None)
        self.cards = []

    def parse(self) -> List[Dict]:
        """Parse all cards from spreadsheet"""
        # Detect data columns (C, D, E... where cards exist)
        data_columns = self._detect_data_columns()

        for col_idx in data_columns:
            cards_in_column = self._parse_column(col_idx)
            self.cards.extend(cards_in_column)

        return self.cards
```

### Step 1: Detect Data Columns

```python
def _detect_data_columns(self) -> List[int]:
    """Identify columns containing card data

    Heuristic: Columns with "AJ" markers (row 9, 68, etc.)
    indicating card start positions
    """
    data_columns = []

    # Scan row 2 for color headers (e.g., "Blue (Bu) Black (Bk)")
    header_row = 2
    for col_idx in range(2, self.df.shape[1]):  # Start from column C (index 2)
        cell_value = self.df.iloc[header_row, col_idx]

        if pd.notna(cell_value) and any(color in str(cell_value) for color in ['(Bu)', '(Bk)', '(Gn)', '(Rd)', '(Wt)']):
            data_columns.append(col_idx)

    return data_columns
```

### Step 2: Parse Column Vertically

```python
def _parse_column(self, col_idx: int) -> List[Dict]:
    """Parse all cards in a single column

    Algorithm:
    1. Scan column for "AJ" markers (card start)
    2. For each "AJ", extract card data until next "AJ" or empty section
    3. Use column A labels to identify fields
    """
    cards = []
    current_row = 0

    while current_row < self.df.shape[0]:
        # Look for "AJ" card marker
        cell_value = self.df.iloc[current_row, col_idx]

        if self._is_card_start(cell_value):
            # Extract card starting at this row
            card, next_row = self._extract_card(col_idx, current_row)
            cards.append(card)
            current_row = next_row
        else:
            current_row += 1

    return cards

def _is_card_start(self, cell_value) -> bool:
    """Check if cell indicates card start"""
    return pd.notna(cell_value) and str(cell_value).strip() == "AJ"
```

### Step 3: Extract Single Card

```python
def _extract_card(self, col_idx: int, start_row: int) -> Tuple[Dict, int]:
    """Extract single card data from column

    Returns: (card_dict, next_row_index)
    """
    card = {
        'name': None,
        'mana_cost': None,
        'image_ref': None,
        'types': None,
        'abilities': [],
        'flavor_text': None,
        'power_toughness': None
    }

    current_row = start_row + 1  # Skip "AJ" marker

    while current_row < self.df.shape[0]:
        label = self.df.iloc[current_row, 0]  # Column A label
        value = self.df.iloc[current_row, col_idx]  # Column C/D/E data

        # End of card (empty section or next "AJ")
        if self._is_card_end(label, value):
            break

        # Parse based on label
        if self._is_name_row(label):
            card['name'], card['mana_cost'] = self._parse_name_and_cost(value)
            card['image_ref'] = f"embedded_cell_{self._cell_ref(col_idx, current_row)}"

        elif str(label).strip() == "Types":
            card['types'] = str(value).strip() if pd.notna(value) else None

        elif str(label).strip() == "text":
            if pd.notna(value) and str(value).strip():
                card['abilities'].append(str(value).strip())

        elif str(label).strip() == "flavor":
            card['flavor_text'] = str(value).strip() if pd.notna(value) else None

        elif str(label).strip() == "Stats":
            card['power_toughness'] = str(value).strip() if pd.notna(value) else None
            current_row += 1  # Stats is last field
            break

        current_row += 1

    return card, current_row

def _parse_name_and_cost(self, cell_value: str) -> Tuple[str, str]:
    """Extract name and mana cost from cell

    Format: "Card Name (Cost)"
    Examples:
    - "Juicero (1)" → ("Juicero", "(1)")
    - "Bernie the forgotten guide (Wt,Wt,Bu)" → ("Bernie...", "(Wt,Wt,Bu)")
    - "Batman Blue (Bu,Bu)(1)" → ("Batman Blue", "(Bu,Bu)(1)")
    """
    import re

    text = str(cell_value).strip()

    # Find last occurrence of parentheses (mana cost)
    match = re.search(r'^(.+?)\s*(\(.+\))$', text)

    if match:
        name = match.group(1).strip()
        cost = match.group(2).strip()
        return name, cost
    else:
        # No mana cost found
        return text, ""

def _is_name_row(self, label) -> bool:
    """Check if row contains card name"""
    return pd.notna(label) and 'name' in str(label).lower()

def _is_card_end(self, label, value) -> bool:
    """Check if we've reached end of card section"""
    # Empty label AND empty value
    if pd.isna(label) and pd.isna(value):
        return True

    # Next "AJ" marker
    if pd.notna(value) and str(value).strip() == "AJ":
        return True

    return False

def _cell_ref(self, col_idx: int, row_idx: int) -> str:
    """Convert indices to Excel cell reference (e.g., C60)"""
    col_letter = chr(65 + col_idx)  # 2 → 'C', 3 → 'D', etc.
    row_number = row_idx + 1  # 0-indexed → 1-indexed
    return f"{col_letter}{row_number}"
```

### Step 4: Validate Parsed Card

```python
def _validate_card(self, card: Dict) -> bool:
    """Check if parsed card has minimum required fields"""
    required_fields = ['name', 'types']

    for field in required_fields:
        if not card.get(field):
            return False

    # At least one ability or flavor text
    if not card.get('abilities') and not card.get('flavor_text'):
        return False

    return True
```

---

## Mana Cost Parsing

### Format Analysis

From spreadsheet examples:
- `(1)` → Colorless mana: 1
- `(Wt,Wt,Bu)` → White White Blue
- `(Bu,Bu)(1)` → Blue Blue Colorless 1
- `(Tap)(4)` → Tap symbol + 4 colorless (in ability text)

### Mana Symbol Mapping

```python
MANA_SYMBOL_MAP = {
    'Wt': 'W',   # White
    'Bu': 'U',   # Blue
    'Bk': 'B',   # Black
    'Rd': 'R',   # Red
    'Gn': 'G',   # Green
    'Cl': 'C',   # Colorless
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
    '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    'Tap': 'T',  # Tap symbol
    'X': 'X',    # Variable cost
}

def parse_mana_cost(cost_string: str) -> List[str]:
    """Parse mana cost into list of symbols

    Examples:
    - "(1)" → ['1']
    - "(Wt,Wt,Bu)" → ['W', 'W', 'U']
    - "(Bu,Bu)(1)" → ['U', 'U', '1']
    - "(Tap)(4)" → ['T', '4']
    """
    import re

    # Remove outer parentheses and split by comma or )(
    cost_string = cost_string.strip('()')

    # Split on comma or )( pattern
    parts = re.split(r',|\)\(', cost_string)

    symbols = []
    for part in parts:
        part = part.strip('() ')
        if part in MANA_SYMBOL_MAP:
            symbols.append(MANA_SYMBOL_MAP[part])
        elif part.isdigit():
            symbols.append(part)
        elif part:
            # Unknown symbol - pass through
            symbols.append(part)

    return symbols
```

---

## Image Handling

### Challenge: Embedded Images

Spreadsheet contains **embedded images in cells**, not URLs or file paths.

### Solution: Image Extraction

```python
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
import io
from PIL import Image

def extract_embedded_images(xlsx_path: str, output_dir: str) -> Dict[str, str]:
    """Extract all embedded images from Excel

    Returns: Dict mapping cell_ref → image_path
    """
    wb = load_workbook(xlsx_path)
    ws = wb.active

    image_map = {}

    # Extract all images from worksheet
    for image in ws._images:
        # Get anchor (cell position)
        cell_ref = image.anchor._from.col, image.anchor._from.row
        cell_str = f"{chr(65 + cell_ref[0])}{cell_ref[1] + 1}"

        # Save image
        image_data = image._data()
        img = Image.open(io.BytesIO(image_data))

        image_filename = f"card_image_{cell_str}.png"
        image_path = os.path.join(output_dir, image_filename)
        img.save(image_path)

        image_map[cell_str] = image_path

    return image_map
```

### Integration with Parser

```python
class HellcubeExcelParser:
    def __init__(self, xlsx_path: str):
        self.xlsx_path = xlsx_path
        self.df = pd.read_excel(xlsx_path, header=None)

        # Extract images on initialization
        self.image_dir = '.cache/extracted_images'
        os.makedirs(self.image_dir, exist_ok=True)
        self.image_map = extract_embedded_images(xlsx_path, self.image_dir)

    def _extract_card(self, col_idx, start_row):
        # ... (previous code)

        if self._is_name_row(label):
            card['name'], card['mana_cost'] = self._parse_name_and_cost(value)

            # Look up image for this cell
            cell_ref = self._cell_ref(col_idx, current_row)
            card['image_path'] = self.image_map.get(cell_ref, None)
```

---

## Template Matching Specification

### Card Type Detection

```python
def determine_card_template(card: Dict) -> str:
    """Select appropriate template based on card types

    Template selection hierarchy:
    1. Special types (planeswalker, saga, etc.)
    2. Creature vs non-creature
    3. Color identity
    4. Legendary status
    """
    types = card.get('types', '').lower()
    mana_cost = card.get('mana_cost', '')

    # Extract color identity from mana cost
    colors = extract_colors(mana_cost)

    # Special types
    if 'planeswalker' in types:
        return f"planeswalker_{color_code(colors)}.png"

    if 'saga' in types:
        return f"saga_{color_code(colors)}.png"

    # Creature vs non-creature
    if 'creature' in types:
        is_legendary = 'legendary' in types
        template_prefix = "legendary_creature" if is_legendary else "creature"
        return f"{template_prefix}_{color_code(colors)}.png"

    # Non-creature spells
    if 'instant' in types:
        return f"instant_{color_code(colors)}.png"

    if 'sorcery' in types:
        return f"sorcery_{color_code(colors)}.png"

    if 'artifact' in types:
        return f"artifact_{color_code(colors)}.png"

    if 'enchantment' in types:
        return f"enchantment_{color_code(colors)}.png"

    # Default
    return f"generic_{color_code(colors)}.png"

def extract_colors(mana_cost: str) -> Set[str]:
    """Extract color identity from mana cost"""
    colors = set()

    if 'Wt' in mana_cost or 'W' in mana_cost:
        colors.add('W')
    if 'Bu' in mana_cost or 'U' in mana_cost:
        colors.add('U')
    if 'Bk' in mana_cost or 'B' in mana_cost:
        colors.add('B')
    if 'Rd' in mana_cost or 'R' in mana_cost:
        colors.add('R')
    if 'Gn' in mana_cost or 'G' in mana_cost:
        colors.add('G')

    return colors

def color_code(colors: Set[str]) -> str:
    """Convert color set to template code

    Examples:
    - {'W'} → 'white'
    - {'U', 'B'} → 'dimir' (blue-black guild)
    - {'W', 'U', 'B'} → 'esper' (3-color)
    - {} → 'colorless'
    """
    color_tuple = tuple(sorted(colors))

    # Monocolor
    if len(colors) == 1:
        return {
            'W': 'white',
            'U': 'blue',
            'B': 'black',
            'R': 'red',
            'G': 'green'
        }[list(colors)[0]]

    # Colorless
    if len(colors) == 0:
        return 'colorless'

    # Multicolor (use generic multicolor template)
    return f"multicolor_{len(colors)}"
```

---

## Complete Workflow

### End-to-End Pipeline

```python
def generate_proxies_from_hellcube(xlsx_path: str, output_dir: str):
    """Complete proxy generation pipeline

    Steps:
    1. Parse Hellcube spreadsheet
    2. Extract embedded images
    3. For each card:
       a. Select appropriate template
       b. Detect template regions (VLM)
       c. Optimize layout (MCTS)
       d. Render final proxy
    4. Save to output directory
    """

    # Step 1: Parse spreadsheet
    parser = HellcubeExcelParser(xlsx_path)
    cards = parser.parse()

    print(f"Parsed {len(cards)} cards from spreadsheet")

    # Step 2: Template region detection (with caching)
    template_analyzer = VLMTemplateAnalyzer(
        instructor=get_instructor('ollama')
    )

    # Step 3: Process each card
    for i, card in enumerate(cards):
        print(f"\nProcessing card {i+1}/{len(cards)}: {card['name']}")

        # 3a. Select template
        template_path = determine_card_template(card)

        # 3b. Detect regions (cached)
        template_regions = template_analyzer.analyze_template(template_path)

        # 3c. Optimize layout with MCTS
        mcts = MCTSLayoutAlgorithm(max_steps=2, instructor=get_instructor('ollama'))

        result = mcts.execute(
            problem=json.dumps({'card_data': card}),
            card_data=card,
            template_regions=template_regions,
            template_path=template_path
        )

        optimal_layout = result['result'].data['layout']
        quality_score = result['result'].data['quality_score']

        print(f"  Layout quality: {quality_score:.3f}")

        # 3d. Render final proxy
        proxy_image = render_proxy(
            template_path=template_path,
            layout=optimal_layout,
            card_data=card
        )

        # 3e. Save
        output_path = os.path.join(output_dir, f"{card['name']}.png")
        proxy_image.save(output_path)

        print(f"  Saved: {output_path}")
```

---

## Validation Checklist

### Parser Validation

- [ ] All data columns detected (C, D, E, ...)
- [ ] "AJ" markers correctly identify card starts
- [ ] Name and mana cost parsed correctly
- [ ] Multiple `text` rows consolidated into abilities list
- [ ] Flavor text captured
- [ ] P/T parsed (e.g., "2/2", "4/1")
- [ ] Empty `text` rows ignored
- [ ] Images extracted and mapped correctly

### Data Quality Checks

- [ ] All cards have `name`
- [ ] All cards have `types`
- [ ] Creature cards have `power_toughness`
- [ ] At least one ability or flavor text
- [ ] Mana cost symbols recognized
- [ ] Color identity correct

### Integration Tests

```python
def test_parse_hellcube_spreadsheet():
    """Integration test on actual Hellcube data"""
    parser = HellcubeExcelParser('Hellcube AJ.xlsx')
    cards = parser.parse()

    # Validate expected cards
    assert len(cards) > 0, "No cards parsed"

    # Find test cards
    juicero = next((c for c in cards if 'Juicero' in c['name']), None)
    assert juicero is not None, "Juicero not found"
    assert juicero['mana_cost'] == '(1)'
    assert juicero['types'] == 'Artifact Creature- Juicer'
    assert len(juicero['abilities']) >= 1
    assert juicero['power_toughness'] == '2/2'

    bernie = next((c for c in cards if 'Bernie' in c['name']), None)
    assert bernie is not None, "Bernie not found"
    assert bernie['mana_cost'] == '(Wt,Wt,Bu)'
    assert 'Legendary' in bernie['types']
    assert len(bernie['abilities']) == 2
    assert bernie['power_toughness'] == '2/3'

    print("✅ All validation checks passed")
```

---

## Document Status

**Status**: ✅ Complete
**Based On**: Actual Hellcube spreadsheet images
**Supersedes**: Generic Excel parsing in Documents 04-06
**Ready For**: Phase 5 implementation

**Next Step**: Implement `HellcubeExcelParser` class in Phase 5 (Days 15-16)
