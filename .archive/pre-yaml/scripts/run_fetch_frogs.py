#!/usr/bin/env python3
import requests
import os
import time
import urllib.parse
import json
from pathlib import Path
from PIL import Image
import io

def sanitize_filename(name):
    """Sanitize card name for use as filename"""
    name = name.replace("/", "_")
    name = name.replace(":", "_")
    for char in ['?', '*', '<', '>', '|', '"', "'"]:
        name = name.replace(char, "")
    return name.strip()

def validate_image(image_data):
    """Validate image file integrity"""
    try:
        img = Image.open(io.BytesIO(image_data))
        img.verify()
        return len(image_data) > 1000
    except Exception:
        return False

def download_card_with_retry(card_name, output_dir="images", max_retries=3):
    """Download card with exponential backoff retry"""
    clean_name = card_name.strip()
    if not clean_name or clean_name.startswith("//"):
        return (True, None, "skipped_comment")

    delays = [0.1, 0.2, 0.4]
    os.makedirs(output_dir, exist_ok=True)

    is_dfc = "//" in clean_name
    if is_dfc:
        front_name, back_name = [part.strip() for part in clean_name.split("//")]
        search_name = front_name
    else:
        search_name = clean_name

    for attempt in range(max_retries):
        try:
            url = f"https://api.scryfall.com/cards/named?fuzzy={urllib.parse.quote(search_name)}"
            response = requests.get(url, timeout=10)

            if response.status_code == 404:
                return (False, None, "card_not_found")

            response.raise_for_status()
            card_data = response.json()

            faces_to_download = []

            if 'card_faces' in card_data and len(card_data['card_faces']) > 1:
                for i, face in enumerate(card_data['card_faces']):
                    if 'image_uris' in face:
                        face_name = f"{sanitize_filename(card_name)}_face{i+1}"
                        faces_to_download.append((face_name, face['image_uris']['normal']))
            elif 'image_uris' in card_data:
                faces_to_download.append((sanitize_filename(card_name), card_data['image_uris']['normal']))
            else:
                return (False, None, "no_image_uri")

            downloaded_paths = []
            for face_name, img_url in faces_to_download:
                file_ext = ".jpg"
                output_file = os.path.join(output_dir, f"{face_name}{file_ext}")

                if os.path.exists(output_file):
                    downloaded_paths.append(output_file)
                    continue

                img_response = requests.get(img_url, timeout=15)
                img_response.raise_for_status()

                if not validate_image(img_response.content):
                    if attempt < max_retries - 1:
                        time.sleep(delays[attempt])
                        continue
                    return (False, None, "corrupted_image")

                with open(output_file, 'wb') as f:
                    f.write(img_response.content)

                downloaded_paths.append(output_file)
                time.sleep(0.1)

            if len(downloaded_paths) > 1:
                return (True, {"paths": downloaded_paths, "faces": len(downloaded_paths)}, None)
            else:
                return (True, downloaded_paths[0], None)

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
            else:
                return (False, None, f"network_error: {str(e)}")

    return (False, None, "max_retries_exceeded")

def download_cards_from_decklist(decklist_file, output_dir="images", manifest_path=".claude/state/fetch_manifest.json"):
    """Main download function"""
    print(f"🎴 Fetching Cards from Scryfall")
    print("=" * 70)
    print(f"📄 Decklist: {decklist_file}")
    print(f"📁 Output: {output_dir}")
    print("=" * 70)

    if not os.path.exists(decklist_file):
        print(f"❌ Error: Decklist file not found: {decklist_file}")
        return 1

    with open(decklist_file, 'r') as f:
        card_names = [line.strip() for line in f if line.strip() and not line.strip().startswith("//")]

    total_cards = len(card_names)
    print(f"\n🔍 Found {total_cards} cards to download\n")

    results = []
    successful = 0
    failed = 0

    for i, card_name in enumerate(card_names, 1):
        print(f"[{i}/{total_cards}] {card_name}")

        success, path_info, error = download_card_with_retry(card_name, output_dir)

        if success:
            successful += 1
            if isinstance(path_info, dict):
                results.append({
                    "name": card_name,
                    "paths": path_info["paths"],
                    "path": path_info["paths"][0],
                    "status": "success",
                    "faces": path_info["faces"]
                })
                print(f"  ✅ Downloaded ({path_info['faces']} faces)")
            else:
                results.append({
                    "name": card_name,
                    "path": path_info,
                    "status": "success"
                })
                print(f"  ✅ Downloaded")
        else:
            failed += 1
            results.append({
                "name": card_name,
                "status": "failed",
                "error": error
            })
            print(f"  ❌ Failed: {error}")

    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "decklist_path": decklist_file,
        "total_cards": total_cards,
        "successful": successful,
        "failed": failed,
        "cards": results
    }

    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 70)
    print(f"📊 Results: {successful}/{total_cards} cards downloaded")
    print(f"💾 Manifest: {manifest_path}")
    print("=" * 70)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    download_cards_from_decklist(
        "decklists/frog_tribal.txt",
        "images",
        ".claude/state/frog_manifest.json"
    )
