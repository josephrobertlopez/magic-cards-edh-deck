"""
Unit tests for WorkflowSkill class.

Tests lazy loading, call stack initialization, circular detection, and error handling.
"""

import pytest
import os
from pathlib import Path
from a2a_orchestrator.workflow_skill import WorkflowSkill
from a2a_orchestrator.exceptions import WorkflowCircularRefError, WorkflowExecutionError


# Mock orchestrator for testing
class MockOrchestrator:
    """Simple mock orchestrator for isolated WorkflowSkill testing"""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.execute_count = 0

    async def execute_workflow(self, workflow, inputs):
        """Mock workflow execution"""
        self.execute_count += 1

        if self.should_fail:
            raise RuntimeError("Mock workflow execution failure")

        return {
            "output_file": "/tmp/mock_output.txt",
            "status": "success"
        }


@pytest.mark.unit
@pytest.mark.us1
class TestWorkflowSkillLazyLoading:
    """T019: Test lazy loading behavior"""

    @pytest.mark.asyncio
    async def test_lazy_loading_first_execute_loads_yaml(self, tmp_path):
        """First execute() loads YAML, workflow attribute is populated"""
        # Create a minimal test workflow YAML
        workflow_file = tmp_path / "test_workflow.yaml"
        workflow_file.write_text("""
name: "test_workflow"
description: "Test workflow for lazy loading"
inputs:
  test_input:
    type: string
    required: true
steps:
  - name: test_step
    skill: test/skill
    args:
      input: "{{inputs.test_input}}"
outputs:
  result: "{{steps.test_step.outputs.result}}"
""")

        orchestrator = MockOrchestrator()
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        # Before execute: workflow should be None
        assert workflow_skill.workflow is None, "Workflow should be None before first execute"

        # Execute workflow
        message = {
            "inputs": {"test_input": "test_value"},
            "context": {"call_stack": []}
        }
        await workflow_skill.execute(message)

        # After execute: workflow should be loaded and cached
        assert workflow_skill.workflow is not None, "Workflow should be loaded after first execute"
        assert workflow_skill.workflow["name"] == "test_workflow"

    @pytest.mark.asyncio
    async def test_lazy_loading_second_execute_reuses_cached(self, tmp_path):
        """Second execute() reuses cached workflow (no re-parsing)"""
        workflow_file = tmp_path / "test_workflow_cache.yaml"
        workflow_file.write_text("""
name: "cached_workflow"
steps:
  - name: step1
    skill: test/skill
    args:
      value: "test"
""")

        orchestrator = MockOrchestrator()
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        message = {
            "inputs": {},
            "context": {"call_stack": []}
        }

        # First execute loads YAML
        await workflow_skill.execute(message)
        first_workflow_ref = id(workflow_skill.workflow)

        # Second execute should reuse cached workflow (same object reference)
        await workflow_skill.execute(message)
        second_workflow_ref = id(workflow_skill.workflow)

        assert first_workflow_ref == second_workflow_ref, \
            "Workflow object should be the same (cached) on second execute"
        assert orchestrator.execute_count == 2, \
            "Orchestrator should be called twice (workflow reused)"


@pytest.mark.unit
@pytest.mark.us1
class TestWorkflowSkillCallStackInitialization:
    """T020: Test call_stack initialization"""

    @pytest.mark.asyncio
    async def test_call_stack_defaults_to_empty_list_if_missing(self, tmp_path):
        """When context.call_stack is missing, initialize to []"""
        workflow_file = tmp_path / "test_init.yaml"
        workflow_file.write_text("""
name: "init_test"
steps:
  - name: step1
    skill: test/skill
""")

        orchestrator = MockOrchestrator()
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        # Message WITHOUT call_stack
        message = {
            "inputs": {},
            "context": {}  # No call_stack field
        }

        await workflow_skill.execute(message)

        # After execute, call_stack should be initialized
        assert "call_stack" in message["context"], "call_stack should be initialized"
        assert isinstance(message["context"]["call_stack"], list), "call_stack should be a list"

    @pytest.mark.asyncio
    async def test_call_stack_defaults_when_context_missing(self, tmp_path):
        """When entire context is missing, initialize context and call_stack"""
        workflow_file = tmp_path / "test_no_context.yaml"
        workflow_file.write_text("""
name: "no_context_test"
steps:
  - name: step1
    skill: test/skill
""")

        orchestrator = MockOrchestrator()
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        # Message WITHOUT context at all
        message = {
            "inputs": {}
            # No "context" key
        }

        await workflow_skill.execute(message)

        # After execute, context and call_stack should exist AND be cleaned up
        assert "context" in message, "context should be initialized"
        assert "call_stack" in message["context"], "call_stack should be initialized"
        assert message["context"]["call_stack"] == [], \
            "call_stack should be empty after execute (cleanup in finally block)"


