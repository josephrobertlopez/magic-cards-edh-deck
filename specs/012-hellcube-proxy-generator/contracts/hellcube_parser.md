# HellcubeExcelParser Contract

**Module**: `src/hellcube_parser.py`
**Purpose**: Parse unstructured Hellcube Excel spreadsheet into structured Card objects

---

## Class: HellcubeExcelParser

### parse_excel()

**Signature**:
```python
def parse_excel(self, file_path: str) -> List[Card]:
    """
    Parse Hellcube Excel spreadsheet into structured card data.

    Args:
        file_path: Absolute path to Hellcube AJ.xlsx file

    Returns:
        List[Card]: Parsed cards with all attributes

    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If spreadsheet structure is invalid
        ParsingError: If card data is malformed
    """
```

**Input Example**:
```python
parser = HellcubeExcelParser()
cards = parser.parse_excel("/path/to/Hellcube AJ.xlsx")
```

**Output Example**:
```python
[
    Card(
        name="Batman Blue",
        mana_cost=ManaCost(symbols=[('U', 2), ('Generic', 1)], cmc=3),
        color="U",
        type="Creature",
        legendary=False,
        subtypes=["Human", "Batman"],
        abilities=["Vigilance", "When Batman Blue enters, draw a card"],
        flavor_text="I'm Batman.",
        power_toughness="2/2",
        author="AJ",
        artwork_url=None
    ),
    # ... more cards
]
```

**Error Handling**:
- **FileNotFoundError**: File path invalid or doesn't exist
- **ValueError**: Missing required columns (A, C, D, E, F) or "AJ" markers not found
- **ParsingError**: Field value format invalid (e.g., malformed mana cost, invalid P/T)

---

### _extract_card() (private)

**Signature**:
```python
def _extract_card(self, worksheet, col_idx: int, start_row: int) -> Card:
    """
    Extract single card from column starting at row.

    Args:
        worksheet: openpyxl worksheet object
        col_idx: Column index (C=3, D=4, E=5, F=6)
        start_row: Row index of "AJ" marker

    Returns:
        Card: Parsed card object

    Raises:
        ParsingError: If required fields missing or malformed
    """
```

**Logic**:
```python
# Use Column A labels to identify fields
for row_idx in range(start_row, next_aj_marker):
    label = str(worksheet.cell(row_idx, 1).value).strip()
    value = worksheet.cell(row_idx, col_idx).value

    if label.startswith("name"):
        # Extract name and mana cost
        card['name'], card['mana_cost'] = self._parse_name_and_cost(value)

    elif label == "Types":
        # Extract type, legendary status, subtypes
        card['type'], card['legendary'], card['subtypes'] = self._parse_types(value)

    elif label == "text":
        if pd.notna(value) and str(value).strip():
            card['abilities'].append(str(value).strip())

    elif label == "flavor":
        card['flavor_text'] = str(value).strip() if pd.notna(value) else None

    elif label == "Stats":
        card['power_toughness'] = self._parse_stats(value)

    elif label == "Author":
        card['author'] = str(value).strip() if pd.notna(value) else None
```

---

###_parse_name_and_cost() (private)

**Signature**:
```python
def _parse_name_and_cost(self, raw_value: str) -> Tuple[str, ManaCost]:
    """
    Extract card name and mana cost from combined string.

    Args:
        raw_value: e.g., "Batman Blue (Bu,Bu)(1)"

    Returns:
        Tuple[str, ManaCost]: (name="Batman Blue", mana_cost=...)

    Examples:
        "Grizzly Bears (Gn)(Gn)" → ("Grizzly Bears", ManaCost([('G', 2)]))
        "Sol Ring (1)" → ("Sol Ring", ManaCost([('Generic', 1)]))
    """
```

**Implementation**:
```python
# Find last opening parenthesis (start of mana cost)
last_paren = raw_value.rfind('(')
if last_paren == -1:
    # No mana cost
    return raw_value.strip(), ManaCost(symbols=[], cmc=0)

name = raw_value[:last_paren].strip()
cost_string = raw_value[last_paren:]
mana_cost = parse_mana_cost(cost_string)  # Calls ManaCost parser

return name, mana_cost
```

---

### _parse_types() (private)

**Signature**:
```python
def _parse_types(self, types_value: str) -> Tuple[str, bool, List[str]]:
    """
    Extract primary type, legendary status, and subtypes.

    Args:
        types_value: e.g., "Legendary Creature- Human, Batman"

    Returns:
        Tuple[str, bool, List[str]]:
            - type: "Creature"
            - legendary: True
            - subtypes: ["Human", "Batman"]

    Examples:
        "Creature- Bear" → ("Creature", False, ["Bear"])
        "Legendary Planeswalker- Jace" → ("Planeswalker", True, ["Jace"])
        "Artifact" → ("Artifact", False, [])
    """
```

**Implementation**:
```python
legendary = "Legendary" in types_value
cleaned = types_value.replace("Legendary", "").strip()

if "-" in cleaned:
    type_part, subtype_part = cleaned.split("-", 1)
    primary_type = type_part.strip()
    subtypes = [s.strip() for s in subtype_part.split(",")]
else:
    primary_type = cleaned
    subtypes = []

return primary_type, legendary, subtypes
```

---

### _parse_stats() (private)

**Signature**:
```python
def _parse_stats(self, stats_value: Any) -> Optional[str]:
    """
    Extract power/toughness from Stats field.

    Args:
        stats_value: Can be str "2/4" or datetime 2025-02-04 (Excel quirk)

    Returns:
        Optional[str]: "2/4" or None if not creature

    Examples:
        "2/4" → "2/4"
        datetime(2025, 2, 4) → "2/4"
        None → None
    """
```

**Implementation**:
```python
if pd.isna(stats_value):
    return None

if isinstance(stats_value, datetime):
    # Excel date quirk: 2025-02-04 means P/T 2/4
    return f"{stats_value.month}/{stats_value.day}"

if isinstance(stats_value, str) and "/" in stats_value:
    return stats_value.strip()

return None
```

---

## Error Classes

```python
class ParsingError(Exception):
    """Raised when card data is malformed during parsing"""
    def __init__(self, card_name: str, field: str, reason: str):
        self.card_name = card_name
        self.field = field
        self.reason = reason
        super().__init__(f"Error parsing {field} for card '{card_name}': {reason}")
```

**Example Usage**:
```python
raise ParsingError(
    card_name="Batman Blue",
    field="mana_cost",
    reason="Invalid notation: (BU,BU)(1) - should use 'Bu' not 'BU'"
)
```

---

## Validation Contract

**Post-Conditions** (after `parse_excel()` returns):
- All returned cards have `name` (non-empty)
- All returned cards have `type` (one of: Creature, Planeswalker, Artifact, Enchantment, Instant, Sorcery, Land)
- `power_toughness` matches pattern `\d+/\d+` if present
- `color` inferred correctly from `mana_cost.symbols`
- No duplicate card names within same author

**Warnings** (logged, not raised):
- Card missing optional fields (flavor_text, author, artwork_url)
- Unusual mana cost notation (e.g., hybrid mana - log for review)
