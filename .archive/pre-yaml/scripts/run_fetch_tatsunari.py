#!/usr/bin/env python3
"""
Fetch Tatsunari Enchantments deck cards from Scryfall
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from magic_cards import fetch_resources_from_list

if __name__ == "__main__":
    print("🐸 Fetching Tatsunari Enchantments deck from Scryfall...\n")

    exit_code = fetch_resources_from_list(
        list_file="decklists/tatsunari_enchantments.txt",
        output_dir="images",
        manifest_path=".claude/state/tatsunari_manifest.json"
    )

    sys.exit(exit_code)
