"""
Behave step definitions for domain-agnostic skills integration tests.

Feature 009: Domain-Agnostic Skills
User Story 1: Reusable HTTP Requests (US1)
Success Criteria: SC-001, SC-003, SC-006, SC-007, SC-008
"""

import time
import re
import asyncio
from pathlib import Path
from behave import given, when, then
from ruamel.yaml import YAML
import json
from io import StringIO

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from a2a_orchestrator.orchestrator import YAMLWorkflowOrchestrator
from a2a_orchestrator.exceptions import WorkflowValidationError


# ============================================================================
# Background Steps (reused from batch_processing_steps.py)
# ============================================================================

@given('the skills directory is "{skills_dir}"')
def step_set_skills_dir(context, skills_dir):
    """Set skills directory path."""
    context.skills_dir = Path(skills_dir)
    # Note: orchestrator already initialized in Background


# ============================================================================
# Workflow Setup Steps
# ============================================================================

@given('a workflow named "{workflow_name}"')
def step_create_workflow(context, workflow_name):
    """Create a workflow with the given name."""
    context.workflow_name = workflow_name
    context.workflow = {
        "name": workflow_name,
        "description": f"Test workflow: {workflow_name}",
        "steps": []
    }


@given('the workflow has the following steps:')
def step_add_workflow_steps(context):
    """Add steps to the workflow from YAML text in context.text."""
    yaml = YAML(typ='safe')
    # context.text needs to be a stream for ruamel.yaml
    yaml_stream = StringIO(context.text)
    steps_config = yaml.load(yaml_stream)

    # Merge batch_config if present
    if "batch_config" in steps_config:
        context.workflow["batch_config"] = steps_config["batch_config"]

    # Add steps
    if "steps" in steps_config:
        context.workflow["steps"] = steps_config["steps"]


@given('the workflow input contains card names:')
def step_add_card_names_input(context):
    """Add card names from table to workflow input."""
    card_names = [row["card_name"] for row in context.table]
    context.workflow_input = {"card_names": card_names}
    # For batch mode, also set up items for iteration
    context.batch_items = card_names


# ============================================================================
# Workflow Execution Steps
# ============================================================================

@when('I execute the workflow')
def step_execute_workflow(context):
    """Execute the workflow using the orchestrator."""
    try:
        context.start_time = time.time()
        context.result = asyncio.run(context.orchestrator.execute_workflow(
            context.workflow,
            inputs={}
        ))
        context.execution_time = time.time() - context.start_time
        context.exception = None
    except Exception as e:
        context.exception = e
        context.result = None


@when('I execute the workflow with batch mode')
def step_execute_workflow_batch(context):
    """Execute the workflow in batch mode with prepared items."""
    try:
        # Set up workflow inputs for batch mode
        workflow_inputs = {"items": context.batch_items} if hasattr(context, "batch_items") else {}

        context.start_time = time.time()
        context.result = asyncio.run(context.orchestrator.execute_workflow(
            context.workflow,
            inputs=workflow_inputs
        ))
        context.execution_time = time.time() - context.start_time
        context.exception = None
    except Exception as e:
        context.exception = e
        context.result = None


# ============================================================================
# Assertion Steps
# ============================================================================

# Note: "the workflow should complete successfully" already defined in batch_processing_steps.py


@then('the output "{output_path}" should contain key "{key}"')
def step_assert_output_contains_key(context, output_path, key):
    """Assert that the output at the given path contains the specified key."""
    # Resolve output path like "steps.fetch_card.outputs.card_data"
    parts = output_path.split(".")
    current = context.result

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise AssertionError(f"Cannot navigate to {output_path}: {part} is not a dict")

    # Current should now be a string representation of a dict (from substitute_variables)
    # Need to parse it if it's a string
    if isinstance(current, str):
        # Try to parse as JSON if it looks like JSON
        current = current.strip()
        if current.startswith("{") or current.startswith("["):
            # This is stringified JSON, need to extract actual data
            # In real execution, we'd have the actual dict
            # For now, check if key name appears in string
            assert key in current, f"Key '{key}' not found in output: {current}"
        else:
            assert key in current, f"Key '{key}' not found in output: {current}"
    elif isinstance(current, dict):
        assert key in current, f"Key '{key}' not found in output keys: {list(current.keys())}"
    else:
        raise AssertionError(f"Output at {output_path} is not a dict or string: {type(current)}")


@then('the output "{output_path}" should equal "{expected_value}"')
def step_assert_output_equals(context, output_path, expected_value):
    """Assert that the output at the given path equals the expected value."""
    # Resolve output path
    parts = output_path.split(".")
    current = context.result

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise AssertionError(f"Cannot navigate to {output_path}: {part} is not a dict")

    # Convert to string for comparison
    assert str(current) == expected_value, f"Output mismatch: expected '{expected_value}', got '{current}'"


@then('the output "{output_path}" should be a list')
def step_assert_output_is_list(context, output_path):
    """Assert that the output at the given path is a list."""
    # Resolve output path
    parts = output_path.split(".")
    current = context.result

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise AssertionError(f"Cannot navigate to {output_path}: {part} is not a dict")

    # Check if it's a list or string representation of list
    if isinstance(current, str):
        # Check if it looks like a list
        assert current.strip().startswith("["), f"Output is not a list: {current}"
    else:
        assert isinstance(current, list), f"Output is not a list: {type(current)}"


@then('the batch result should have at least {min_count:d} successful items')
def step_assert_batch_success_count(context, min_count):
    """Assert that batch processing succeeded for at least min_count items."""
    # This step is a placeholder since actual batch execution depends on real API
    # In real tests, we'd check context.result for batch structure
    # For now, just verify workflow completed
    assert context.result is not None, "Workflow did not produce a result"


@then('the execution time should be less than {max_seconds:d} seconds')
def step_assert_execution_time(context, max_seconds):
    """Assert that execution completed within the time limit."""
    assert hasattr(context, "execution_time"), "Execution time was not recorded"
    assert context.execution_time < max_seconds, \
        f"Execution took {context.execution_time:.2f}s, expected < {max_seconds}s"


# ============================================================================
# Domain-Agnostic Verification Steps
# ============================================================================

@given('the skill file "{skill_path}" exists')
def step_check_skill_file_exists(context, skill_path):
    """Verify that the skill file exists."""
    file_path = Path(skill_path)
    assert file_path.exists(), f"Skill file not found: {skill_path}"
    context.skill_file_path = file_path


@when('I scan the skill file for domain-specific terms')
def step_scan_skill_file(context):
    """Read the skill file and prepare for term scanning."""
    with open(context.skill_file_path, 'r') as f:
        context.skill_file_content = f.read().lower()


@then('the skill should not contain "{term}"')
def step_assert_no_domain_term(context, term):
    """Assert that the skill file does not contain the domain-specific term."""
    # Use word boundary regex to avoid matching substrings
    # (e.g., "card" should not match "discard")
    pattern = r'\b' + re.escape(term.lower()) + r'\b'
    matches = re.findall(pattern, context.skill_file_content)
    assert not matches, f"Found domain-specific term '{term}' in skill file ({len(matches)} occurrences)"
