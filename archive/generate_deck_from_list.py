#!/usr/bin/env python3
"""
Simple script to generate deck PDF from a card list.
"""
import sys
import json
import time
import requests
from pathlib import Path
import subprocess

def fetch_card_from_scryfall(card_name):
    """Fetch card data from Scryfall API."""
    url = f"https://api.scryfall.com/cards/named"
    params = {"fuzzy": card_name}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ❌ Failed to fetch {card_name}: {e}")
        return None

def download_image(url, output_path):
    """Download image from URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"  ❌ Failed to download image: {e}")
        return False

def main(card_list_file, output_dir="outputs"):
    """Generate deck from card list."""

    print("🎴 MTG Deck Generator")
    print("=" * 70)

    # Read card list
    card_list_path = Path(card_list_file)
    if not card_list_path.exists():
        print(f"❌ Card list not found: {card_list_file}")
        return 1

    with open(card_list_path, 'r') as f:
        card_names = [line.strip() for line in f if line.strip()]

    print(f"📋 Found {len(card_names)} cards in list")
    print()

    # Create output directories
    images_dir = Path("images")
    images_dir.mkdir(exist_ok=True)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Fetch and download cards
    print("🔍 Fetching card data from Scryfall...")
    successful_images = []

    for i, card_name in enumerate(card_names, 1):
        print(f"[{i}/{len(card_names)}] {card_name}")

        # Fetch card data
        card_data = fetch_card_from_scryfall(card_name)
        if not card_data:
            continue

        # Get image URL
        image_url = card_data.get('image_uris', {}).get('normal')
        if not image_url:
            print(f"  ⚠️  No image available")
            continue

        # Download image
        safe_name = card_name.replace(' ', '_').replace('/', '_').replace("'", "")
        image_path = images_dir / f"{safe_name}.jpg"

        if image_path.exists():
            print(f"  ✓ Already downloaded")
            successful_images.append(str(image_path))
        else:
            if download_image(image_url, image_path):
                print(f"  ✓ Downloaded")
                successful_images.append(str(image_path))

        # Rate limiting
        time.sleep(0.1)

    print()
    print(f"✓ Successfully downloaded {len(successful_images)}/{len(card_names)} cards")
    print()

    if len(successful_images) == 0:
        print("❌ No cards downloaded, cannot generate deck")
        return 1

    # Generate PPTX using grid-layout skill
    print("📄 Generating PPTX...")
    pptx_path = output_path / "user_deck.pptx"

    grid_layout_script = Path(".claude/skills/document/grid-layout.py")
    if not grid_layout_script.exists():
        print(f"❌ Grid layout script not found: {grid_layout_script}")
        return 1

    cmd = [
        "python3",
        str(grid_layout_script),
        "--image-paths", json.dumps(successful_images),
        "--rows", "3",
        "--columns", "3",
        "--output-path", str(pptx_path),
        "--slide-width", "10",
        "--slide-height", "7.5",
        "--margin", "0.5",
        "--spacing", "0.1"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_data = json.loads(result.stdout)
        print(f"  ✓ Created {output_data['slide_count']} slides")
        print(f"  ✓ {output_data['images_per_slide']} cards per slide")
        print(f"  📁 {pptx_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate PPTX: {e}")
        print(f"Error: {e.stderr}")
        return 1

    print()

    # Convert to PDF
    print("📄 Converting to PDF...")
    pdf_path = output_path / "user_deck.pdf"

    # Try LibreOffice command line
    try:
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_path),
            str(pptx_path)
        ], check=True, capture_output=True, timeout=60)
        print(f"  ✓ {pdf_path}")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"  ⚠️  PDF conversion failed (LibreOffice not available)")
        print(f"  ℹ️  You can convert {pptx_path} to PDF manually")

    print()
    print("=" * 70)
    print("🎉 Deck generation complete!")
    print(f"📁 PPTX: {pptx_path}")
    if pdf_path.exists():
        print(f"📁 PDF:  {pdf_path}")
    print(f"🎴 {len(successful_images)} cards across {output_data['slide_count']} pages")

    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_deck_from_list.py <card_list_file>")
        print()
        print("Example:")
        print("  python3 generate_deck_from_list.py decklists/user_deck.txt")
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
