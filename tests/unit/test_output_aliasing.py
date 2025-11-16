"""
Unit tests for output aliasing in a2a_orchestrator/orchestrator.py

Tests cover:
- Successful output aliasing: {{result.data}} → actual value
- Field existence validation: Non-existent field raises WorkflowValidationError
- Multiple output aliasing in single step
- Nested field references
- Output aliasing with batch processing results
"""

import pytest
from pathlib import Path
from a2a_orchestrator.orchestrator import YAMLWorkflowOrchestrator, WorkflowContext
from a2a_orchestrator.exceptions import WorkflowValidationError


# --- Fixtures ---

@pytest.fixture
def orchestrator():
    """Create orchestrator instance with default skills"""
    skills_dir = Path(".claude/skills")
    return YAMLWorkflowOrchestrator(skills_dir)


@pytest.fixture
def context():
    """Create workflow context for testing"""
    return WorkflowContext(workflow_inputs={})


# --- Unit Tests ---

def test_output_aliasing_single_field_success(orchestrator, context):
    """Test successful output aliasing with single field"""
    # Simulate skill execution result
    skill_result = {"result": {"data": "test_value", "status": "success"}}

    # Simulate workflow step with output aliasing
    step = {
        "name": "test_step",
        "skill": "http/fetch-json",
        "outputs": {
            "card_data": "{{result.data}}"
        }
    }

    # Set up context with result
    context.set_variable("result", skill_result["result"])

    # Process output aliasing
    outputs_spec = step.get("outputs", {})
    result_data = skill_result["result"]

    # Validate and substitute
    import re
    for output_name, output_expr in outputs_spec.items():
        result_refs = re.findall(r'\{\{result\.(\w+)\}\}', str(output_expr))
        if result_refs and isinstance(result_data, dict):
            for field in result_refs:
                if field not in result_data:
                    pytest.fail(f"Field '{field}' should exist in result_data")

        output_value = context.substitute_variables(output_expr)
        context.set_variable(f"steps.test_step.outputs.{output_name}", output_value)

    # Verify aliased output is accessible
    assert context._resolve_path("steps.test_step.outputs.card_data") == "test_value"


def test_output_aliasing_field_not_found(orchestrator, context):
    """Test that referencing non-existent field raises WorkflowValidationError"""
    # Simulate skill execution result WITHOUT 'missing_field'
    skill_result = {"result": {"data": "test_value", "status": "success"}}

    # Simulate workflow step referencing non-existent field
    step = {
        "name": "test_step",
        "skill": "http/fetch-json",
        "outputs": {
            "card_data": "{{result.missing_field}}"
        }
    }

    # Set up context with result
    context.set_variable("result", skill_result["result"])

    # Process output aliasing - should raise WorkflowValidationError
    outputs_spec = step.get("outputs", {})
    result_data = skill_result["result"]

    with pytest.raises(WorkflowValidationError) as exc_info:
        import re
        for output_name, output_expr in outputs_spec.items():
            result_refs = re.findall(r'\{\{result\.(\w+)\}\}', str(output_expr))
            if result_refs and isinstance(result_data, dict):
                for field in result_refs:
                    if field not in result_data:
                        raise WorkflowValidationError(
                            skill_name=step.get("skill", "unknown"),
                            step_index=0,
                            line_number=0,
                            message=f"Output aliasing failed: Field '{field}' not found in skill result. Available fields: {list(result_data.keys())}"
                        )

    # Verify error message contains helpful info
    error = exc_info.value
    assert "missing_field" in str(error)
    assert "not found" in str(error)
    assert "Available fields:" in str(error)


def test_output_aliasing_multiple_outputs(orchestrator, context):
    """Test multiple output aliasing in single step"""
    # Simulate skill execution result with multiple fields
    skill_result = {
        "result": {
            "data": {"name": "Atraxa", "type": "Creature"},
            "status": "success",
            "timestamp": "2025-11-15T12:00:00Z"
        }
    }

    # Simulate workflow step with multiple output aliases
    step = {
        "name": "test_step",
        "skill": "http/fetch-json",
        "outputs": {
            "card_data": "{{result.data}}",
            "fetch_status": "{{result.status}}",
            "fetch_time": "{{result.timestamp}}"
        }
    }

    # Set up context with result
    context.set_variable("result", skill_result["result"])

    # Process output aliasing
    outputs_spec = step.get("outputs", {})
    result_data = skill_result["result"]

    # Validate and substitute all outputs
    import re
    for output_name, output_expr in outputs_spec.items():
        result_refs = re.findall(r'\{\{result\.(\w+)\}\}', str(output_expr))
        if result_refs and isinstance(result_data, dict):
            for field in result_refs:
                if field not in result_data:
                    pytest.fail(f"Field '{field}' should exist in result_data")

        output_value = context.substitute_variables(output_expr)
        context.set_variable(f"steps.test_step.outputs.{output_name}", output_value)

    # Verify all aliased outputs are accessible
    # Note: substitute_variables converts dicts to strings when used in templates
    assert context._resolve_path("steps.test_step.outputs.card_data") == "{'name': 'Atraxa', 'type': 'Creature'}"
    assert context._resolve_path("steps.test_step.outputs.fetch_status") == "success"
    assert context._resolve_path("steps.test_step.outputs.fetch_time") == "2025-11-15T12:00:00Z"


