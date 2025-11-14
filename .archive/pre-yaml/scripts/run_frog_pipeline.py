#!/usr/bin/env python3
"""
Complete pipeline for Frog Tribal deck: Fetch → Generate → PDF
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from magic_cards import fetch_resources_from_list, generate_document, transform_to_pdf

if __name__ == "__main__":
    print("🐸 Frog Tribal Deck Pipeline Starting! Ribbit ribbit!\n")

    # Step 1: Fetch cards from Scryfall
    print("=" * 70)
    print("STEP 1: Fetching froggy cards from Scryfall")
    print("=" * 70)
    exit_code = fetch_resources_from_list(
        resource_list_file="decklists/frog_tribal.txt",
        output_dir="images",
        manifest_path=".claude/state/frog_manifest.json",
        api_url_template="https://api.scryfall.com/cards/named?fuzzy={identifier}",
        response_schema={
            "image_url": "image_uris.png",
            "image_url_multi": "card_faces[].image_uris.png",
            "name": "name"
        },
        size_hints={
            "width_px": 750,
            "height_px": 1050,
            "dpi": 300,
            "source": "provider"
        }
    )

    if exit_code != 0:
        print("\n❌ Fetch failed!")
        sys.exit(1)

    # Step 2: Generate presentation
    print("\n" + "=" * 70)
    print("STEP 2: Generating froggy presentation")
    print("=" * 70)
    output_path = generate_document(
        manifest_path=".claude/state/frog_manifest.json",
        template_path="template_2v6h_FIXED.pptx",
        output_path="outputs/frog_tribal.pptx"
    )

    # Step 3: Convert to PDF
    print("\n" + "=" * 70)
    print("STEP 3: Converting to PDF")
    print("=" * 70)
    pdf_path = transform_to_pdf(
        source_path=output_path,
        output_dir="outputs"
    )

    print("\n" + "=" * 70)
    print("✨ FROG TRIBAL DECK COMPLETE! 🐸✨")
    print("=" * 70)
    print(f"📄 PPTX: {output_path}")
    print(f"📄 PDF:  {pdf_path}")
    print("=" * 70)

    sys.exit(0)
