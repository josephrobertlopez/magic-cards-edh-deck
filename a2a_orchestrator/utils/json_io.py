"""JSON I/O utilities for skill output formatting."""

import json
import sys
from typing import Any, Dict


def format_success_output(data: Dict[str, Any]) -> None:
    """
    Output success response as JSON to stdout.

    Args:
        data: Dictionary containing success data (must include 'status': 'success')
    """
    output = {"status": "success", **data}
    print(json.dumps(output, indent=2))


def format_error_output(error_message: str, exit_code: int = 1, context: Dict[str, Any] | None = None) -> None:
    """
    Output error response as JSON to stderr and exit with code.

    Args:
        error_message: Human-readable error description
        exit_code: Exit code (1=not found, 3=network, 5=conversion)
        context: Optional additional error context
    """
    output = {
        "status": "error",
        "error": error_message,
        "exit_code": exit_code
    }
    if context:
        output["context"] = context

    print(json.dumps(output, indent=2), file=sys.stderr)
    sys.exit(exit_code)
