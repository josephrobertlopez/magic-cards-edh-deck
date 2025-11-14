#!/usr/bin/env python3
"""
A2A Workflow Orchestrator

Loads YAML workflows and coordinates skill execution via A2A message passing.
"""

import os
import sys
import yaml
from ruamel.yaml import YAML
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from a2a_orchestrator.vendor.mcp_a2a_server import (
    A2AMessage,
    MessageType,
    Skill,
    WorkflowOrchestrator as BaseOrchestrator
)
from a2a_orchestrator.skills import (
    DataFetcherSkill,
    DocumentGeneratorSkill,
    FormatTransformerSkill,
    WebFetcherSkill,
    HTMLExtractorSkill
)
from a2a_orchestrator.exceptions import WorkflowValidationError
from a2a_orchestrator.message_cache import A2AMessageCache, A2AMessageBus


class WorkflowContext:
    """Manages workflow execution context and variable substitution"""

    def __init__(self, workflow_inputs: Dict[str, Any]):
        # Support both 'input' and 'inputs' for backward compatibility
        self.variables = {
            "input": workflow_inputs,
            "inputs": workflow_inputs  # Alias for common YAML pattern
        }
        self.message_log = []
        self.call_stack = []  # T017: Track workflow nesting for composition

    def substitute_variables(self, value: Any) -> Any:
        """Recursively substitute ${var} or {{var}} references in values"""
        if isinstance(value, str):
            # Handle both ${var.path} and {{var.path}} syntax
            import re
            # Match both ${...} and {{...}} patterns
            pattern = r'(\$\{([^}]+)\}|\{\{([^}]+)\}\})'

            def replacer(match):
                # Group 2 is ${} syntax, group 3 is {{}} syntax
                var_path = match.group(2) if match.group(2) else match.group(3)
                resolved = self._resolve_path(var_path)
                return str(resolved) if resolved is not None else match.group(0)

            return re.sub(pattern, replacer, value)
        elif isinstance(value, dict):
            return {k: self.substitute_variables(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.substitute_variables(item) for item in value]
        else:
            return value

    def _resolve_path(self, path: str) -> Any:
        """Resolve dot-notation path like 'manifest_path' or 'input.decklist_path'"""
        parts = path.split(".")
        current = self.variables

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def set_variable(self, name: str, value: Any):
        """Set a workflow variable, supporting dot-notation paths"""
        if "." in name:
            # Create nested dict structure for paths like "steps.fetch_cards.outputs.manifest_path"
            parts = name.split(".")
            current = self.variables
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            # Simple variable name
            self.variables[name] = value

    def log_message(self, message: A2AMessage):
        """Log A2A message to context"""
        self.message_log.append({
            "message_id": message.message_id,
            "message_type": message.message_type.value,
            "sender": message.sender_skill,
            "recipient": message.recipient_skill,
            "payload": message.payload,
            "timestamp": datetime.now().isoformat()
        })


class YAMLWorkflowOrchestrator:
    """Orchestrates YAML-defined workflows via A2A skills"""

    def __init__(self, skills_dir: Path, enable_cache: bool = True):
        self.skills_dir = skills_dir
        self.base_orchestrator = BaseOrchestrator()
        self.registered_skills = {}
        self.message_counter = 0
        self.enable_cache = enable_cache
        self.message_cache = A2AMessageCache() if enable_cache else None
        self.message_bus = A2AMessageBus()
        self._register_builtin_skills()

    def generate_message_id(self) -> str:
        """Generate unique message ID"""
        self.message_counter += 1
        return f"msg_{self.message_counter}"

    def _register_builtin_skills(self):
        """Register built-in skill instances"""
        self.registered_skills["data/fetch-from-api"] = DataFetcherSkill("data/fetch-from-api")
        self.registered_skills["presentation/place-images-in-pptx"] = DocumentGeneratorSkill("presentation/place-images-in-pptx")
        self.registered_skills["pdf/convert-to-pdf"] = FormatTransformerSkill("pdf/convert-to-pdf")
        self.registered_skills["data/fetch-web-page"] = WebFetcherSkill("data/fetch-web-page")
        self.registered_skills["data/extract-cards-from-html"] = HTMLExtractorSkill("data/extract-cards-from-html")

    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        Load YAML workflow file with line number tracking.

        Uses ruamel.yaml to preserve line number metadata for error reporting.
        """
        ryaml = YAML()
        with open(workflow_path, 'r') as f:
            return ryaml.load(f)

    def validate_workflow(self, workflow: Dict[str, Any]) -> None:
        """
        Validate workflow structure before execution.

        Checks:
        - Steps have either 'skill' OR 'workflow' reference (mutual exclusivity)
        - All skill references exist in registered_skills
        - Raises WorkflowValidationError with line numbers for invalid steps

        Args:
            workflow: Workflow dictionary with 'steps' key

        Raises:
            WorkflowValidationError: If any step reference is invalid
        """
        steps = workflow.get("steps", [])

        for step_idx, step in enumerate(steps, 1):
            step_name = step.get("name", f"step-{step_idx}")
            has_skill = "skill" in step
            has_workflow = "workflow" in step

            # T013: Check mutual exclusivity (skill OR workflow, not both)
            if has_skill and has_workflow:
                raise WorkflowValidationError(
                    skill_name=step_name,
                    step_index=step_idx,
                    line_number=-1,
                    message=f"Step '{step_name}' cannot have both 'skill' and 'workflow' references"
                )

            if not has_skill and not has_workflow:
                raise WorkflowValidationError(
                    skill_name=step_name,
                    step_index=step_idx,
                    line_number=-1,
                    message=f"Step '{step_name}' must have either 'skill' or 'workflow' reference"
                )

            # Validate skill registration (if skill reference)
            if has_skill:
                skill_name = step["skill"]
                if skill_name not in self.registered_skills:
                    # Extract line number from ruamel.yaml metadata if available
                    line_number = getattr(step, "lc", None)
                    if line_number:
                        line_num = line_number.line + 1  # Convert 0-based to 1-based
                    else:
                        line_num = -1  # Unknown line number

                    raise WorkflowValidationError(
                        skill_name=skill_name,
                        step_index=step_idx,
                        line_number=line_num
                    )

            # Workflow path validation is deferred to WorkflowSkill lazy load
            # (allows relative paths to be resolved at execution time)

    def register_skill_from_markdown(self, skill_path: str) -> str:
        """Register a skill from its markdown definition"""
        # For now, return skill path as identifier
        # In full implementation, would parse markdown and create Skill instance
        skill_name = Path(skill_path).stem
        return skill_name

    async def execute_workflow(self, workflow: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a YAML workflow with given inputs"""
        # Pre-flight validation (fail-fast before any execution)
        self.validate_workflow(workflow)

        # Merge input defaults from workflow definition with provided inputs
        input_schema = workflow.get("inputs", {})
        merged_inputs = {}
        for input_name, input_spec in input_schema.items():
            if input_name in inputs:
                merged_inputs[input_name] = inputs[input_name]
            elif "default" in input_spec:
                merged_inputs[input_name] = input_spec["default"]
            elif input_spec.get("required", False):
                raise ValueError(f"Required input '{input_name}' not provided")
        # Also include any extra inputs not in schema
        for key, value in inputs.items():
            if key not in merged_inputs:
                merged_inputs[key] = value

        context = WorkflowContext(merged_inputs)

        print(f"📋 Starting workflow: {workflow.get('name', 'unnamed')}")
        print(f"📝 Description: {workflow.get('description', '')}")
        print()

        # Execute steps in order
        for step_idx, step in enumerate(workflow.get("steps", []), 1):
            step_name = step.get("name", f"step-{step_idx}")

            # T014: Detect workflow: reference in steps
            if "workflow" in step:
                workflow_path = step["workflow"]
                print(f"⚙️  Step {step_idx}: {step_name} (workflow: {workflow_path})")

                # T015: Instantiate WorkflowSkill when workflow: found
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent))
                from workflow_skill import WorkflowSkill
                workflow_skill = WorkflowSkill(workflow_path, orchestrator=self)

                # Substitute variables in input (support both 'input' and 'args' field names)
                step_input = context.substitute_variables(step.get("input") or step.get("args", {}))
                print(f"   📤 Passing inputs to sub-workflow: {step_input}")

                # T016: Pass call_stack in context when calling WorkflowSkill
                response = await workflow_skill.execute({
                    "inputs": step_input,
                    "context": {
                        "call_stack": getattr(context, "call_stack", []),
                        "workflow": workflow.get("name"),
                        "step": step_name
                    }
                })

                # Store output variables (support both output_var and outputs)
                # Handle single output_var (legacy)
                output_var = step.get("output_var")
                if output_var and response:
                    context.set_variable(output_var, response.get("result"))
                    print(f"   ✅ Output: {output_var} = {response.get('result')}")

                # Handle multiple outputs (modern pattern)
                outputs_spec = step.get("outputs", {})
                if outputs_spec and response:
                    # Temporarily add 'result' to context for output expressions
                    context.set_variable("result", response.get("result"))
                    # Store the full result so {{result.field}} references work
                    context.set_variable(f"steps.{step_name}.result", response.get("result"))
                    # Also evaluate and store each named output
                    for output_name, output_expr in outputs_spec.items():
                        # Substitute variables in the expression (e.g., "{{result.manifest_file}}")
                        output_value = context.substitute_variables(output_expr)
                        context.set_variable(f"steps.{step_name}.outputs.{output_name}", output_value)
                        print(f"   ✅ Output: steps.{step_name}.outputs.{output_name} = {output_value}")

                print()
                continue

            # Existing skill execution path
            skill_name = step["skill"]
            print(f"⚙️  Step {step_idx}: {step_name} (skill: {skill_name})")

            # Check condition if present
            condition = step.get("condition")
            if condition:
                condition_result = self._evaluate_condition(condition, context)
                if not condition_result:
                    print(f"   ⏭️  Skipped (condition false)")
                    continue

            # Substitute variables in input (support both 'input' and 'args' field names)
            step_input = context.substitute_variables(step.get("input") or step.get("args", {}))
            print(f"   📤 Passing payload to skill: {step_input}")

            # Create A2A message
            message = A2AMessage(
                message_id=self.generate_message_id(),
                message_type=MessageType.REQUEST,
                sender_skill="orchestrator",
                recipient_skill=skill_name,
                payload=step_input,
                context={"workflow": workflow.get("name"), "step": step_name}
            )

            context.log_message(message)

            # Execute skill (for now, simulate)
            response = await self._execute_skill(skill_name, message, context)

            # Store output variables (support both output_var and outputs)
            # Handle single output_var (legacy)
            output_var = step.get("output_var")
            if output_var and response:
                context.set_variable(output_var, response)
                print(f"   ✅ Output: {output_var} = {response}")

            # Handle multiple outputs (modern pattern)
            outputs_spec = step.get("outputs", {})
            if outputs_spec and response:
                # Temporarily add 'result' to context for output expressions
                context.set_variable("result", response)
                # Store the full result so {{result.field}} references work
                context.set_variable(f"steps.{step_name}.result", response)
                # Also evaluate and store each named output
                for output_name, output_expr in outputs_spec.items():
                    # Substitute variables in the expression
                    output_value = context.substitute_variables(output_expr)
                    context.set_variable(f"steps.{step_name}.outputs.{output_name}", output_value)
                    print(f"   ✅ Output: steps.{step_name}.outputs.{output_name} = {output_value}")

            print()

        # Save message log
        self._save_message_log(workflow.get("name", "unnamed"), context)

        # Return output variables (support both 'output' and 'outputs')
        output_spec = workflow.get("outputs") or workflow.get("output", {})
        result = context.substitute_variables(output_spec)
        print(f"🔙 Workflow result: {result}")
        return result

    async def _execute_skill(self, skill_name: str, message: A2AMessage, context: WorkflowContext) -> Any:
        """Execute a skill via subprocess invocation (with caching)"""
        # Check cache first (if enabled)
        if self.enable_cache and self.message_cache:
            cached_result = self.message_cache.get(skill_name, message.payload)
            if cached_result is not None:
                print(f"   💾 Cache HIT for {skill_name}")
                # Publish cache hit event to message bus
                await self.message_bus.publish("skill.cache_hit", {
                    "skill": skill_name,
                    "message_id": message.message_id
                })
                return cached_result

        # Look up skill in registry
        skill = self.registered_skills.get(skill_name)

        if not skill:
            print(f"   ❌ Skill not found: {skill_name}")
            error_msg = A2AMessage(
                message_id=self.generate_message_id(),
                message_type=MessageType.ERROR,
                sender_skill="orchestrator",
                recipient_skill="orchestrator",
                payload={"error": f"Skill not found: {skill_name}"},
                context={"workflow_message_id": message.message_id}
            )
            context.log_message(error_msg)
            return None

        print(f"   🔄 Executing {skill_name}...")

        # Publish skill execution event
        await self.message_bus.publish("skill.executing", {
            "skill": skill_name,
            "message_id": message.message_id,
            "payload": message.payload
        })

        # Invoke skill asynchronously (skills have async process_request methods)
        response_coro = skill.process_request(message)

        # Defensive check: ensure we got a coroutine (expected for async methods)
        if not asyncio.iscoroutine(response_coro):
            error_msg = A2AMessage(
                message_id=self.generate_message_id(),
                message_type=MessageType.ERROR,
                sender_skill="orchestrator",
                recipient_skill="orchestrator",
                payload={"error": f"Skill {skill_name} process_request did not return coroutine (not async?)"},
                context={"workflow_message_id": message.message_id}
            )
            context.log_message(error_msg)
            return None

        # Await coroutine to get actual response message
        response_message = await response_coro

        # Log response (safe to access attributes after await)
        context.log_message(response_message)

        # Handle ERROR messages
        if response_message.message_type == MessageType.ERROR:
            print(f"   ❌ Skill error: {response_message.payload.get('error', 'Unknown error')}")
            # Publish error event
            await self.message_bus.publish("skill.error", {
                "skill": skill_name,
                "message_id": message.message_id,
                "error": response_message.payload.get('error')
            })
            return None

        # Extract result from RESPONSE payload
        result = response_message.payload

        # Cache successful result (if enabled)
        if self.enable_cache and self.message_cache:
            # Default TTL: 1 hour for most skills, 10 min for data fetching (might change)
            ttl = 600 if "fetch" in skill_name else 3600
            self.message_cache.put(skill_name, message.payload, result, ttl_seconds=ttl)

        # Publish success event
        await self.message_bus.publish("skill.complete", {
            "skill": skill_name,
            "message_id": message.message_id
        })

        return result

    def _resolve_skill_path(self, skill_name: str) -> Optional[Path]:
        """Resolve skill name to markdown file path"""
        # Handle slash notation: data/fetch-from-api → data/fetch-from-api.md
        skill_md = self.skills_dir / f"{skill_name}.md"
        return skill_md if skill_md.exists() else None


    def _evaluate_condition(self, condition: str, context: WorkflowContext) -> bool:
        """Evaluate a condition string like '${input.no_pdf} == false'"""
        # Simple evaluation - in production would use safer eval
        try:
            # Substitute variables
            evaluated = context.substitute_variables(condition)
            # For simple boolean checks
            if "==" in str(evaluated):
                left, right = str(evaluated).split("==")
                left = left.strip().lower()
                right = right.strip().lower()
                return left == right
            return bool(evaluated)
        except:
            return False

    def _save_message_log(self, workflow_name: str, context: WorkflowContext):
        """Save message log to state directory"""
        state_dir = Path(".claude/state")
        state_dir.mkdir(parents=True, exist_ok=True)

        log_path = state_dir / f"{workflow_name}_messages.json"
        with open(log_path, 'w') as f:
            json.dump(context.message_log, f, indent=2)

        print(f"💾 Message log saved: {log_path}")


def load_yaml_workflow(workflow_path: str) -> Dict[str, Any]:
    """Load YAML workflow file with line number tracking"""
    ryaml = YAML()
    with open(workflow_path, 'r') as f:
        return ryaml.load(f)


async def execute_workflow(workflow: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a workflow with given inputs"""
    skills_dir = Path(__file__).parent.parent / ".claude" / "skills"
    orchestrator = YAMLWorkflowOrchestrator(skills_dir)
    return await orchestrator.execute_workflow(workflow, inputs)


async def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <workflow.yaml> [input_key=value ...]")
        sys.exit(1)

    workflow_path = sys.argv[1]

    # Parse input arguments (key=value format)
    inputs = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            # Convert string booleans
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            inputs[key] = value

    # Load workflow
    workflow = load_yaml_workflow(workflow_path)

    # Execute
    orchestrator = YAMLWorkflowOrchestrator(Path(".claude/skills"))
    result = await orchestrator.execute_workflow(workflow, inputs)

    print("\n🎯 Workflow complete!")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
