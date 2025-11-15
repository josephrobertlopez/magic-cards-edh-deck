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


class BatchProcessingError(Exception):
    """
    Raised when batch processing fails below partial success threshold.

    Batch processing continues if ≥50% of batches succeed (partial success).
    This exception is raised when <50% of batches succeed, indicating
    systemic failure (e.g., API completely unreachable).

    Attributes:
        message: Human-readable error message with failure statistics
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class ContractValidationError(Exception):
    """
    Raised when skill contract validation fails at workflow load time.

    Contract validation is fail-fast: workflows are validated before execution
    starts to catch type mismatches, missing required parameters, and schema
    violations before making expensive API calls.

    Attributes:
        message: Detailed error message with JSON Pointer path to failed field

    Example:
        ContractValidationError: Skill input validation failed for 'fetch-card-data':
          'batch_size' must be integer, got string
          Path: /batch_size
          Expected: {type: integer, minimum: 1}
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class RateLimitError(Exception):
    """
    Raised when API rate limit is exceeded (HTTP 429).

    This is a transient error eligible for retry with exponential backoff.
    Retry logic should handle this exception and apply increasing delays
    (1s → 2s → 4s → 8s) before retrying.

    Attributes:
        message: Error message (e.g., "API rate limit exceeded")
        retry_after: Optional retry-after header value in seconds
    """

    def __init__(self, message: str, retry_after: int = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)

    def __str__(self):
        if self.retry_after:
            return f"{self.message} (retry after {self.retry_after}s)"
        return self.message


class TimeoutError(Exception):
    """
    Raised when request exceeds timeout threshold.

    This is a transient error eligible for retry. Per-request timeouts
    (default 30s) prevent hung connections from blocking batch processing.

    Attributes:
        message: Error message (e.g., "Request timeout after 30s")
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message
