---
name: example-with-script
description: Example Anthropic skill with Python executor in scripts/ subdirectory
version: 1.0.0
author: A2A Orchestrator Team
tags: [example, scripting, python]
---

# Example Skill with Script Execution

This skill demonstrates the Anthropic skills format with a Python executor script in the `scripts/` subdirectory.

## Purpose

Shows how to:
- Package executable Python scripts alongside skill definitions
- Pass workflow variables to script executors
- Maintain portability for skill sharing

## Usage

Reference this skill in a workflow YAML file:

```yaml
skills:
  - name: example-with-script
    variables:
      input_text: "Hello from workflow"
      output_file: "result.txt"
```

The skill will execute `scripts/process.py` with workflow variables injected as environment variables.

## Script Execution

The orchestrator automatically discovers and executes Python files in the `scripts/` subdirectory when this skill is invoked.
