"""Skill contract validation using JSON Schema for fail-fast workflow loading.

This module provides contract-first validation for A2A skills, ensuring type safety
and catching errors at workflow load time (before expensive API calls are made).
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import json
import logging
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator


logger = logging.getLogger(__name__)


@dataclass
class SkillContract:
    """JSON Schema-based specification of skill input/output data structures.

    Enables fail-fast validation at workflow load time to catch type mismatches,
    missing required parameters, and schema violations before execution starts.

    Attributes:
        input_schema: JSON Schema (draft-07) for skill input parameters
        output_schema: JSON Schema (draft-07) for skill output data
        skill_name: Name of skill this contract belongs to (for error messages)

    Example:
        >>> contract = SkillContract(
        ...     skill_name="fetch-card-data",
        ...     input_schema={
        ...         "type": "object",
        ...         "properties": {
        ...             "card_name": {"type": "string", "minLength": 1}
        ...         },
        ...         "required": ["card_name"]
        ...     },
        ...     output_schema={
        ...         "type": "object",
        ...         "properties": {
        ...             "name": {"type": "string"},
        ...             "image_uris": {"type": "object"}
        ...         },
        ...         "required": ["name", "image_uris"]
        ...     }
        ... )
        >>> contract.validate_input({"card_name": "Sol Ring"})  # ✓ passes
        >>> contract.validate_input({"card_name": ""})  # ✗ fails: minLength
    """
    skill_name: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    def __post_init__(self):
        """Validate that input/output schemas are valid JSON Schema."""
        try:
            Draft7Validator.check_schema(self.input_schema)
        except jsonschema.SchemaError as e:
            raise ValueError(
                f"Invalid input schema for skill '{self.skill_name}': {e.message}"
            )

        try:
            Draft7Validator.check_schema(self.output_schema)
        except jsonschema.SchemaError as e:
            raise ValueError(
                f"Invalid output schema for skill '{self.skill_name}': {e.message}"
            )

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate skill input data against input schema.

        Args:
            input_data: Input parameters passed to skill

        Raises:
            ContractValidationError: If validation fails with actionable error message
                including JSON Pointer path to failed field

        Example:
            >>> contract.validate_input({"card_name": "Sol Ring"})  # ✓
            >>> contract.validate_input({"batch_size": "10"})  # ✗ wrong type
            ContractValidationError: Skill input validation failed for 'fetch-card-data':
                'batch_size' must be integer, got string
                Path: /batch_size
                Expected: {type: integer, minimum: 1}
        """
        try:
            validate(instance=input_data, schema=self.input_schema)
        except ValidationError as e:
            # Build JSON Pointer path to failed field
            path = "/" + "/".join(str(p) for p in e.path) if e.path else "/"

            # Format error message with context
            error_msg = (
                f"Skill input validation failed for '{self.skill_name}':\n"
                f"  {e.message}\n"
                f"  Path: {path}\n"
                f"  Expected: {json.dumps(e.schema, indent=2)}"
            )

            from a2a_orchestrator.exceptions import ContractValidationError
            raise ContractValidationError(error_msg)

    def validate_output(self, output_data: Dict[str, Any]) -> None:
        """Validate skill output data against output schema.

        Args:
            output_data: Output data returned by skill

        Raises:
            ContractValidationError: If validation fails

        Example:
            >>> contract.validate_output({"name": "Sol Ring", "image_uris": {...}})  # ✓
            >>> contract.validate_output({"name": "Sol Ring"})  # ✗ missing image_uris
        """
        try:
            validate(instance=output_data, schema=self.output_schema)
        except ValidationError as e:
            path = "/" + "/".join(str(p) for p in e.path) if e.path else "/"

            error_msg = (
                f"Skill output validation failed for '{self.skill_name}':\n"
                f"  {e.message}\n"
                f"  Path: {path}\n"
                f"  Expected: {json.dumps(e.schema, indent=2)}"
            )

            from a2a_orchestrator.exceptions import ContractValidationError
            raise ContractValidationError(error_msg)


def load_skill_contract(skill_frontmatter: Dict[str, Any]) -> Optional[SkillContract]:
    """Load SkillContract from skill SKILL.md frontmatter.

    Args:
        skill_frontmatter: Parsed YAML frontmatter from skill markdown file

    Returns:
        SkillContract instance, or None if contract not defined

    Example:
        >>> import frontmatter
        >>> with open('.claude/skills/fetch-card-data/SKILL.md') as f:
        ...     metadata = frontmatter.load(f)
        >>> contract = load_skill_contract(metadata)
    """
    if "contract" not in skill_frontmatter:
        return None

    contract_data = skill_frontmatter["contract"]
    skill_name = skill_frontmatter.get("name", "unknown")

    if "input" not in contract_data or "output" not in contract_data:
        logger.warning(
            f"Skill '{skill_name}' has incomplete contract "
            f"(missing input or output schema)"
        )
        return None

    return SkillContract(
        skill_name=skill_name,
        input_schema=contract_data["input"],
        output_schema=contract_data["output"]
    )


def validate_workflow_contracts(workflow_config: Dict[str, Any], skill_registry: Dict[str, Any]) -> None:
    """Validate all skill invocations in workflow against skill contracts.

    This function is called at workflow load time to fail fast on contract violations
    before execution starts. Validates that all skill inputs match their contracts.

    Args:
        workflow_config: Parsed workflow YAML configuration
        skill_registry: Dictionary mapping skill names to skill metadata (with contracts)

    Raises:
        ContractValidationError: If any skill invocation violates its contract

    Example:
        >>> workflow = {
        ...     "steps": [
        ...         {
        ...             "name": "fetch_data",
        ...             "skill": "fetch-card-data",
        ...             "args": {"card_name": "Sol Ring"}
        ...         }
        ...     ]
        ... }
        >>> validate_workflow_contracts(workflow, skill_registry)  # ✓ or raises
    """
    for step in workflow_config.get("steps", []):
        skill_name = step.get("skill")
        if not skill_name:
            continue  # Sub-workflow step, not a skill

        # Look up skill contract from registry
        if skill_name not in skill_registry:
            raise ValueError(
                f"Workflow references unknown skill: '{skill_name}'\n"
                f"Available skills: {', '.join(skill_registry.keys())}"
            )

        skill_metadata = skill_registry[skill_name]
        contract = skill_metadata.get("contract")

        if not contract:
            # Skill has no contract, skip validation
            logger.debug(f"Skill '{skill_name}' has no contract, skipping validation")
            continue

        # Validate step arguments against contract input schema
        step_args = step.get("args", {})
        try:
            contract.validate_input(step_args)
        except Exception as e:
            raise ValueError(
                f"Contract validation failed for step '{step.get('name', '?')}' "
                f"invoking skill '{skill_name}':\n{e}"
            )

    logger.info(
        f"✓ Workflow contract validation passed "
        f"({len(workflow_config.get('steps', []))} steps validated)"
    )
