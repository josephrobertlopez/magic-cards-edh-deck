#!/usr/bin/env python3
"""
Download missing cards to complete the Tifa Lockhart EDH deck
- Both sides of Walk-In Closet // Forgotten Cellar
- Basic lands to reach 100 cards total (72 unique + 28 basics = 100)
"""

import requests
import os
import time
import urllib.parse
from pathlib import Path

def sanitize_filename(name):
    """Sanitize card name for use as filename"""
    # Replace problematic characters
    name = name.replace("/", "_")
    name = name.replace(":", "_")
    name = name.replace("?", "")
    name = name.replace("*", "")
    name = name.replace("<", "")
    name = name.replace(">", "")
    name = name.replace("|", "")
    name = name.replace('"', "")
    name = name.replace("'", "")
    name = name.replace("//", "_")
    return name.strip()

def download_card_image(card_name, output_dir="images", delay=0.1, filename_override=None):
    """
    Download a card image from Scryfall
    """
    try:
        # Clean the card name for API call
        clean_name = card_name.strip()
        
        # URL encode the card name
        encoded_name = urllib.parse.quote(clean_name)
        
        # Scryfall API endpoint for exact name search
        api_url = f"https://api.scryfall.com/cards/named?exact={encoded_name}"
        
        print(f"🔍 Searching for: {card_name}")
        
        # Get card data from Scryfall
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ Card not found: {card_name} (HTTP {response.status_code})")
            return False
        
        card_data = response.json()
        
        # Get the image URL (prefer normal quality)
        image_urls = card_data.get('image_uris', {})
        
        # Handle double-faced cards
        if not image_urls and 'card_faces' in card_data:
            # This is a double-faced card, we want the front face by default
            front_face = card_data['card_faces'][0]
            image_urls = front_face.get('image_uris', {})
        
        if 'normal' in image_urls:
            image_url = image_urls['normal']
        elif 'large' in image_urls:
            image_url = image_urls['large']
        elif 'small' in image_urls:
            image_url = image_urls['small']
        else:
            print(f"  ❌ No image found for: {card_name}")
            return False
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Download the image
        print(f"  📥 Downloading image...")
        img_response = requests.get(image_url, timeout=30)
        
        if img_response.status_code == 200:
            # Create filename
            if filename_override:
                filename = filename_override
            else:
                safe_name = sanitize_filename(card_name)
                filename = f"{safe_name}.jpg"
            
            filepath = os.path.join(output_dir, filename)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            print(f"  ✅ Saved: {filename}")
            
            # Rate limiting - be nice to Scryfall
            time.sleep(delay)
            return True
        else:
            print(f"  ❌ Failed to download image for: {card_name}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error downloading {card_name}: {e}")
        return False

def download_card_face(card_name, face_index, face_name, output_dir="images", delay=0.1):
    """
    Download a specific face of a double-faced card
    """
    try:
        # Clean the card name for API call
        clean_name = card_name.strip()
        
        # URL encode the card name
        encoded_name = urllib.parse.quote(clean_name)
        
        # Scryfall API endpoint for exact name search
        api_url = f"https://api.scryfall.com/cards/named?exact={encoded_name}"
        
        print(f"🔍 Searching for {face_name} side of: {card_name}")
        
        # Get card data from Scryfall
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ Card not found: {card_name} (HTTP {response.status_code})")
            return False
        
        card_data = response.json()
        
        # Handle double-faced cards
        if 'card_faces' in card_data and len(card_data['card_faces']) > face_index:
            card_face = card_data['card_faces'][face_index]
            image_urls = card_face.get('image_uris', {})
            actual_face_name = card_face.get('name', face_name)
        else:
            print(f"  ❌ Face {face_index} not found for: {card_name}")
            return False
        
        if 'normal' in image_urls:
            image_url = image_urls['normal']
        elif 'large' in image_urls:
            image_url = image_urls['large']
        elif 'small' in image_urls:
            image_url = image_urls['small']
        else:
            print(f"  ❌ No image found for {face_name} face of: {card_name}")
            return False
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Download the image
        print(f"  📥 Downloading {face_name} face image...")
        img_response = requests.get(image_url, timeout=30)
        
        if img_response.status_code == 200:
            # Create filename using the actual face name
            safe_name = sanitize_filename(actual_face_name)
            filename = f"{safe_name}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            print(f"  ✅ Saved: {filename}")
            
            # Rate limiting - be nice to Scryfall
            time.sleep(delay)
            return True
        else:
            print(f"  ❌ Failed to download {face_name} image for: {card_name}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error downloading {face_name} face of {card_name}: {e}")
        return False

def main():
    """Download missing cards to complete the deck"""
    
    print(f"🎴 Downloading missing cards for complete Tifa Lockhart EDH deck...")
    print("=" * 60)
    
    successful_downloads = 0
    failed_downloads = []
    
    # Step 1: Download both faces of the double-faced card
    print(f"\n🔄 Step 1: Double-faced card - Walk-In Closet // Forgotten Cellar")
    
    double_faced_card = "Walk-In Closet // Forgotten Cellar"
    
    # Download front face (Walk-In Closet)
    if download_card_face(double_faced_card, 0, "Walk-In Closet"):
        successful_downloads += 1
    else:
        failed_downloads.append("Walk-In Closet")
    
    # Download back face (Forgotten Cellar)  
    if download_card_face(double_faced_card, 1, "Forgotten Cellar"):
        successful_downloads += 1
    else:
        failed_downloads.append("Forgotten Cellar")
    
    # Step 2: Download basic lands to reach 100 cards
    print(f"\n🌲 Step 2: Adding basic lands to reach 100 cards total")
    
    # We have 72 unique named cards + 2 faces of double card = 74 cards
    # Need 26 more basic lands to reach 100
    basic_lands = ["Forest"] * 26
    
    for i, land in enumerate(basic_lands):
        suffix = f"_{i+2:02d}" if i > 0 else ""  # Start numbering from 02
        filename = f"Forest{suffix}.jpg" if suffix else "Forest.jpg"
        
        # Check if this file already exists
        if os.path.exists(f"images/{filename}"):
            print(f"  ⏭️ Skipping {filename} (already exists)")
            continue
            
        print(f"\n[{i+1}/26] Forest{suffix}")
        
        if download_card_image("Forest", filename_override=filename):
            successful_downloads += 1
        else:
            failed_downloads.append(f"Forest{suffix}")
    
    print("\n" + "=" * 60)
    print(f"🎉 Download complete!")
    print(f"✅ Successful: {successful_downloads}")
    
    if failed_downloads:
        print(f"❌ Failed downloads: {len(failed_downloads)}")
        for card in failed_downloads:
            print(f"  - {card}")
    else:
        print("🎊 All missing cards downloaded successfully!")
    
    # Show total deck count
    total_images = len([f for f in os.listdir("images") if f.endswith(".jpg")])
    print(f"\n🎴 Total cards in deck: {total_images}/100")

if __name__ == "__main__":
    main()