@pytest.mark.unit
@pytest.mark.us2b
class TestWorkflowSkillCircularDetection:
    """Test circular reference detection (used in US2b but foundational)"""

    @pytest.mark.asyncio
    async def test_circular_reference_raises_error(self, tmp_path):
        """Workflow already in call_stack raises WorkflowCircularRefError"""
        workflow_file = tmp_path / "circular.yaml"
        workflow_file.write_text("""
name: "circular_workflow"
steps:
  - name: step1
    skill: test/skill
""")

        orchestrator = MockOrchestrator()
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        # Message with circular_workflow already in call_stack
        message = {
            "inputs": {},
            "context": {
                "call_stack": ["parent_workflow", "circular_workflow"]
            }
        }

        with pytest.raises(WorkflowCircularRefError) as exc_info:
            await workflow_skill.execute(message)

        assert "circular_workflow" in str(exc_info.value)
        assert "Circular workflow reference detected" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.us2b
class TestWorkflowSkillErrorWrapping:
    """Test error context preservation (used in US2b but foundational)"""

    @pytest.mark.asyncio
    async def test_error_wrapping_preserves_call_stack(self, tmp_path):
        """Exceptions wrapped with WorkflowExecutionError including call_stack"""
        workflow_file = tmp_path / "failing.yaml"
        workflow_file.write_text("""
name: "failing_workflow"
steps:
  - name: step1
    skill: test/skill
""")

        orchestrator = MockOrchestrator(should_fail=True)
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        message = {
            "inputs": {},
            "context": {
                "call_stack": ["parent", "grandparent"]
            }
        }

        with pytest.raises(WorkflowExecutionError) as exc_info:
            await workflow_skill.execute(message)

        error = exc_info.value
        assert error.workflow == "failing_workflow"
        assert error.call_stack == ["parent", "grandparent", "failing_workflow"]
        assert isinstance(error.original_error, RuntimeError)
        assert "Mock workflow execution failure" in str(error.original_error)


@pytest.mark.unit
@pytest.mark.us2b
class TestWorkflowSkillCleanup:
    """Test call_stack cleanup in finally block"""

    @pytest.mark.asyncio
    async def test_call_stack_cleanup_on_success(self, tmp_path):
        """call_stack is popped after successful execution"""
        workflow_file = tmp_path / "cleanup_success.yaml"
        workflow_file.write_text("""
name: "cleanup_test"
steps:
  - name: step1
    skill: test/skill
""")

        orchestrator = MockOrchestrator()
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        message = {
            "inputs": {},
            "context": {
                "call_stack": ["parent"]
            }
        }

        initial_stack_length = len(message["context"]["call_stack"])
        await workflow_skill.execute(message)
        final_stack_length = len(message["context"]["call_stack"])

        # Call stack should be back to original length (popped in finally)
        assert final_stack_length == initial_stack_length, \
            "call_stack should be cleaned up after execute"

    @pytest.mark.asyncio
    async def test_call_stack_cleanup_on_failure(self, tmp_path):
        """call_stack is popped even when execution fails"""
        workflow_file = tmp_path / "cleanup_fail.yaml"
        workflow_file.write_text("""
name: "cleanup_fail_test"
steps:
  - name: step1
    skill: test/skill
""")

        orchestrator = MockOrchestrator(should_fail=True)
        workflow_skill = WorkflowSkill(str(workflow_file), orchestrator)

        message = {
            "inputs": {},
            "context": {
                "call_stack": ["parent"]
            }
        }

        initial_stack_length = len(message["context"]["call_stack"])

        with pytest.raises(WorkflowExecutionError):
            await workflow_skill.execute(message)

        final_stack_length = len(message["context"]["call_stack"])

        # Even on failure, call_stack should be cleaned up
        assert final_stack_length == initial_stack_length, \
            "call_stack should be cleaned up even on failure (finally block)"
