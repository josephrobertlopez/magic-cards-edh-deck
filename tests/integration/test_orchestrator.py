"""
Integration tests for A2A workflow orchestration

Tests cover:
- Full workflow execution via orchestrator
- A2A message passing between skills
- Multi-step workflow coordination
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from a2a_orchestrator.orchestrator import YAMLWorkflowOrchestrator, load_yaml_workflow


# --- Fixtures ---

@pytest.fixture
def temp_output_dir():
    """Create temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_decklist():
    """Create minimal test decklist"""
    content = """Forest
Island
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(content)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def test_workflow(temp_output_dir):
    """Create test workflow YAML"""
    workflow_content = f"""name: test-orchestrator
description: Test workflow for integration testing

steps:
  - name: fetch-cards
    skill: data/fetch-from-api
    input:
      decklist_path: ${{input.decklist_path}}
      output_dir: {temp_output_dir}
      manifest_path: {temp_output_dir}/manifest.json
    output_var: fetch_result

output:
  status: ${{fetch_result.status}}
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        f.write(workflow_content)
        yield f.name
    os.unlink(f.name)


# --- Integration Tests ---

@pytest.mark.asyncio
async def test_workflow_execution(test_workflow, test_decklist, temp_output_dir):
    """Test full workflow execution through orchestrator"""
    # Load workflow
    workflow = load_yaml_workflow(test_workflow)

    # Create orchestrator
    skills_dir = Path(".claude/skills")
    orchestrator = YAMLWorkflowOrchestrator(skills_dir)

    # Execute workflow
    inputs = {"decklist_path": test_decklist}
    result = await orchestrator.execute_workflow(workflow, inputs)

    # Verify result structure
    assert isinstance(result, dict)

    # Verify manifest created
    manifest_path = os.path.join(temp_output_dir, "manifest.json")
    assert os.path.exists(manifest_path)

    # Verify message log created
    log_path = Path(".claude/state/test-orchestrator_messages.json")
    assert log_path.exists()

    # Verify A2A messages logged
    with open(log_path, 'r') as f:
        messages = json.load(f)

    assert len(messages) >= 2  # REQUEST + RESPONSE at minimum
    assert any(msg["message_type"] == "REQUEST" for msg in messages)
    assert any(msg["message_type"] == "RESPONSE" for msg in messages)

    # Clean up log
    log_path.unlink()


@pytest.mark.asyncio
async def test_workflow_validation_before_execution():
    """Test that validation runs before any steps execute"""
    from a2a_orchestrator.exceptions import WorkflowValidationError

    # Create invalid workflow
    invalid_workflow = {
        "name": "invalid-test",
        "description": "Workflow with invalid skill",
        "steps": [
            {"name": "broken", "skill": "nonexistent/skill", "input": {}}
        ]
    }

    skills_dir = Path(".claude/skills")
    orchestrator = YAMLWorkflowOrchestrator(skills_dir)

    # Should raise validation error before executing any steps
    with pytest.raises(WorkflowValidationError):
        await orchestrator.execute_workflow(invalid_workflow, {})


def test_synchronous_workflow_loading(test_workflow):
    """Test workflow loading preserves line numbers"""
    workflow = load_yaml_workflow(test_workflow)

    assert "name" in workflow
    assert "steps" in workflow
    assert len(workflow["steps"]) >= 1

    # Verify line number metadata preserved
    assert hasattr(workflow["steps"][0], 'lc')
