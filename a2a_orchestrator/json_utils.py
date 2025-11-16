"""
JSONPath extraction utilities for domain-agnostic JSON field access.

Feature 009: Domain-Agnostic Skills
User Story 3: JSONPath Field Extraction

This module provides generic JSONPath extraction capabilities that work with
any JSON structure, enabling workflows to access nested fields, array elements,
and complex data structures without domain-specific code.
"""

import json
from typing import Any, Union, List
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError


def extract_jsonpath(
    json_data: Union[str, dict, list],
    jsonpath: str,
    default_value: Any = None
) -> dict:
    """
    Extract data from JSON using JSONPath expressions.

    Args:
        json_data: JSON string, dict, or list to extract from
        jsonpath: JSONPath expression (e.g., "$.image_uris.large", "$.products[*].name")
        default_value: Value to return if no matches found (default: None)

    Returns:
        dict with keys:
            - "value": Single extracted value (for scalar results)
            - "items": List of extracted values (for array results)
            - "count": Number of matches found
            - "error": Error code if extraction failed (optional)

    Examples:
        >>> extract_jsonpath('{"name": "Bob"}', '$.name')
        {'value': 'Bob', 'items': ['Bob'], 'count': 1}

        >>> extract_jsonpath('{"items": [{"x": 1}, {"x": 2}]}', '$.items[*].x')
        {'value': None, 'items': [1, 2], 'count': 2}

        >>> extract_jsonpath('{}', '$.missing', default_value='N/A')
        {'value': 'N/A', 'items': [], 'count': 0}
    """
    # Parse JSON if string
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return {
                "value": default_value,
                "items": [],
                "count": 0,
                "error": "INVALID_JSON",
                "error_details": str(e)
            }
    else:
        data = json_data

    # Parse JSONPath expression
    try:
        jsonpath_expr = parse(jsonpath)
    except (JsonPathParserError, Exception) as e:
        return {
            "value": default_value,
            "items": [],
            "count": 0,
            "error": "INVALID_JSONPATH",
            "error_details": str(e)
        }

    # Find matches
    matches = jsonpath_expr.find(data)

    # Extract values
    values = [match.value for match in matches]

    # Handle no matches
    if not values:
        return {
            "value": default_value,
            "items": [],
            "count": 0
        }

    # Return results
    # Single value: use "value" field
    # Multiple values: use "items" field
    if len(values) == 1:
        return {
            "value": values[0],
            "items": values,
            "count": len(values)
        }
    else:
        return {
            "value": None,  # Multiple matches - use items instead
            "items": values,
            "count": len(values)
        }


def extract_nested_field(data: dict, field_path: str, default: Any = None) -> Any:
    """
    Extract a nested field from a dict using dot notation.

    This is a simpler alternative to JSONPath for basic field access.

    Args:
        data: Dictionary to extract from
        field_path: Dot-separated field path (e.g., "user.address.city")
        default: Default value if field not found

    Returns:
        Field value or default

    Examples:
        >>> extract_nested_field({'a': {'b': {'c': 123}}}, 'a.b.c')
        123

        >>> extract_nested_field({'x': 1}, 'y.z', default='N/A')
        'N/A'
    """
    keys = field_path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string, returning default on error.

    Args:
        json_str: JSON string to parse
        default: Value to return on parse error

    Returns:
        Parsed JSON data or default value

    Examples:
        >>> safe_json_loads('{"valid": true}')
        {'valid': True}

        >>> safe_json_loads('invalid json', default={})
        {}
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default
