"""
Behave step definitions for html/extract-css skill integration tests.

Feature 009: Domain-Agnostic Skills
User Story 2: Universal HTML Extraction (US2)
Success Criteria: SC-002
"""

from behave import then


# ============================================================================
# HTML Extract Assertions
# ============================================================================

@then('the output "{output_path}" should contain "{expected_value}"')
def step_assert_output_contains_value(context, output_path, expected_value):
    """Assert that the output at the given path contains the expected value."""
    # Resolve output path like "steps.extract_names.outputs.card_names"
    parts = output_path.split(".")
    current = context.result

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise AssertionError(f"Cannot navigate to {output_path}: {part} is not a dict")

    # Check if current is a list containing the expected value
    if isinstance(current, list):
        assert expected_value in current, \
            f"Expected value '{expected_value}' not found in list: {current}"
    elif isinstance(current, str):
        # If it's a string representation of a list, check if value appears in string
        assert expected_value in current, \
            f"Expected value '{expected_value}' not found in output: {current}"
    else:
        raise AssertionError(f"Output at {output_path} is not a list or string: {type(current)}")


@then('the output "{output_path}" should be empty')
def step_assert_output_is_empty(context, output_path):
    """Assert that the output at the given path is an empty list."""
    # Resolve output path
    parts = output_path.split(".")
    current = context.result

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise AssertionError(f"Cannot navigate to {output_path}: {part} is not a dict")

    # Check if it's an empty list
    if isinstance(current, list):
        assert len(current) == 0, f"Expected empty list, got {len(current)} items: {current}"
    elif isinstance(current, str):
        # Check if it looks like an empty list
        assert current.strip() in ["[]", ""], f"Expected empty list, got: {current}"
    else:
        raise AssertionError(f"Output at {output_path} is not a list: {type(current)}")
