---
name: example-anthropic
description: Demonstrates Anthropic skills format with YAML frontmatter. Use this when you need an example of the directory-based skill format with metadata.
version: 1.0.0
author: orchestrator-dev
tags: [example, documentation, anthropic-format]
---

# Example Anthropic Skill

This skill demonstrates the Anthropic skills format with:
- YAML frontmatter (name, description required)
- Markdown body (instructions for Claude or skill executor)
- Optional metadata fields (version, author, tags)

## How This Skill Works

When referenced in a YAML workflow, the orchestrator will:

1. Detect the directory format (`.claude/skills/example-anthropic/SKILL.md`)
2. Parse the YAML frontmatter to extract metadata
3. Load the markdown content as skill instructions
4. Execute the skill logic based on the workflow step configuration

## Example Usage

```yaml
steps:
  - skill: example-anthropic
    inputs:
      message: "Hello from workflow"
    output_var: example_result
```

## Supported Inputs

- `message` (string): A message to process

## Expected Outputs

- `status` (string): "success" or "error"
- `processed_message` (string): The processed message
- `skill_metadata` (object): Skill metadata from frontmatter

This is a demonstration skill showing the Anthropic format structure.
