#!/usr/bin/env python3
"""
Generate MTG deck on US Letter paper (8.5" × 11") with 8 cards per page.
Cards are placed in landscape orientation (3.5"w × 2.5"h) in 2×4 grid.
"""
import sys
import time
import requests
from pathlib import Path
import subprocess
import math
from pptx import Presentation
from pptx.util import Inches
from pptx.dml.color import RGBColor
from PIL import Image

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

def get_letter_size_card_positions():
    """
    Calculate 8 card positions for US Letter paper (8.5" × 11").
    Returns 2×4 grid with cards in landscape orientation, centered on page.
    """
    # Letter paper dimensions
    page_width = 8.5
    page_height = 11.0

    # Card dimensions in landscape (rotated 90°)
    # 2% larger than sleeve-compatible size for better visibility when printing
    # (2.60" × 3.62" = 2% larger than 2.55" × 3.55")
    card_width = 3.62  # MTG card height becomes width
    card_height = 2.60  # MTG card width becomes height

    # Gap between cards
    gap_horizontal = 0.2
    gap_vertical = 0.2

    # Calculate total dimensions needed
    total_width = 2 * card_width + gap_horizontal
    total_height = 4 * card_height + 3 * gap_vertical

    # Center on page
    margin_left = (page_width - total_width) / 2
    margin_top = (page_height - total_height) / 2

    positions = []

    # 2 columns × 4 rows
    for row in range(4):
        for col in range(2):
            left = margin_left + col * (card_width + gap_horizontal)
            top = margin_top + row * (card_height + gap_vertical)

            positions.append({
                'left': left,
                'top': top,
                'width': card_width,
                'height': card_height
            })

    return positions

def place_card_landscape(slide, card_path, slot_info):
    """
    Place card image in landscape orientation (rotated 90°).
    """
    try:
        if not card_path.exists():
            print(f"    ⚠️  Image not found: {card_path}")
            return False

        with Image.open(card_path) as img:
            # Rotate image 90° for landscape placement
            img_rotated = img.rotate(-90, expand=True)

            # Calculate aspect ratios
            slot_aspect = slot_info['width'] / slot_info['height']
            img_aspect = img_rotated.width / img_rotated.height

            # Preserve aspect ratio while fitting to slot
            if img_aspect > slot_aspect:
                new_width = slot_info['width']
                new_height = slot_info['width'] / img_aspect
            else:
                new_height = slot_info['height']
                new_width = slot_info['height'] * img_aspect

            # Center in slot
            left = slot_info['left'] + (slot_info['width'] - new_width) / 2
            top = slot_info['top'] + (slot_info['height'] - new_height) / 2

            # Save rotated image temporarily
            temp_path = card_path.parent / f"temp_rotated_{card_path.name}"
            img_rotated.save(temp_path)

        # Add picture to slide
        slide.shapes.add_picture(
            str(temp_path),
            Inches(left),
            Inches(top),
            width=Inches(new_width),
            height=Inches(new_height)
        )

        # Clean up temp file
        temp_path.unlink()

        return True

    except Exception as e:
        print(f"    ❌ Failed to place card: {e}")
        return False