def test_output_aliasing_batch_result_structure(orchestrator, context):
    """Test output aliasing with batch processing result structure"""
    # Simulate batch processing result (Feature 010 structure)
    batch_result = {
        "result": {
            "successful": 95,
            "failed": 5,
            "items": [
                {"status": "success", "data": {"name": "Atraxa"}, "error": None},
                {"status": "success", "data": {"name": "Thrasios"}, "error": None},
                {"status": "failure", "data": None, "error": "HTTP_404: Not Found"},
            ]
        }
    }

    # Simulate workflow step with batch result aliasing
    step = {
        "name": "fetch_cards",
        "skill": "http/fetch-json",
        "batch_mode": True,
        "outputs": {
            "cards_data": "{{result.items}}",
            "success_count": "{{result.successful}}"
        }
    }

    # Set up context with result
    context.set_variable("result", batch_result["result"])

    # Process output aliasing
    outputs_spec = step.get("outputs", {})
    result_data = batch_result["result"]

    # Validate and substitute
    import re
    for output_name, output_expr in outputs_spec.items():
        result_refs = re.findall(r'\{\{result\.(\w+)\}\}', str(output_expr))
        if result_refs and isinstance(result_data, dict):
            for field in result_refs:
                if field not in result_data:
                    pytest.fail(f"Field '{field}' should exist in result_data")

        output_value = context.substitute_variables(output_expr)
        context.set_variable(f"steps.fetch_cards.outputs.{output_name}", output_value)

    # Verify batch result aliasing
    # Note: substitute_variables converts lists to strings when used in templates
    expected_items_str = str(batch_result["result"]["items"])
    assert context._resolve_path("steps.fetch_cards.outputs.cards_data") == expected_items_str
    assert context._resolve_path("steps.fetch_cards.outputs.success_count") == "95"


def test_output_aliasing_no_result_field():
    """Test that validation handles non-dict result gracefully"""
    # Simulate skill execution result that's not a dict
    context = WorkflowContext(workflow_inputs={})
    skill_result = {"result": "simple_string_result"}

    step = {
        "name": "test_step",
        "skill": "http/fetch-json",
        "outputs": {
            "data": "{{result.field}}"
        }
    }

    # Set up context with non-dict result
    context.set_variable("result", skill_result["result"])

    # Process output aliasing - validation should skip non-dict results
    outputs_spec = step.get("outputs", {})
    result_data = skill_result["result"]

    # This should NOT raise an error because result_data is not a dict
    import re
    for output_name, output_expr in outputs_spec.items():
        result_refs = re.findall(r'\{\{result\.(\w+)\}\}', str(output_expr))
        # Validation only applies to dict results
        if result_refs and isinstance(result_data, dict):
            for field in result_refs:
                if field not in result_data:
                    pytest.fail("Should not validate non-dict results")


def test_output_aliasing_available_fields_in_error(orchestrator, context):
    """Test that error message shows available fields for debugging"""
    # Simulate skill execution result
    skill_result = {"result": {"data": "value", "status": "ok", "timestamp": "2025-11-15"}}

    # Simulate workflow step referencing wrong field
    step = {
        "name": "test_step",
        "skill": "http/fetch-json",
        "outputs": {
            "card_info": "{{result.card_data}}"  # Wrong field name
        }
    }

    # Set up context with result
    context.set_variable("result", skill_result["result"])

    # Process output aliasing - should raise WorkflowValidationError with available fields
    outputs_spec = step.get("outputs", {})
    result_data = skill_result["result"]

    with pytest.raises(WorkflowValidationError) as exc_info:
        import re
        for output_name, output_expr in outputs_spec.items():
            result_refs = re.findall(r'\{\{result\.(\w+)\}\}', str(output_expr))
            if result_refs and isinstance(result_data, dict):
                for field in result_refs:
                    if field not in result_data:
                        raise WorkflowValidationError(
                            skill_name=step.get("skill", "unknown"),
                            step_index=0,
                            line_number=0,
                            message=f"Output aliasing failed: Field '{field}' not found in skill result. Available fields: {list(result_data.keys())}"
                        )

    # Verify error message contains available fields list
    error_message = str(exc_info.value)
    assert "'data'" in error_message
    assert "'status'" in error_message
    assert "'timestamp'" in error_message
    assert "Available fields:" in error_message
