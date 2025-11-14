#!/usr/bin/env python3
"""
Convert Tatsunari Enchantments presentation to PDF
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from magic_cards import transform_to_pdf

if __name__ == "__main__":
    print("📄 Converting Tatsunari Enchantments to PDF...\n")

    pdf_path = transform_to_pdf(
        source_path="outputs/tatsunari_enchantments.pptx",
        output_dir="outputs"
    )

    print(f"\n✨ PDF ready for printing: {pdf_path}")
    sys.exit(0)
