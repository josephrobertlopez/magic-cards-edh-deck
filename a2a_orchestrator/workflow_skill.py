"""
WorkflowSkill - Wraps a workflow YAML as a Skill instance for composition.

This module implements the Workflow-as-Skill pattern, enabling workflows to call
other workflows recursively while maintaining uniform A2A message-passing interface.
"""

import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Use absolute imports for consistent exception identity across modules
from a2a_orchestrator.exceptions import WorkflowCircularRefError, WorkflowExecutionError


class WorkflowSkill:
    """
    Wraps a workflow YAML as a Skill for composition.

    Responsibilities:
    - Lazy load workflow YAML on first execution
    - Track call stack for circular reference detection
    - Execute sub-workflow via orchestrator delegation
    - Wrap execution errors with parent workflow context

    Attributes:
        workflow_path: Absolute or relative path to workflow YAML file
        workflow: Cached workflow definition (None until first load)
        orchestrator: Reference to parent orchestrator instance
    """

    def __init__(self, workflow_path: str, orchestrator):
        """
        Initialize with path (lazy load on execute).

        Args:
            workflow_path: Path to workflow YAML file
            orchestrator: Orchestrator instance for delegation
        """
        self.workflow_path = workflow_path
        self.workflow = None  # Lazy load
        self.orchestrator = orchestrator

    def _load_workflow(self) -> None:
        """
        Load workflow YAML (cached after first call).

        Raises:
            FileNotFoundError: Workflow file not found at workflow_path
            yaml.YAMLError: Invalid YAML syntax
            WorkflowValidationError: Missing required fields (name, steps)
        """
        if self.workflow is None:
            start_time = time.time()
            # Load raw YAML instead of using load_yaml_workflow
            import yaml
            from pathlib import Path
            workflow_file = Path(self.workflow_path)
            with workflow_file.open('r') as f:
                self.workflow = yaml.safe_load(f)
            load_time_ms = (time.time() - start_time) * 1000
            print(f"⚙️  Loaded workflow '{self.workflow.get('name', self.workflow_path)}' in {load_time_ms:.2f}ms")

    async def execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute workflow as a skill (A2A protocol).

        Args:
            message: A2A format with inputs, context (including call_stack)

        Returns:
            A2A format with status, result, context

        Raises:
            WorkflowCircularRefError: If circular reference detected
            WorkflowExecutionError: If sub-workflow execution fails
        """
        # T007: Lazy load workflow YAML
        self._load_workflow()

        # T008: Initialize call_stack if missing (default to empty list)
        if "context" not in message:
            message["context"] = {}
        if "call_stack" not in message["context"]:
            message["context"]["call_stack"] = []

        call_stack = message["context"]["call_stack"]
        workflow_name = self.workflow.get("name", self.workflow_path)

        # T009: Circular reference detection before workflow execution
        if workflow_name in call_stack:
            cycle_start = call_stack.index(workflow_name)
            cycle_path = call_stack[cycle_start:] + [workflow_name]
            raise WorkflowCircularRefError(cycle_path)

        # Push workflow to call stack
        call_stack.append(workflow_name)

        try:
            # T010: Delegate execution to orchestrator
            result = await self.orchestrator.execute_workflow(
                self.workflow,
                message.get("inputs", {})
            )

            return {
                "status": "success",
                "result": result,
                "context": message["context"]
            }

        except Exception as e:
            # T011: Wrap error with call_stack context
            raise WorkflowExecutionError(
                workflow=workflow_name,
                call_stack=call_stack.copy(),
                original_error=e
            ) from e

        finally:
            # T012: Call stack cleanup (always pop)
            if call_stack and call_stack[-1] == workflow_name:
                call_stack.pop()
