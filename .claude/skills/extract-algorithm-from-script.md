# extract-algorithm-from-script

Extract reusable functions from Python scripts for consolidation into modules or skills.

## Usage

```
/extract-algorithm-from-script <script.py> [--function function_name]
```

**Parameters**:
- `script.py`: Python script to analyze (required)
- `--function`: Specific function to extract (optional, extracts all if omitted)

**Output**:
- Analysis of extractable functions
- Dependencies (imports, helper functions)
- Suggestions for consolidation into modules or skills

**Examples**:
```
/extract-algorithm-from-script analyze_templates.py
/extract-algorithm-from-script old_script.py --function download_card
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import ast
from pathlib import Path
from collections import defaultdict

def extract_functions(script_path, target_function=None):
    """
    Extract function definitions from Python script using AST.

    Args:
        script_path: Path to Python script
        target_function: Optional specific function name to extract

    Returns:
        Dictionary with extraction analysis
    """
    script_path = Path(script_path).resolve()

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    if not script_path.suffix == '.py':
        raise ValueError(f"File must be Python script (.py), got: {script_path.suffix}")

    # Read script
    with open(script_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # Parse AST
    try:
        tree = ast.parse(source_code, filename=str(script_path))
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error at line {e.lineno}: {e.msg}")

    # Extract imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)

    # Extract function definitions
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Skip if target function specified and doesn't match
            if target_function and node.name != target_function:
                continue

            # Get function signature
            args = [arg.arg for arg in node.args.args]
            defaults = [ast.unparse(d) for d in node.args.defaults]

            # Get docstring
            docstring = ast.get_docstring(node)

            # Get body line count
            body_lines = node.end_lineno - node.lineno

            # Detect dependencies (calls to other functions)
            calls = set()
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    if isinstance(subnode.func, ast.Name):
                        calls.add(subnode.func.id)
                    elif isinstance(subnode.func, ast.Attribute):
                        calls.add(f"{ast.unparse(subnode.func.value)}.{subnode.func.attr}")

            functions.append({
                "name": node.name,
                "args": args,
                "defaults": defaults,
                "docstring": docstring,
                "line_start": node.lineno,
                "line_end": node.end_lineno,
                "body_lines": body_lines,
                "calls": list(calls)
            })

    return {
        "script_path": str(script_path),
        "imports": imports,
        "functions": functions
    }

def suggest_consolidation(analysis):
    """
    Suggest how to consolidate extracted functions.

    Args:
        analysis: Output from extract_functions()

    Returns:
        Dictionary with consolidation suggestions
    """
    suggestions = []

    # Pattern: Image download functions
    download_funcs = [f for f in analysis['functions'] if 'download' in f['name'].lower()]
    if download_funcs:
        suggestions.append({
            "pattern": "Image Download",
            "functions": [f['name'] for f in download_funcs],
            "suggestion": "Consider using /batch-download-images skill",
            "rationale": "Rate limiting, retry logic, and manifest tracking already implemented"
        })

    # Pattern: Template/slot detection functions
    slot_funcs = [f for f in analysis['functions'] if 'slot' in f['name'].lower() or 'template' in f['name'].lower()]
    if slot_funcs:
        suggestions.append({
            "pattern": "Template Analysis",
            "functions": [f['name'] for f in slot_funcs],
            "suggestion": "Extract to magic_cards/template.py module",
            "rationale": "Reusable template slot detection logic"
        })

    # Pattern: Card placement/layout functions
    placement_funcs = [f for f in analysis['functions'] if 'place' in f['name'].lower() or 'layout' in f['name'].lower()]
    if placement_funcs:
        suggestions.append({
            "pattern": "Card Placement",
            "functions": [f['name'] for f in placement_funcs],
            "suggestion": "Extract to magic_cards/layout.py module",
            "rationale": "Presentation generation logic"
        })

    # Pattern: Conversion/export functions
    convert_funcs = [f for f in analysis['functions'] if 'convert' in f['name'].lower() or 'export' in f['name'].lower() or 'pdf' in f['name'].lower()]
    if convert_funcs:
        suggestions.append({
            "pattern": "File Conversion",
            "functions": [f['name'] for f in convert_funcs],
            "suggestion": "Consider using /convert-pptx-to-pdf skill",
            "rationale": "Cross-platform LibreOffice integration already solved"
        })

    return suggestions

def main():
    """Main skill execution"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract reusable functions from Python scripts"
    )
    parser.add_argument("script", help="Python script to analyze")
    parser.add_argument("--function", help="Specific function to extract (optional)")

    args = parser.parse_args()

    try:
        print(f"🔍 Extracting Functions from Script")
        print("=" * 70)
        print(f"📄 Script: {args.script}")
        if args.function:
            print(f"🎯 Target: {args.function}")
        print("=" * 70)
        print()

        # Extract functions
        analysis = extract_functions(args.script, args.function)

        # Show imports
        if analysis['imports']:
            print(f"📦 Imports ({len(analysis['imports'])} found):")
            for imp in sorted(set(analysis['imports'])):
                print(f"   - {imp}")
            print()

        # Show functions
        if analysis['functions']:
            print(f"🔧 Functions ({len(analysis['functions'])} found):")
            print()

            for func in analysis['functions']:
                print(f"  {func['name']}({', '.join(func['args'])})")
                print(f"    Lines: {func['line_start']}-{func['line_end']} ({func['body_lines']} lines)")

                if func['docstring']:
                    print(f"    Doc: {func['docstring'][:60]}...")

                if func['calls']:
                    calls_str = ', '.join(sorted(set(func['calls']))[:5])
                    if len(func['calls']) > 5:
                        calls_str += f", ... ({len(func['calls'])} total)"
                    print(f"    Calls: {calls_str}")

                print()

            # Show consolidation suggestions
            suggestions = suggest_consolidation(analysis)

            if suggestions:
                print("💡 Consolidation Suggestions:")
                print()

                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion['pattern']}")
                    print(f"     Functions: {', '.join(suggestion['functions'])}")
                    print(f"     → {suggestion['suggestion']}")
                    print(f"     Why: {suggestion['rationale']}")
                    print()

        else:
            print("⚠️  No functions found in script")

        print("=" * 70)
        print("✅ Analysis complete!")

        return 0

    except FileNotFoundError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except ValueError as e:
        print(f"\\n❌ Error: {e}")
        return 1

    except SyntaxError as e:
        print(f"\\n❌ Syntax error: {e}")
        return 1

    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Output Example

```
🔍 Extracting Functions from Script
======================================================================
📄 Script: analyze_templates.py
======================================================================

