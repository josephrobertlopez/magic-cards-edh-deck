"""
Unit tests for JSONPath extraction utilities.

Feature 009: Domain-Agnostic Skills
User Story 3: JSONPath Field Extraction

Tests cover:
- Nested field extraction ($.field.subfield.value)
- Array element extraction ($.items[*].name)
- Single value extraction
- Multiple value extraction
- Missing field handling with defaults
- Invalid JSON handling
- Invalid JSONPath expression handling
- Edge cases (empty arrays, null values, etc.)
"""

import pytest
from a2a_orchestrator.json_utils import (
    extract_jsonpath,
    extract_nested_field,
    safe_json_loads
)


# ============================================================================
# extract_jsonpath Tests
# ============================================================================

def test_extract_single_nested_field():
    """Test extracting a single nested field."""
    json_data = {
        "name": "Lightning Bolt",
        "image_uris": {
            "small": "https://example.com/small.jpg",
            "normal": "https://example.com/normal.jpg",
            "large": "https://example.com/large.jpg"
        }
    }

    result = extract_jsonpath(json_data, "$.image_uris.large")

    assert result["value"] == "https://example.com/large.jpg"
    assert result["items"] == ["https://example.com/large.jpg"]
    assert result["count"] == 1
    assert "error" not in result


def test_extract_array_of_values():
    """Test extracting multiple values from an array."""
    json_data = {
        "products": [
            {"id": 1, "name": "Widget Pro"},
            {"id": 2, "name": "Super Tool"},
            {"id": 3, "name": "Mega Device"}
        ]
    }

    result = extract_jsonpath(json_data, "$.products[*].name")

    assert result["value"] is None  # Multiple values - use items instead
    assert result["items"] == ["Widget Pro", "Super Tool", "Mega Device"]
    assert result["count"] == 3
    assert "error" not in result


def test_extract_array_index():
    """Test extracting specific array index."""
    json_data = {
        "items": ["first", "second", "third"]
    }

    result = extract_jsonpath(json_data, "$.items[1]")

    assert result["value"] == "second"
    assert result["items"] == ["second"]
    assert result["count"] == 1


def test_extract_missing_field_with_default():
    """Test that missing fields return default value."""
    json_data = {
        "name": "Product X",
        "price": 19.99
    }

    result = extract_jsonpath(json_data, "$.description", default_value="N/A")

    assert result["value"] == "N/A"
    assert result["items"] == []
    assert result["count"] == 0
    assert "error" not in result


def test_extract_missing_field_without_default():
    """Test that missing fields return None if no default specified."""
    json_data = {"name": "Test"}

    result = extract_jsonpath(json_data, "$.nonexistent")

    assert result["value"] is None
    assert result["items"] == []
    assert result["count"] == 0


def test_extract_from_json_string():
    """Test parsing JSON string before extraction."""
    json_str = '{"user": {"name": "Alice", "age": 30}}'

    result = extract_jsonpath(json_str, "$.user.name")

    assert result["value"] == "Alice"
    assert result["count"] == 1


def test_extract_deeply_nested_field():
    """Test extracting deeply nested fields."""
    json_data = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "value": "deep"
                    }
                }
            }
        }
    }

    result = extract_jsonpath(json_data, "$.level1.level2.level3.level4.value")

    assert result["value"] == "deep"
    assert result["count"] == 1


def test_extract_all_values_from_nested_arrays():
    """Test extracting values from nested arrays."""
    json_data = {
        "categories": [
            {"items": [{"name": "A"}, {"name": "B"}]},
            {"items": [{"name": "C"}, {"name": "D"}]}
        ]
    }

    result = extract_jsonpath(json_data, "$.categories[*].items[*].name")

    assert result["items"] == ["A", "B", "C", "D"]
    assert result["count"] == 4


def test_extract_filtered_array():
    """Test extracting with array filter."""
    json_data = {
        "products": [
            {"name": "Product A", "price": 10},
            {"name": "Product B", "price": 20},
            {"name": "Product C", "price": 15}
        ]
    }

    # Note: jsonpath-ng supports filters like [?price > 10]
    # but for simplicity, we'll test basic extraction
    result = extract_jsonpath(json_data, "$.products[*].price")

    assert result["items"] == [10, 20, 15]
    assert result["count"] == 3


