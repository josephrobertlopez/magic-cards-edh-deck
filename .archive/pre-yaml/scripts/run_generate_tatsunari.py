#!/usr/bin/env python3
"""
Generate Tatsunari Enchantments presentation from manifest
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from magic_cards import generate_document

if __name__ == "__main__":
    print("🎨 Generating Tatsunari Enchantments presentation...\n")

    output_path = generate_document(
        manifest_path=".claude/state/tatsunari_manifest.json",
        template_path="template_2v6h_FIXED.pptx",
        output_path="outputs/tatsunari_enchantments.pptx"
    )

    print(f"\n✨ Presentation saved: {output_path}")
    sys.exit(0)
