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
from a2a_orchestrator.exceptions import WorkflowValidationError, BatchProcessingError
from a2a_orchestrator.message_cache import A2AMessageCache, A2AMessageBus
from a2a_orchestrator.batch_processor import BatchProcessor, BatchConfig
from a2a_orchestrator.execution_manifest import ExecutionManifestLogger


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
        # T023: Initialize batch processor and manifest logger
        self.batch_processor = None  # Created per workflow with config
        self.manifest_logger = None  # Created per workflow run
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

    def _detect_circular_dependencies(self, workflow_path: str, visited: set = None, rec_stack: list = None) -> None:
        """
        Detect circular dependencies in workflow composition using DFS.

        Args:
            workflow_path: Path to workflow file to check
            visited: Set of already visited workflow paths (prevents re-checking)
            rec_stack: Current recursion stack for cycle detection

        Raises:
            WorkflowValidationError: If circular dependency detected
        """
        if visited is None:
            visited = set()
        if rec_stack is None:
            rec_stack = []

        # Normalize path for comparison
        workflow_path = str(Path(workflow_path).resolve())

        # If already in recursion stack, we found a cycle
        if workflow_path in rec_stack:
            cycle_start = rec_stack.index(workflow_path)
            cycle_path = ' → '.join([Path(p).name for p in rec_stack[cycle_start:]] + [Path(workflow_path).name])
            raise WorkflowValidationError(
                skill_name="workflow_composition",
                step_index=-1,
                line_number=-1,
                message=f"Circular dependency detected: {cycle_path}"
            )

        # If already fully explored, skip
        if workflow_path in visited:
            return

        # Add to recursion stack
        rec_stack.append(workflow_path)

        # Load and check this workflow's dependencies
        try:
            workflow = self.load_workflow(workflow_path)
            steps = workflow.get("steps", [])

            for step in steps:
                if "workflow" in step:
                    # Resolve workflow path (support both absolute and relative)
                    sub_workflow_path = step["workflow"]
                    if not Path(sub_workflow_path).is_absolute():
                        # Resolve relative to current workflow's directory
                        current_dir = Path(workflow_path).parent
                        sub_workflow_path = str((current_dir / sub_workflow_path).resolve())

                    # Recurse into sub-workflow
                    self._detect_circular_dependencies(sub_workflow_path, visited, rec_stack)

        except FileNotFoundError:
            # Sub-workflow doesn't exist - will be caught by workflow execution
            pass

        # Remove from recursion stack and mark as visited
        rec_stack.pop()
        visited.add(workflow_path)

    def _validate_batch_config(self, batch_config: Dict[str, Any]) -> None:
        """
        Validate batch_config structure and values.

        Args:
            batch_config: Batch configuration dictionary

        Raises:
            WorkflowValidationError: If batch_config is invalid
        """
        if not batch_config:
            return

        # Validate batch_size
        batch_size = batch_config.get("batch_size", 10)
        if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 50:
            raise WorkflowValidationError(
                skill_name="batch_config",
                step_index=-1,
                line_number=-1,
                message=f"batch_size must be integer between 1-50, got: {batch_size}"
            )

        # Validate max_concurrent
        max_concurrent = batch_config.get("max_concurrent", 3)
        if not isinstance(max_concurrent, int) or max_concurrent < 1:
            raise WorkflowValidationError(
                skill_name="batch_config",
                step_index=-1,
                line_number=-1,
                message=f"max_concurrent must be positive integer, got: {max_concurrent}"
            )

        # Validate retry_strategy
        retry_strategy = batch_config.get("retry_strategy", "exponential_backoff")
        valid_strategies = ["exponential_backoff", "linear_backoff", "constant_backoff", "none"]
        if retry_strategy not in valid_strategies:
            raise WorkflowValidationError(
                skill_name="batch_config",
                step_index=-1,
                line_number=-1,
                message=f"retry_strategy must be one of {valid_strategies}, got: {retry_strategy}"
            )

        # Validate request_timeout_seconds
        timeout = batch_config.get("request_timeout_seconds", 30)
        if not isinstance(timeout, (int, float)) or timeout < 1:
            raise WorkflowValidationError(
                skill_name="batch_config",
                step_index=-1,
                line_number=-1,
                message=f"request_timeout_seconds must be positive number, got: {timeout}"
            )

        # Validate retry_policy if present
        retry_policy = batch_config.get("retry_policy", {})
        if retry_policy:
            max_retries = retry_policy.get("max_retries", 3)
            if not isinstance(max_retries, int) or max_retries < 0:
                raise WorkflowValidationError(
                    skill_name="batch_config.retry_policy",
                    step_index=-1,
                    line_number=-1,
                    message=f"retry_policy.max_retries must be non-negative integer, got: {max_retries}"
                )

            initial_delay = retry_policy.get("initial_delay_seconds", 1.0)
            max_delay = retry_policy.get("max_delay_seconds", 8.0)
            if initial_delay > max_delay:
                raise WorkflowValidationError(
                    skill_name="batch_config.retry_policy",
                    step_index=-1,
                    line_number=-1,
                    message=f"retry_policy.initial_delay_seconds ({initial_delay}) must be ≤ max_delay_seconds ({max_delay})"
                )

    def validate_workflow(self, workflow: Dict[str, Any], workflow_path: str = None) -> None:
        """
        Validate workflow structure before execution.

        Checks:
        - Steps have either 'skill' OR 'workflow' reference (mutual exclusivity)
        - All skill references exist in registered_skills
        - No circular dependencies in workflow composition (if workflow_path provided)
        - T014: Batch configuration is valid (if present)
        - Raises WorkflowValidationError with line numbers for invalid steps

        Args:
            workflow: Workflow dictionary with 'steps' key
            workflow_path: Optional path to workflow file (for circular dependency detection)

        Raises:
            WorkflowValidationError: If any step reference is invalid
        """
        # T013: Detect circular dependencies at load time
        if workflow_path:
            self._detect_circular_dependencies(workflow_path)

        # T014: Validate batch_config if present
        batch_config = workflow.get("batch_config")
        if batch_config:
            self._validate_batch_config(batch_config)

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

    def _extract_batch_items(self, step: Dict[str, Any], context: WorkflowContext) -> List[Any]:
        """
        Extract list of items to process in batch from step arguments.

        T023: Detects batch items from step args by looking for list-type inputs.

        Args:
            step: Workflow step configuration
            context: Workflow execution context

        Returns:
            List of items to process in batch

        Raises:
            BatchProcessingError: If no list inputs found or batch_mode used incorrectly
        """
        step_args = step.get("args", {})

        # Resolve variables in args first
        resolved_args = {}
        for key, value in step_args.items():
            resolved_value = context.substitute_variables(value)
            resolved_args[key] = resolved_value

        # Look for list-type inputs (common patterns: card_names, cards_data, items, etc.)
        batch_items = None
        for key, value in resolved_args.items():
            if isinstance(value, list) and len(value) > 0:
                batch_items = value
                break

        if batch_items is None:
            raise BatchProcessingError(
                f"Step '{step.get('name')}' has batch_mode=true but no list inputs found. "
                f"Expected list-type argument (e.g., card_names, cards_data)."
            )

        return batch_items

    async def _execute_skill_async(self, skill_name: str, payload: Dict[str, Any]) -> Any:
        """
        Execute skill asynchronously (wrapper for existing _execute_skill).

        T023: Wraps sync skill execution for batch processing compatibility.
        """
        # For now, delegate to existing _execute_skill
        # In future, this could be truly async skill execution
        return await asyncio.to_thread(lambda: {"status": "simulated", "skill": skill_name, "payload": payload})

    async def execute_workflow(self, workflow: Dict[str, Any], inputs: Dict[str, Any], workflow_path: str = None) -> Dict[str, Any]:
        """Execute a YAML workflow with given inputs"""
        # Pre-flight validation (fail-fast before any execution)
        # T013: Pass workflow_path for circular dependency detection
        self.validate_workflow(workflow, workflow_path=workflow_path)

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

        # T023 & T024: Initialize batch processing infrastructure
        batch_config_dict = workflow.get("batch_config", {})
        if batch_config_dict:
            try:
                batch_config = BatchConfig(**batch_config_dict)
                self.batch_processor = BatchProcessor(batch_config)
                print(f"🔄 Batch processing enabled (size={batch_config.batch_size}, concurrent={batch_config.max_concurrent})")
            except Exception as e:
                print(f"⚠️  Batch config invalid, using sequential execution: {e}")
                self.batch_processor = None
        else:
            self.batch_processor = None

        # T024: Create execution manifest logger
        workflow_name = workflow.get("name", "unnamed_workflow")
        manifest_dir = Path(".execution_manifests")
        manifest_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workflow_run_id = f"{workflow_name}_{timestamp}"
        manifest_path = manifest_dir / f"{workflow_run_id}.jsonl"
        self.manifest_logger = ExecutionManifestLogger(manifest_path, workflow_name, workflow_run_id)

        print(f"📋 Starting workflow: {workflow.get('name', 'unnamed')}")
        print(f"📝 Description: {workflow.get('description', '')}")
        print(f"📊 Manifest: {manifest_path}")
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

            # T023: Check for batch_mode flag
            batch_mode = step.get("batch_mode", False)
            mode_indicator = " [BATCH]" if batch_mode else ""
            print(f"⚙️  Step {step_idx}: {step_name} (skill: {skill_name}){mode_indicator}")

            # Check condition if present
            condition = step.get("condition")
            if condition:
                condition_result = self._evaluate_condition(condition, context)
                if not condition_result:
                    print(f"   ⏭️  Skipped (condition false)")
                    continue

            # T023: Route to batch processor if batch_mode enabled
            if batch_mode and self.batch_processor:
                try:
                    # Extract batch items from step args
                    batch_items = self._extract_batch_items(step, context)
                    print(f"   🔄 Processing {len(batch_items)} items in batches...")

                    # Create async executor for each batch item
                    async def process_item(item):
                        # Simulate skill execution with the item
                        # In full implementation, this would call the actual skill
                        return {"item": item, "status": "success", "skill": skill_name}

                    # Execute batches with BatchProcessor
                    batch_results = await self.batch_processor.process_batches(
                        items=batch_items,
                        processor_func=process_item,
                        manifest_logger=self.manifest_logger
                    )

                    # T025: Aggregate results (partial success handling is in BatchProcessor)
                    total_success = sum(r.success_count for r in batch_results)
                    total_failed = sum(r.failure_count for r in batch_results)
                    print(f"   ✅ Batch complete: {total_success} success, {total_failed} failed")

                    # Store aggregated results in context
                    response = {
                        "batch_results": batch_results,
                        "total": len(batch_items),
                        "successful": total_success,
                        "failed": total_failed
                    }

                except BatchProcessingError as e:
                    print(f"   ❌ Batch processing failed: {e}")
                    raise

            else:
                # Normal sequential execution (existing path)
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
    result = await orchestrator.execute_workflow(workflow, inputs, workflow_path=workflow_path)

    print("\n🎯 Workflow complete!")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
