"""
Config Loader: Load and validate strategy configs and knowledge base from JSON files.

This module provides protocol-first configuration loading for domain-agnostic resource fetching.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import jsonschema
except ImportError:
    raise ImportError("jsonschema library required. Install with: pip install jsonschema")


# Setup logging
logger = logging.getLogger(__name__)


# JSON Schema for KnowledgeBase validation
KNOWLEDGE_BASE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["knowledge_base"],
    "properties": {
        "knowledge_base": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["keywords", "fact", "title"],
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search terms that trigger this fact"
                    },
                    "fact": {
                        "type": "string",
                        "description": "The factual information"
                    },
                    "title": {
                        "type": "string",
                        "description": "Short title for fact categorization"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.5,
                        "description": "Confidence score (0.0-1.0)"
                    }
                }
            }
        }
    }
}


def load_strategy_configs(config_dirs: List[Path] = None) -> Dict[str, Dict]:
    """
    Discover and load all strategy config files from search paths.

    Args:
        config_dirs: List of directories to search. If None, uses default search paths:
            - ~/.config/resource-fetcher/strategies/ (user configs)
            - .config/strategies/ (repo builtin configs)

    Returns:
        Dict[str, Dict]: Domain name → validated strategy config

    Raises:
        jsonschema.ValidationError: If any config file fails schema validation
        FileNotFoundError: If config_dirs specified but don't exist
        json.JSONDecodeError: If config file contains invalid JSON
    """
    if config_dirs is None:
        # Default search paths (user > builtin precedence)
        config_dirs = [
            Path.home() / ".config" / "resource-fetcher" / "strategies",  # User configs
            Path(__file__).parent.parent / ".config" / "strategies"        # Repo builtins
        ]

    # Load strategy schema for validation
    schema_path = Path(__file__).parent.parent / ".config" / "strategies" / "schema.json"
    if schema_path.exists():
        with open(schema_path) as f:
            strategy_schema = json.load(f)
    else:
        logger.warning(f"Strategy schema not found at {schema_path} - skipping validation")
        strategy_schema = None

    strategies = {}
    loaded_from = []

    for search_path in config_dirs:
        if not search_path.exists():
            continue

        for config_file in sorted(search_path.glob("*.json")):
            # Skip schema.json itself
            if config_file.name == "schema.json":
                continue

            domain = config_file.stem

            # First match wins (user > builtin)
            if domain in strategies:
                continue

            try:
                with open(config_file) as f:
                    config = json.load(f)

                # Validate against schema if available
                if strategy_schema:
                    jsonschema.validate(config, strategy_schema)

                strategies[domain] = config
                loaded_from.append(f"{domain} ({config_file})")

            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Invalid JSON in strategy config {config_file}: {str(e)}",
                    e.doc, e.pos
                )
            except jsonschema.ValidationError as e:
                raise jsonschema.ValidationError(
                    f"Invalid strategy config '{config_file}'\n"
                    f"  - {e.message}\n"
                    f"  See schema: .config/strategies/schema.json"
                )

    # Log which strategies were loaded (FR-014)
    if loaded_from:
        logger.info(f"Loaded {len(strategies)} strategy config(s): {', '.join([s.split()[0] for s in loaded_from])}")
    else:
        logger.warning("No strategy configs found in search paths")

    return strategies


def load_knowledge_base(filepath: Path = None) -> List[Dict]:
    """
    Load search oracle knowledge base from JSON file.

    Args:
        filepath: Path to knowledge base JSON. If None, uses .config/oracle_knowledge.json

    Returns:
        List[Dict]: List of knowledge base entries (each with keywords, fact, title, confidence)

    Raises:
        jsonschema.ValidationError: If knowledge base fails schema validation
        FileNotFoundError: If filepath doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if filepath is None:
        filepath = Path(__file__).parent.parent / ".config" / "oracle_knowledge.json"

    if not filepath.exists():
        logger.warning(f"Knowledge base not found at {filepath} - returning empty list")
        return []

    try:
        with open(filepath) as f:
            data = json.load(f)

        # Validate against schema
        jsonschema.validate(data, KNOWLEDGE_BASE_SCHEMA)

        kb = data.get("knowledge_base", [])
        logger.info(f"Loaded {len(kb)} knowledge base entries from {filepath}")
        return kb

    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in knowledge base {filepath}: {str(e)}",
            e.doc, e.pos
        )
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            f"Invalid knowledge base config '{filepath}'\n"
            f"  - {e.message}"
        )


def validate_api_config(
    api_url_template: str,
    response_schema: Dict,
    multi_delimiter: str = "//"
) -> None:
    """
    Validate API configuration parameters for correctness.

    Args:
        api_url_template: API URL with {identifier} placeholder
        response_schema: JSONPath mappings dict
        multi_delimiter: Multi-resource separator (default: "//")

    Returns:
        None (raises exception on validation failure)

    Raises:
        ValueError: If api_url_template missing {identifier} placeholder
        ValueError: If multi_delimiter is empty or >5 characters
        TypeError: If response_schema is not a dict
    """
    # Validate placeholder presence in URL template
    if "{identifier}" not in api_url_template:
        raise ValueError(
            "api_url_template must contain {identifier} placeholder. "
            f"Example: 'https://api.scryfall.com/cards/named?fuzzy={{identifier}}'"
        )

    # Validate response_schema type
    if not isinstance(response_schema, dict):
        raise TypeError(f"response_schema must be a dict, got {type(response_schema).__name__}")

    # Validate delimiter length constraints
    if not multi_delimiter:
        raise ValueError("multi_delimiter cannot be empty")

    if len(multi_delimiter) > 5:
        raise ValueError(
            f"multi_delimiter must be 1-5 characters (got {len(multi_delimiter)}). "
            f"Provided: '{multi_delimiter}'"
        )
