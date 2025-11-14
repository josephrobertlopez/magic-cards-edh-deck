# validate-manifest-integrity

Validate JSON manifest structure and referenced file integrity.

## Usage

```
/validate-manifest-integrity <manifest.json>
```

**Parameters**:
- `manifest.json`: JSON manifest file to validate (required)

**Output**:
- Validation report with passed/failed checks
- Line numbers of errors for easy fixing
- File existence verification for referenced paths

**Examples**:
```
/validate-manifest-integrity .claude/state/krenko_manifest.json
/validate-manifest-integrity deck_manifest.json
```

## Implementation

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

def validate_manifest(manifest_path):
    """
    Validate manifest JSON structure and file references.

    Args:
        manifest_path: Path to manifest JSON file

    Returns:
        Tuple of (is_valid: bool, errors: list, warnings: list)
    """
    manifest_path = Path(manifest_path).resolve()

    if not manifest_path.exists():
        return (False, [f"Manifest file not found: {manifest_path}"], [])

    errors = []
    warnings = []

    # Load JSON
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return (False, [f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}"], [])
    except Exception as e:
        return (False, [f"Failed to read manifest: {e}"], [])

    # Required fields
    required_fields = ['timestamp', 'total_cards', 'successful', 'failed', 'cards']

    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: '{field}'")

    # If cards field exists, validate structure
    if 'cards' in manifest:
        if not isinstance(manifest['cards'], list):
            errors.append(f"Field 'cards' must be array, got {type(manifest['cards']).__name__}")
        else:
            total_cards = len(manifest['cards'])

            # Validate counts match
            if 'total_cards' in manifest and manifest['total_cards'] != total_cards:
                errors.append(f"total_cards ({manifest['total_cards']}) doesn't match cards array length ({total_cards})")

            success_count = 0
            fail_count = 0

            # Validate each card
            for i, card in enumerate(manifest['cards']):
                if not isinstance(card, dict):
                    errors.append(f"Card [{i}] must be object, got {type(card).__name__}")
                    continue

                # Check required card fields
                if 'name' not in card:
                    errors.append(f"Card [{i}] missing 'name' field")
                if 'status' not in card:
                    errors.append(f"Card [{i}] missing 'status' field")
                else:
                    if card['status'] not in ['success', 'failed', 'pending']:
                        errors.append(f"Card [{i}] has invalid status: '{card['status']}'")

                    # Validate success cards have path
                    if card['status'] == 'success':
                        success_count += 1

                        if 'path' not in card and 'paths' not in card:
                            errors.append(f"Card [{i}] ({card.get('name', 'unknown')}) has status='success' but no 'path' or 'paths' field")
                        else:
                            # Check file existence
                            paths_to_check = []
                            if 'path' in card:
                                paths_to_check.append(card['path'])
                            if 'paths' in card:
                                paths_to_check.extend(card['paths'])

                            for path in paths_to_check:
                                if not Path(path).exists():
                                    warnings.append(f"Card [{i}] ({card.get('name', 'unknown')}) references missing file: {path}")

                    # Validate failed cards have reason
                    elif card['status'] == 'failed':
                        fail_count += 1
                        if 'error' not in card and 'reason' not in card:
                            warnings.append(f"Card [{i}] ({card.get('name', 'unknown')}) has status='failed' but no error/reason")

            # Validate success/fail counts
            if 'successful' in manifest and manifest['successful'] != success_count:
                errors.append(f"successful count ({manifest['successful']}) doesn't match actual ({success_count})")

            if 'failed' in manifest and manifest['failed'] != fail_count:
                errors.append(f"failed count ({manifest['failed']}) doesn't match actual ({fail_count})")

    is_valid = len(errors) == 0

    return (is_valid, errors, warnings)

def main(manifest_path):
    """Main skill execution"""
    print(f"📋 Validating Manifest Integrity")
    print("=" * 70)
    print(f"📄 Manifest: {manifest_path}")
    print()

    is_valid, errors, warnings = validate_manifest(manifest_path)

    if is_valid and len(warnings) == 0:
        print("✅ Manifest is valid!")
        print()

        # Load and show stats
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        print(f"📊 Summary:")
        print(f"   Total cards: {manifest.get('total_cards', 0)}")
        print(f"   Successful: {manifest.get('successful', 0)}")
        print(f"   Failed: {manifest.get('failed', 0)}")

        return 0

    elif is_valid and len(warnings) > 0:
        print("⚠️  Manifest is valid but has warnings:")
        print()
        for warning in warnings:
            print(f"   • {warning}")

        return 0

    else:
        print("❌ Manifest validation failed:")
        print()

        if errors:
            print("🔴 Errors (must fix):")
            for error in errors:
                print(f"   • {error}")
            print()

        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"   • {warning}")
            print()

        print("Fix errors and run validation again.")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate-manifest-integrity <manifest.json>")
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
```

## Output Examples

### Valid Manifest
```
📋 Validating Manifest Integrity
======================================================================
📄 Manifest: .claude/state/krenko_manifest.json

✅ Manifest is valid!

📊 Summary:
   Total cards: 100
   Successful: 100
   Failed: 0
```

### Invalid Manifest
```
📋 Validating Manifest Integrity
======================================================================
📄 Manifest: broken_manifest.json

❌ Manifest validation failed:

🔴 Errors (must fix):
   • Missing required field: 'total_cards'
   • Card [42] missing 'status' field
   • Card [67] has status='success' but no 'path' or 'paths' field
   • successful count (98) doesn't match actual (97)

⚠️  Warnings:
   • Card [12] (Lightning Bolt) references missing file: images/lightning_bolt.jpg

Fix errors and run validation again.
```

## Error Handling

**Common Errors**:

**`Manifest file not found`**:
```
❌ Manifest validation failed:
🔴 Errors (must fix):
   • Manifest file not found: /path/to/manifest.json
```

**`Invalid JSON`**:
```
❌ Manifest validation failed:
🔴 Errors (must fix):
   • Invalid JSON at line 23, column 5: Expecting ',' delimiter
```

**`Missing required field`**:
```
❌ Manifest validation failed:
🔴 Errors (must fix):
   • Missing required field: 'timestamp'
   • Missing required field: 'cards'
```

## Validation Checks

**Schema Validation**:
- Required fields: `timestamp`, `total_cards`, `successful`, `failed`, `cards`
- Cards must be array of objects
- Each card must have `name` and `status`

**Count Validation**:
- `total_cards` must equal `cards` array length
- `successful` must equal count of cards with `status="success"`
- `failed` must equal count of cards with `status="failed"`

**File Validation**:
- Cards with `status="success"` must have `path` or `paths` field
- Files referenced in `path`/`paths` should exist (warning if missing)
- Cards with `status="failed"` should have `error` or `reason` (warning if missing)

**Status Validation**:
- Status must be one of: `success`, `failed`, `pending`
- Invalid status values trigger error

## Use Cases

**Pre-Generation Validation**:
- Check manifest before using it to generate presentation
- Catch schema errors early before wasting time on generation

**CI/CD Integration**:
- Validate manifests in automated pipelines
- Fail builds if manifests are corrupted

**Manual Editing Recovery**:
- After hand-editing manifest JSON, verify it's still valid
- Find specific line numbers of errors for quick fixes

**Data Integrity Audits**:
- Periodic checks that cached manifests haven't corrupted
- Verify all referenced images still exist

## Exit Codes

- `0`: Valid (with or without warnings)
- `1`: Invalid (errors found)
