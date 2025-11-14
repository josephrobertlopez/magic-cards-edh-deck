"""Argument parsing utilities for skill CLI wrappers."""

import argparse
from typing import Any, Dict


def parse_skill_args(parser: argparse.ArgumentParser, args: list[str] | None = None) -> Dict[str, Any]:
    """
    Parse skill command-line arguments and return as dictionary.

    Args:
        parser: Configured ArgumentParser instance
        args: Optional argument list (defaults to sys.argv)

    Returns:
        Dictionary of parsed arguments
    """
    parsed = parser.parse_args(args)
    return vars(parsed)
