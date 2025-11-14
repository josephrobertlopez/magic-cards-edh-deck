"""
Unit tests for a2a_orchestrator/orchestrator.py

Tests cover:
- Workflow validation (skill reference checking)
- Line number tracking in error messages
- WorkflowValidationError exception handling
"""

import pytest
from pathlib import Path
from ruamel.yaml import YAML
from a2a_orchestrator.orchestrator import YAMLWorkflowOrchestrator
from a2a_orchestrator.exceptions import WorkflowValidationError


# --- Fixtures ---

@pytest.fixture
def orchestrator():
    """Create orchestrator instance with default skills"""
    skills_dir = Path(".claude/skills")
    return YAMLWorkflowOrchestrator(skills_dir)


@pytest.fixture
def valid_workflow():
    """Valid workflow with registered skills"""
    return {
        "name": "test-workflow",
        "description": "Test workflow with valid skills",
        "steps": [
            {"name": "fetch", "skill": "data/fetch-from-api", "input": {}, "output_var": "result"}
        ]
    }


@pytest.fixture
def invalid_workflow():
    """Invalid workflow with non-existent skill"""
    return {
        "name": "test-invalid",
        "description": "Test workflow with invalid skill",
        "steps": [
            {"name": "fetch", "skill": "data/fetch-cards", "input": {}, "output_var": "result"}
        ]
    }


# --- Unit Tests ---

def test_validate_workflow_success(orchestrator, valid_workflow):
    """Test workflow validation passes for valid skills"""
    # Should not raise exception
    orchestrator.validate_workflow(valid_workflow)


def test_validate_workflow_invalid_skill(orchestrator, invalid_workflow):
    """Test workflow validation raises error for invalid skill"""
    with pytest.raises(WorkflowValidationError) as exc_info:
        orchestrator.validate_workflow(invalid_workflow)

    assert "data/fetch-cards" in str(exc_info.value)
    assert "not found" in str(exc_info.value)


def test_validate_workflow_error_attributes(orchestrator, invalid_workflow):
    """Test WorkflowValidationError contains correct attributes"""
    with pytest.raises(WorkflowValidationError) as exc_info:
        orchestrator.validate_workflow(invalid_workflow)

    error = exc_info.value
    assert error.skill_name == "data/fetch-cards"
    assert error.step_index == 1
    assert isinstance(error.line_number, int)


def test_validate_workflow_empty_steps(orchestrator):
    """Test workflow validation handles empty steps list"""
    workflow = {"name": "empty", "description": "No steps", "steps": []}
    orchestrator.validate_workflow(workflow)  # Should not raise


def test_validate_workflow_missing_skill_key(orchestrator):
    """Test workflow validation handles steps without 'skill' key"""
    workflow = {
        "name": "test",
        "description": "Step missing skill key",
        "steps": [{"name": "broken-step", "input": {}}]
    }
    orchestrator.validate_workflow(workflow)  # Should not raise


def test_load_workflow_with_line_numbers():
    """Test load_workflow preserves line number metadata"""
    import tempfile
    from ruamel.yaml import YAML

    yaml_content = """name: test
description: Test workflow
steps:
  - name: step1
    skill: data/fetch-from-api
    input: {}
"""

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        f.write(yaml_content)
        f.flush()
        workflow_path = f.name

    skills_dir = Path(".claude/skills")
    orchestrator = YAMLWorkflowOrchestrator(skills_dir)
    workflow = orchestrator.load_workflow(workflow_path)

    # Verify ruamel.yaml preserved line metadata
    assert hasattr(workflow['steps'][0], 'lc')

    import os
    os.unlink(workflow_path)


def test_registered_skills_present(orchestrator):
    """Test orchestrator has expected builtin skills registered"""
    assert "data/fetch-from-api" in orchestrator.registered_skills
    assert "presentation/place-images-in-pptx" in orchestrator.registered_skills
    assert "pdf/convert-to-pdf" in orchestrator.registered_skills