📦 Imports (5 found):
   - math
   - os
   - pptx.Presentation
   - pptx.util.Inches
   - sys

🔧 Functions (3 found):

  get_template_slot_positions(template_slide)
    Lines: 14-41 (27 lines)
    Doc: Extract card slot positions from template. Returns slot...
    Calls: append, inches, shape_type, shapes, sort

  place_card_in_slot(slide, card_path, slot_info)
    Lines: 43-114 (71 lines)
    Doc: Place card image in slot with aspect ratio preservatio...
    Calls: Image.open, Inches, exists, inches, open, remove, ... (12 total)

  sanitize_filename(name)
    Lines: 8-12 (4 lines)
    Calls: replace, strip

💡 Consolidation Suggestions:

  1. Template Analysis
     Functions: get_template_slot_positions
     → Extract to magic_cards/template.py module
     Why: Reusable template slot detection logic

  2. Card Placement
     Functions: place_card_in_slot
     → Extract to magic_cards/layout.py module
     Why: Presentation generation logic

======================================================================
✅ Analysis complete!
```

## Error Handling

**`Script not found`**:
```
❌ Error: Script not found: /path/to/script.py
```

**`Not a Python file`**:
```
❌ Error: File must be Python script (.py), got: .txt
```

**`Syntax error`**:
```
❌ Syntax error: Syntax error at line 42: invalid syntax
```

**`No functions found`**:
```
⚠️  No functions found in script
```

## Features

**AST-Based Parsing**:
- Doesn't execute code (safe for untrusted scripts)
- Handles Python 3.8+ syntax
- Extracts function signatures accurately

**Dependency Detection**:
- Identifies imports used
- Tracks function calls (detects helper functions)
- Maps dependencies between functions

**Smart Suggestions**:
- Pattern matching (download, template, placement, conversion)
- Recommends existing skills when applicable
- Suggests module organization

**Function Metadata**:
- Line numbers for easy navigation
- Docstring extraction
- Argument lists with defaults

## Use Cases

**Codebase Consolidation**:
- Analyze iteration artifacts before deletion
- Extract working logic from throwaway scripts
- Identify duplicate functions across files

**Refactoring Planning**:
- Understand script structure before refactor
- Map dependencies between functions
- Plan module boundaries

**Skill Discovery**:
- Identify reusable patterns worth discretizing
- Find candidates for Claude Code skills
- Avoid reinventing existing skills

**Code Review**:
- Understand unfamiliar scripts quickly
- Locate specific functions by pattern
- Audit function complexity (line counts)

## Limitations

- **Python only**: Doesn't work with other languages
- **Surface analysis**: Doesn't detect runtime behavior
- **Simple patterns**: Suggestions based on name matching only
- **No execution**: Can't validate if extracted code actually works

## Exit Codes

- `0`: Success
- `1`: File not found or invalid syntax
