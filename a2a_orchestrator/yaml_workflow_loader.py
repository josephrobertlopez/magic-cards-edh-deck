"""
YAML Workflow Loader - Following monorepo patterns

Loads declarative YAML workflows and converts them to executable Workflow objects
with A2A protocol message passing. Supports:
- Variable substitution (${input.foo}, ${var_name})
- Conditional execution (condition: ${input.flag} == true)
- Output variable mapping
- Session tracking
"""

import yaml
import re
from pathlib import Path
from typing import Any, Dict, Optional
import sys

# Add vendor to path
sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
from mcp_a2a_server import Workflow, WorkflowOrchestrator


class VariableResolver:
    """Resolves variable references in YAML workflow definitions"""

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def resolve(self, value: Any) -> Any:
        """Recursively resolve variables in value"""
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        else:
            return value

    def _resolve_string(self, text: str) -> Any:
        """Resolve ${variable} references in string"""
        # Pattern: ${path.to.var}
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            var_path = match.group(1)
            return str(self._get_nested_value(var_path))

        # Check if entire string is a single variable reference
        if text.strip().startswith('${') and text.strip().endswith('}'):
            var_path = text.strip()[2:-1]
            return self._get_nested_value(var_path)

        # Otherwise do string substitution
        return re.sub(pattern, replacer, text)

    def _get_nested_value(self, path: str) -> Any:
        """Get value from nested path (e.g., 'input.foo' or 'result.data.manifest_path')"""
        parts = path.split('.')
        value = self.context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, f"${{{path}}}")  # Return unresolved if not found
            else:
                return f"${{{path}}}"  # Can't navigate further

        return value


def load_yaml_workflow(workflow_path: str) -> Workflow:
    """
    Load workflow from YAML file following monorepo patterns

    YAML Structure:
    ```yaml
    name: workflow-name
    description: Workflow description

    inputs:
      param1:
        type: string
        required: true
        description: Parameter description

    steps:
      - name: step-name
        skill: skill/path
        input:
          arg1: ${input.param1}
          arg2: value
        output_var: result_var
        condition: ${input.flag} == false

    output:
      final_result: ${result_var.data}
    ```

    Args:
        workflow_path: Path to YAML workflow file

    Returns:
        Workflow object ready for execution

    Raises:
        FileNotFoundError: If workflow file doesn't exist
        ValueError: If YAML structure is invalid
    """
    workflow_file = Path(workflow_path)
    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    with open(workflow_file) as f:
        workflow_def = yaml.safe_load(f)

    # Validate required fields
    if 'name' not in workflow_def:
        raise ValueError(f"Workflow missing 'name' field: {workflow_path}")
    if 'steps' not in workflow_def or not workflow_def['steps']:
        raise ValueError(f"Workflow missing 'steps' field: {workflow_path}")

    # Create workflow
    workflow = Workflow(
        name=workflow_def['name'],
        description=workflow_def.get('description', '')
    )

    # Add steps
    for step_def in workflow_def['steps']:
        if 'skill' not in step_def:
            raise ValueError(f"Step missing 'skill' field: {step_def.get('name', 'unnamed')}")

        # Build input mapping (convert YAML input dict to skill payload)
        input_mapping = None
        if 'input' in step_def:
            # Store as-is; will be resolved at execution time
            input_mapping = step_def['input']

        # Build output mapping
        output_mapping = None
        if 'output_var' in step_def:
            # Map skill result to output variable
            output_mapping = {step_def['output_var']: 'result'}

        # Build condition lambda
        condition = None
        if 'condition' in step_def:
            condition_expr = step_def['condition']
            # Create lambda that evaluates condition string
            # Note: Simplified - real impl would parse safely
            condition = lambda ctx: eval_condition(condition_expr, ctx)

        workflow.add_step(
            skill_name=step_def['skill'],
            input_mapping=input_mapping,
            output_mapping=output_mapping,
            condition=condition
        )

    # Store workflow definition for later use
    workflow._yaml_def = workflow_def

    return workflow


def eval_condition(condition_expr: str, context: Dict[str, Any]) -> bool:
    """
    Safely evaluate condition expression

    Supports:
    - ${var} == value
    - ${var} != value
    - ${var} == true/false

    Args:
        condition_expr: Condition string (e.g., "${input.no_pdf} == false")
        context: Variable context for resolution

    Returns:
        Boolean result of condition
    """
    # Resolve variables first
    resolver = VariableResolver(context)
    resolved = resolver.resolve(condition_expr)

    # Simple evaluation (real impl would use safe parser)
    try:
        # Check for boolean comparisons
        if ' == true' in resolved or ' == false' in resolved:
            resolved = resolved.replace(' == true', ' == True').replace(' == false', ' == False')

        # Very basic eval (UNSAFE in production - use ast.literal_eval or proper parser)
        # For demo purposes only
        return eval(resolved)
    except:
        # Default to True if condition can't be evaluated
        return True


async def execute_yaml_workflow(
    orchestrator: WorkflowOrchestrator,
    workflow: Workflow,
    inputs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute YAML workflow with variable resolution

    Args:
        orchestrator: WorkflowOrchestrator instance
        workflow: Loaded workflow
        inputs: Input parameters

    Returns:
        Dict with workflow results and outputs
    """
    # Build execution context
    context = {
        "input": inputs,
        "workflow_input": inputs,
        "workflow_name": workflow.name
    }

    # Execute workflow
    result_message = await workflow.execute(orchestrator, inputs)

    # Resolve output mapping if defined in YAML
    outputs = {}
    if hasattr(workflow, '_yaml_def') and 'output' in workflow._yaml_def:
        output_def = workflow._yaml_def['output']
        resolver = VariableResolver(context)

        for output_key, output_expr in output_def.items():
            outputs[output_key] = resolver.resolve(output_expr)

    return {
        "success": result_message.message_type.value != "error",
        "result": result_message.payload.get("result", {}),
        "outputs": outputs,
        "message_history": [msg.to_dict() for msg in orchestrator.message_history[-20:]]
    }


# Convenience function for loading all workflows from directory
def load_workflows_from_directory(workflows_dir: str) -> Dict[str, Workflow]:
    """
    Load all YAML workflows from directory

    Args:
        workflows_dir: Path to workflows directory

    Returns:
        Dict mapping workflow names to Workflow objects
    """
    workflows_path = Path(workflows_dir)
    if not workflows_path.exists():
        raise FileNotFoundError(f"Workflows directory not found: {workflows_dir}")

    workflows = {}

    for yaml_file in workflows_path.glob("*.yaml"):
        try:
            workflow = load_yaml_workflow(str(yaml_file))
            workflows[workflow.name] = workflow
        except Exception as e:
            print(f"Warning: Failed to load workflow {yaml_file.name}: {e}")

    for yml_file in workflows_path.glob("*.yml"):
        try:
            workflow = load_yaml_workflow(str(yml_file))
            workflows[workflow.name] = workflow
        except Exception as e:
            print(f"Warning: Failed to load workflow {yml_file.name}: {e}")

    return workflows
