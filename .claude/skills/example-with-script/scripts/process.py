#!/usr/bin/env python3
"""
Example Python executor script for Anthropic skills format.

Receives workflow variables via environment variables and demonstrates
script execution within the A2A orchestrator framework.
"""

import os
import sys
import json
from pathlib import Path


def main():
    """Execute skill logic with workflow variables from environment."""
    # Read workflow variables from environment
    input_text = os.environ.get('input_text', 'No input provided')
    output_file = os.environ.get('output_file', 'output.txt')

    # Process input
    result = {
        'status': 'success',
        'input_received': input_text,
        'message': f'Processed input: {input_text}',
        'timestamp': os.environ.get('timestamp', 'N/A')
    }

    # Write output
    output_path = Path(output_file)
    output_path.write_text(json.dumps(result, indent=2))

    # Print result to stdout for orchestrator capture
    print(json.dumps(result))

    return 0


if __name__ == '__main__':
    sys.exit(main())
