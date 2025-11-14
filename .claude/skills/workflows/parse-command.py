#!/usr/bin/env python3
"""
Parse Command Skill: Natural language command → A2A workflow YAML

Converts natural language commands into executable A2A workflow definitions.
Detects intent, maps to skills, generates valid workflow YAML.

Use cases:
- "Fetch MTG cards from frog deck and convert to PDF"
  → workflow: fetch-from-api → place-images-in-pptx → convert-to-pdf

- "Get Pokemon sprites for pikachu, then analyze the results"
  → workflow: fetch-from-api (Pokemon API) → analyze-manifest

- "Search for card dimensions, then fetch cards at optimal size"
  → workflow: search-oracle → fetch-from-api (with size hints)

This is a **meta-skill**: It doesn't do work itself, it GENERATES workflows that do work.
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from a2a_orchestrator.utils.json_io import format_success_output, format_error_output
from a2a_orchestrator.constants import SUCCESS, NOT_FOUND


# ===== SKILL REGISTRY =====

SKILL_REGISTRY = {
    "data/fetch-from-api": {
        "description": "Fetch resources from API (cards, images, data)",
        "inputs": ["decklist_path", "api_url", "schema_json", "output_dir"],
        "outputs": ["manifest_path", "status"],
        "keywords": ["fetch", "get", "download", "retrieve", "pull", "cards", "images", "data", "api"]
    },
    "data/probe-api-schema": {
        "description": "Auto-discover API response schema",
        "inputs": ["api_url", "sample_id"],
        "outputs": ["schema"],
        "keywords": ["probe", "discover", "analyze", "schema", "api", "structure"]
    },
    "data/search-oracle": {
        "description": "Search for factual information (dimensions, DPI, sizes)",
        "inputs": ["query", "num_results"],
        "outputs": ["facts", "confidence"],
        "keywords": ["search", "find", "query", "oracle", "dimensions", "size", "dpi", "facts"]
    },
    "presentation/place-images-in-pptx": {
        "description": "Place images into PowerPoint template slots",
        "inputs": ["manifest_path", "template_path", "output_path"],
        "outputs": ["output_path"],
        "keywords": ["place", "insert", "arrange", "powerpoint", "pptx", "slides", "template", "generate", "create"]
    },
    "pdf/convert-to-pdf": {
        "description": "Convert PowerPoint to PDF for printing",
        "inputs": ["pptx_path", "output_path"],
        "outputs": ["pdf_path"],
        "keywords": ["convert", "pdf", "print", "export", "transform"]
    }
}


# ===== INTENT DETECTION =====

def detect_intents(command: str) -> List[str]:
    """
    Detect user intents from natural language command.

    Args:
        command: Natural language command string

    Returns:
        List of detected intent strings
    """
    command_lower = command.lower()
    intents = []

    # Fetch intent
    if any(kw in command_lower for kw in ["fetch", "get", "download", "retrieve", "pull"]):
        intents.append("fetch")

    # Generate/create intent
    if any(kw in command_lower for kw in ["generate", "create", "make", "build", "arrange"]):
        intents.append("generate")

    # Convert intent
    if any(kw in command_lower for kw in ["convert", "transform", "export"]) or "pdf" in command_lower:
        intents.append("convert_pdf")

    # Search intent
    if any(kw in command_lower for kw in ["search", "find", "query", "lookup"]):
        intents.append("search")

    # Probe/analyze intent
    if any(kw in command_lower for kw in ["probe", "analyze", "discover", "inspect"]):
        intents.append("probe")

    return intents


def extract_parameters(command: str) -> Dict[str, Any]:
    """
    Extract parameters from natural language command.

    Args:
        command: Natural language command string

    Returns:
        Dict of extracted parameters
    """
    params = {}

    # Extract file paths (words ending in .txt, .yaml, .pptx, etc.)
    file_patterns = [
        (r'([a-zA-Z0-9_/-]+\.txt)', 'decklist_path'),
        (r'([a-zA-Z0-9_/-]+\.pptx)', 'template_path'),
        (r'([a-zA-Z0-9_/-]+\.pdf)', 'output_pdf_path'),
        (r'([a-zA-Z0-9_/-]+\.yaml)', 'workflow_path'),
    ]

    for pattern, param_name in file_patterns:
        match = re.search(pattern, command)
        if match:
            params[param_name] = match.group(1)

    # Extract quoted strings (likely queries or names)
    quoted = re.findall(r'"([^"]+)"', command)
    if quoted:
        params['query'] = quoted[0]

    # Extract API hints
    if 'pokemon' in command.lower():
        params['api_hint'] = 'pokemon'
    elif 'mtg' in command.lower() or 'magic' in command.lower() or 'card' in command.lower():
        params['api_hint'] = 'mtg'

    # Extract output directory hints
    if 'output' in command.lower():
        output_match = re.search(r'output[:\s]+([a-zA-Z0-9_/-]+)', command, re.IGNORECASE)
        if output_match:
            params['output_dir'] = output_match.group(1)

    # Extract DPI hints
    dpi_match = re.search(r'(\d+)\s*dpi', command.lower())
    if dpi_match:
        params['dpi'] = int(dpi_match.group(1))

    # Extract size hints
    size_match = re.search(r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*(?:inches|in)', command.lower())
    if size_match:
        params['size_width'] = float(size_match.group(1))
        params['size_height'] = float(size_match.group(2))

    return params


def generate_workflow(intents: List[str], params: Dict[str, Any], command: str) -> Dict[str, Any]:
    """
    Generate A2A workflow YAML structure from intents and parameters.

    Args:
        intents: List of detected intents
        params: Extracted parameters
        command: Original command for context

    Returns:
        Workflow dict (to be serialized as YAML)
    """
    workflow = {
        "name": "auto-generated-workflow",
        "description": f"Auto-generated from command: {command}",
        "steps": []
    }

    step_counter = 1
    previous_output = None

    # === BUILD WORKFLOW STEPS ===

    # Search oracle step (if search intent)
    if "search" in intents:
        query = params.get('query', 'standard card dimensions')
        workflow["steps"].append({
            "name": f"step{step_counter}-search-oracle",
            "skill": "data/search-oracle",
            "input": {
                "query": query,
                "num_results": 5
            },
            "output_var": "oracle_facts"
        })
        previous_output = "oracle_facts"
        step_counter += 1

    # Probe API step (if probe intent)
    if "probe" in intents:
        api_url = params.get('api_url', 'https://api.scryfall.com/cards/named?fuzzy={identifier}')
        sample_id = params.get('sample_id', 'Forest')

        workflow["steps"].append({
            "name": f"step{step_counter}-probe-api",
            "skill": "data/probe-api-schema",
            "input": {
                "api_url": api_url,
                "sample_id": sample_id
            },
            "output_var": "api_schema"
        })
        previous_output = "api_schema"
        step_counter += 1

    # Fetch step (if fetch intent)
    if "fetch" in intents:
        decklist_path = params.get('decklist_path', '${input.decklist_path}')
        output_dir = params.get('output_dir', 'images')

        fetch_input = {
            "decklist_path": decklist_path,
            "output_dir": output_dir
        }

        # Use API hint to set defaults
        if params.get('api_hint') == 'pokemon':
            fetch_input['api_url'] = 'https://pokeapi.co/api/v2/pokemon/{identifier}'
            fetch_input['schema_json'] = 'pokeapi'
        # If search was done, use size hints
        elif previous_output == "oracle_facts":
            fetch_input['size_hints'] = '${oracle_facts.facts}'

        workflow["steps"].append({
            "name": f"step{step_counter}-fetch-resources",
            "skill": "data/fetch-from-api",
            "input": fetch_input,
            "output_var": "fetch_manifest"
        })
        previous_output = "fetch_manifest"
        step_counter += 1

    # Generate presentation step (if generate intent)
    if "generate" in intents:
        template_path = params.get('template_path', '${input.template_path}')

        # Determine manifest source
        if previous_output == "fetch_manifest":
            manifest_path = "${fetch_manifest.manifest_path}"
        else:
            manifest_path = "${input.manifest_path}"

        workflow["steps"].append({
            "name": f"step{step_counter}-generate-presentation",
            "skill": "presentation/place-images-in-pptx",
            "input": {
                "manifest_path": manifest_path,
                "template_path": template_path,
                "output_path": "output.pptx"
            },
            "output_var": "pptx_output"
        })
        previous_output = "pptx_output"
        step_counter += 1

    # Convert to PDF step (if convert intent)
    if "convert_pdf" in intents:
        # Determine PPTX source
        if previous_output == "pptx_output":
            pptx_path = "${pptx_output.output_path}"
        else:
            pptx_path = params.get('template_path', '${input.pptx_path}')

        output_pdf = params.get('output_pdf_path', 'output.pdf')

        workflow["steps"].append({
            "name": f"step{step_counter}-convert-to-pdf",
            "skill": "pdf/convert-to-pdf",
            "input": {
                "pptx_path": pptx_path,
                "output_path": output_pdf
            },
            "output_var": "pdf_output"
        })
        previous_output = "pdf_output"
        step_counter += 1

    # Set workflow output
    if previous_output:
        workflow["output"] = {
            "status": "success",
            "result": f"${{{previous_output}}}"
        }

    return workflow


def parse_command_to_workflow(command: str) -> Dict[str, Any]:
    """
    Parse natural language command to A2A workflow definition.

    Args:
        command: Natural language command

    Returns:
        Workflow dict ready for YAML serialization
    """
    print(f"📝 Parsing command: '{command}'", file=sys.stderr)

    # Detect intents
    intents = detect_intents(command)
    print(f"🎯 Detected intents: {intents}", file=sys.stderr)

    if not intents:
        return {
            "error": "No intents detected",
            "command": command,
            "hint": "Try commands like: 'fetch cards from deck.txt', 'search for card dimensions', 'convert ppt to pdf'"
        }

    # Extract parameters
    params = extract_parameters(command)
    print(f"📊 Extracted params: {params}", file=sys.stderr)

    # Generate workflow
    workflow = generate_workflow(intents, params, command)

    print(f"✅ Generated workflow with {len(workflow['steps'])} steps", file=sys.stderr)

    return workflow


def main():
    """CLI entry point for parse-command skill."""
    parser = argparse.ArgumentParser(
        description='Parse natural language command to A2A workflow YAML'
    )
    parser.add_argument(
        '--command',
        required=True,
        help='Natural language command (e.g., "fetch cards from deck.txt and convert to PDF")'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output YAML file for generated workflow (default: stdout as JSON)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'yaml'],
        default='yaml',
        help='Output format (default: yaml)'
    )

    args = parser.parse_args()

    try:
        # Parse command
        workflow = parse_command_to_workflow(args.command)

        # Check for errors
        if "error" in workflow:
            format_error_output(
                workflow["error"],
                exit_code=NOT_FOUND,
                context={"command": args.command, "hint": workflow.get("hint")}
            )
            return

        # Output to file if requested
        if args.output:
            if args.format == 'yaml':
                # Use ruamel.yaml for nice formatting
                try:
                    from ruamel.yaml import YAML
                    yaml = YAML()
                    yaml.default_flow_style = False
                    with open(args.output, 'w') as f:
                        yaml.dump(workflow, f)
                except ImportError:
                    # Fallback to PyYAML
                    import yaml
                    with open(args.output, 'w') as f:
                        yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)

                print(f"\n💾 Workflow saved to: {args.output}", file=sys.stderr)
            else:
                with open(args.output, 'w') as f:
                    json.dump(workflow, f, indent=2)
                print(f"\n💾 Workflow (JSON) saved to: {args.output}", file=sys.stderr)

        # Print workflow preview to stderr
        print("\n" + "=" * 70, file=sys.stderr)
        print("🔄 GENERATED WORKFLOW", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n📋 Name: {workflow['name']}", file=sys.stderr)
        print(f"📝 Description: {workflow['description']}", file=sys.stderr)
        print(f"\n🔗 Steps ({len(workflow['steps'])}):", file=sys.stderr)
        for i, step in enumerate(workflow['steps'], 1):
            print(f"   {i}. {step['name']}: {step['skill']}", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        # Output to stdout for skill chaining
        format_success_output(workflow)

    except Exception as e:
        format_error_output(
            f"Command parsing failed: {str(e)}",
            exit_code=NOT_FOUND,
            context={"command": args.command, "exception": str(e)}
        )


if __name__ == '__main__':
    main()
