"""
A2A Orchestrator Exception Classes

Custom exceptions for workflow validation and execution errors.
"""


class WorkflowValidationError(Exception):
    """
    Raised when workflow validation fails before execution.

    Attributes:
        skill_name: Name of the missing/invalid skill
        step_index: Index of the step containing the error (1-based)
        line_number: YAML line number where the error occurred
        message: Human-readable error message
    """

    def __init__(self, skill_name: str, step_index: int, line_number: int, message: str = None):
        self.skill_name = skill_name
        self.step_index = step_index
        self.line_number = line_number

        if message is None:
            message = f"Skill '{skill_name}' not found (referenced at step {step_index}: line {line_number})"

        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class WorkflowCircularRefError(Exception):
    """
    Raised when circular workflow reference detected (A→B→A).

    Attributes:
        call_stack: List of workflow names showing the circular path
        message: Human-readable error message with full call path
    """

    def __init__(self, call_stack: list):
        self.call_stack = call_stack
        cycle = " → ".join(call_stack)
        self.message = f"Circular workflow reference detected: {cycle}"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class WorkflowExecutionError(Exception):
    """
    Raised when sub-workflow execution fails (preserves context).

    Attributes:
        workflow: Name of the workflow that failed
        call_stack: List of workflow names in execution path
        original_error: The underlying exception that caused the failure
        message: Human-readable error message with full context
    """

    def __init__(self, workflow: str, call_stack: list, original_error: Exception):
        self.workflow = workflow
        self.call_stack = call_stack
        self.original_error = original_error

        call_path = " → ".join(call_stack)
        self.message = (
            f"Workflow '{workflow}' failed in call stack: {call_path}\n"
            f"Original error: {original_error}"
        )
        super().__init__(self.message)

    def __str__(self):
        return self.message


class SkillNotFoundError(Exception):
    """
    Raised when skill cannot be found in any supported format.

    Attributes:
        skill_name: Name of the skill that was not found
        checked_paths: List of paths that were checked
        message: Human-readable error message with all checked locations
    """

    def __init__(self, skill_name: str, checked_paths: list):
        self.skill_name = skill_name
        self.checked_paths = checked_paths

        paths_str = "\n  - ".join(str(p) for p in checked_paths)
        self.message = (
            f"Skill '{skill_name}' not found. Checked paths:\n  - {paths_str}"
        )
        super().__init__(self.message)

    def __str__(self):
        return self.message


class SkillLoadError(Exception):
    """
    Raised when skill file exists but cannot be loaded (invalid YAML, missing fields, etc.).

    Attributes:
        skill_name: Name of the skill that failed to load
        skill_path: Path to the skill file
        reason: Description of why loading failed
        message: Human-readable error message
    """

    def __init__(self, skill_name: str, skill_path: str, reason: str):
        self.skill_name = skill_name
        self.skill_path = skill_path
        self.reason = reason

        self.message = (
            f"Failed to load skill '{skill_name}' from {skill_path}\n"
            f"Reason: {reason}"
        )
        super().__init__(self.message)

    def __str__(self):
        return self.message