def test_invalid_json_string():
    """Test handling of invalid JSON string."""
    result = extract_jsonpath("invalid json", "$.field")

    assert "error" in result
    assert result["error"] == "INVALID_JSON"
    assert result["value"] is None
    assert result["items"] == []
    assert result["count"] == 0


def test_invalid_jsonpath_expression():
    """Test handling of invalid JSONPath expression."""
    json_data = {"name": "Test"}

    # Invalid JSONPath syntax
    result = extract_jsonpath(json_data, "$[invalid")

    assert "error" in result
    assert result["error"] == "INVALID_JSONPATH"
    assert result["value"] is None
    assert result["items"] == []
    assert result["count"] == 0


def test_extract_from_root():
    """Test extracting the root element."""
    json_data = {"name": "Root Object"}

    result = extract_jsonpath(json_data, "$")

    assert result["value"] == json_data
    assert result["items"] == [json_data]
    assert result["count"] == 1


def test_extract_numeric_values():
    """Test extracting numeric values."""
    json_data = {"price": 19.99, "quantity": 5}

    result_price = extract_jsonpath(json_data, "$.price")
    result_qty = extract_jsonpath(json_data, "$.quantity")

    assert result_price["value"] == 19.99
    assert result_qty["value"] == 5


def test_extract_boolean_values():
    """Test extracting boolean values."""
    json_data = {"active": True, "deleted": False}

    result_active = extract_jsonpath(json_data, "$.active")
    result_deleted = extract_jsonpath(json_data, "$.deleted")

    assert result_active["value"] is True
    assert result_deleted["value"] is False


def test_extract_null_value():
    """Test extracting null values."""
    json_data = {"optional_field": None}

    result = extract_jsonpath(json_data, "$.optional_field")

    assert result["value"] is None
    assert result["count"] == 1


def test_extract_empty_array():
    """Test extracting from empty array."""
    json_data = {"items": []}

    result = extract_jsonpath(json_data, "$.items[*]")

    assert result["items"] == []
    assert result["count"] == 0


def test_extract_mixed_types_from_array():
    """Test extracting mixed types from array."""
    json_data = {"values": [1, "two", 3.0, True, None]}

    result = extract_jsonpath(json_data, "$.values[*]")

    assert result["items"] == [1, "two", 3.0, True, None]
    assert result["count"] == 5


# ============================================================================
# extract_nested_field Tests
# ============================================================================

def test_nested_field_simple():
    """Test simple nested field extraction."""
    data = {"a": {"b": {"c": 123}}}

    result = extract_nested_field(data, "a.b.c")

    assert result == 123


def test_nested_field_top_level():
    """Test top-level field extraction."""
    data = {"name": "Alice"}

    result = extract_nested_field(data, "name")

    assert result == "Alice"


def test_nested_field_missing_with_default():
    """Test missing nested field with default."""
    data = {"x": 1}

    result = extract_nested_field(data, "y.z", default="N/A")

    assert result == "N/A"


def test_nested_field_partial_path():
    """Test when partial path exists but not full path."""
    data = {"a": {"b": 123}}

    result = extract_nested_field(data, "a.b.c", default="missing")

    assert result == "missing"


def test_nested_field_non_dict_value():
    """Test when intermediate value is not a dict."""
    data = {"a": 123}

    result = extract_nested_field(data, "a.b", default="error")

    assert result == "error"


# ============================================================================
# safe_json_loads Tests
# ============================================================================

def test_safe_json_loads_valid():
    """Test parsing valid JSON."""
    result = safe_json_loads('{"valid": true}')

    assert result == {"valid": True}


def test_safe_json_loads_invalid_with_default():
    """Test parsing invalid JSON with default."""
    result = safe_json_loads("invalid json", default={})

    assert result == {}


def test_safe_json_loads_invalid_without_default():
    """Test parsing invalid JSON without default."""
    result = safe_json_loads("invalid json")

    assert result is None


def test_safe_json_loads_array():
    """Test parsing JSON array."""
    result = safe_json_loads('[1, 2, 3]')

    assert result == [1, 2, 3]


def test_safe_json_loads_null():
    """Test parsing null."""
    result = safe_json_loads('null')

    assert result is None


def test_safe_json_loads_number():
    """Test parsing number."""
    result = safe_json_loads('42')

    assert result == 42


def test_safe_json_loads_string():
    """Test parsing JSON string."""
    result = safe_json_loads('"hello"')

    assert result == "hello"