def create_letter_size_deck(card_images, output_file):
    """
    Create deck presentation on US Letter paper (8.5" × 11").
    """
    print(f"📄 Creating Letter size presentation (8.5\" × 11\")")

    # Get card positions for Letter paper
    card_positions = get_letter_size_card_positions()
    cards_per_page = len(card_positions)  # Should be 8
    slides_needed = math.ceil(len(card_images) / cards_per_page)

    print(f"📐 Layout: 2 columns × 4 rows (8 cards per page)")
    print(f"📏 Cards in landscape: 3.5\" × 2.5\" each")
    print(f"📄 Creating {slides_needed} slides")

    # Create presentation
    prs = Presentation()
    prs.slide_width = Inches(8.5)
    prs.slide_height = Inches(11.0)

    blank_layout = prs.slide_layouts[6]  # Blank layout

    # Process cards in groups of 8
    cards_placed = 0
    for slide_num in range(slides_needed):
        # Add new slide
        slide = prs.slides.add_slide(blank_layout)

        # White background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(255, 255, 255)

        # Calculate card indices for this slide
        start_idx = slide_num * cards_per_page
        end_idx = min(start_idx + cards_per_page, len(card_images))

        print(f"\n📄 Slide {slide_num + 1}: Cards {start_idx + 1} to {end_idx}")

        # Place cards using calculated positions
        for i, card_idx in enumerate(range(start_idx, end_idx)):
            if i >= len(card_positions):
                break

            card_path = card_images[card_idx]
            slot = card_positions[i]

            card_name = card_path.stem
            print(f"  [{i+1}] {card_name}")
            if place_card_landscape(slide, card_path, slot):
                print(f"      ✅ Placed at ({slot['left']:.2f}\", {slot['top']:.2f}\") - {slot['width']:.2f}\" × {slot['height']:.2f}\"")
                cards_placed += 1
            else:
                print(f"      ❌ Failed to place")

    # Save presentation
    prs.save(output_file)
    print(f"\n💾 Saved presentation: {output_file}")
    print(f"📊 Stats: {cards_placed} cards across {slides_needed} slides")
    print(f"📏 Paper size: 8.5\" × 11\" (US Letter)")
    print(f"🎴 Card layout: 2×4 grid, landscape orientation")

    return True

def main(card_list_file, output_dir="outputs"):
    """Generate deck on Letter size paper."""

    print("🎴 MTG Deck Generator (US Letter Size - 8 cards per page)")
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

        # Handle double-faced cards (download BOTH sides)
        if 'card_faces' in card_data:
            # Double-faced card: download both front and back
            for face_idx, face in enumerate(card_data['card_faces']):
                face_name = face.get('name', card_name)
                face_type = "Front" if face_idx == 0 else "Back"
                image_url = face.get('image_uris', {}).get('normal')

                if not image_url:
                    print(f"  ⚠️  {face_type}: No image available")
                    continue

                # Use face name for filename
                safe_name = face_name.replace(' ', '_').replace('/', '_').replace("'", "").replace(',', '')
                image_path = images_dir / f"{safe_name}.jpg"

                if image_path.exists():
                    print(f"  ✓ {face_type}: {face_name} (cached)")
                    successful_images.append(image_path)
                else:
                    if download_image(image_url, image_path):
                        print(f"  ✓ {face_type}: {face_name}")
                        successful_images.append(image_path)

                # Rate limiting between faces
                time.sleep(0.1)

        elif 'image_uris' in card_data:
            # Single-faced card
            image_url = card_data['image_uris'].get('normal')

            if not image_url:
                print(f"  ⚠️  No image available")
                continue

            # Download image
            safe_name = card_name.replace(' ', '_').replace('/', '_').replace("'", "")
            image_path = images_dir / f"{safe_name}.jpg"

            if image_path.exists():
                print(f"  ✓ Already downloaded")
                successful_images.append(image_path)
            else:
                if download_image(image_url, image_path):
                    print(f"  ✓ Downloaded")
                    successful_images.append(image_path)
        else:
            print(f"  ⚠️  No image available")
            continue

        # Rate limiting
        time.sleep(0.1)

    print()
    print(f"✓ Successfully downloaded {len(successful_images)}/{len(card_names)} cards")
    print()

    if len(successful_images) == 0:
        print("❌ No cards downloaded, cannot generate deck")
        return 1

    # Generate PPTX
    print("📄 Generating Letter size deck...")
    pptx_path = output_path / "deck_letter_size.pptx"

    if not create_letter_size_deck(successful_images, pptx_path):
        return 1

    print()

    # Convert to PDF
    print("📄 Converting to PDF...")
    pdf_path = output_path / "deck_letter_size.pdf"

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
    print(f"🎴 {len(successful_images)} cards on US Letter paper (8.5\" × 11\")")
    print(f"📏 8 cards per page in 2×4 grid (landscape)")
    print(f"✂️  Ready to print and cut!")

    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_deck_letter_size.py <card_list_file>")
        print()
        print("Example:")
        print("  python3 generate_deck_letter_size.py decklists/user_deck.txt")
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
