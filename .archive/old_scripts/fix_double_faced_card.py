#!/usr/bin/env python3
"""
Fix the double-faced card download by trying each face individually
"""

import requests
import os
import time
import urllib.parse
from pathlib import Path

def sanitize_filename(name):
    """Sanitize card name for use as filename"""
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

def download_individual_card(card_name, output_dir="images", delay=0.1):
    """Download an individual card by its exact name"""
    try:
        # Clean the card name for API call
        clean_name = card_name.strip()
        
        # URL encode the card name
        encoded_name = urllib.parse.quote(clean_name)
        
        # Try exact search first
        api_url = f"https://api.scryfall.com/cards/named?exact={encoded_name}"
        
        print(f"🔍 Searching for: {card_name}")
        
        # Get card data from Scryfall
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            # Try fuzzy search if exact fails
            api_url = f"https://api.scryfall.com/cards/named?fuzzy={encoded_name}"
            response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ Card not found: {card_name} (HTTP {response.status_code})")
            return False
        
        card_data = response.json()
        
        # Get the image URL
        image_urls = card_data.get('image_uris', {})
        
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
            safe_name = sanitize_filename(card_name)
            filename = f"{safe_name}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            print(f"  ✅ Saved: {filename}")
            
            # Rate limiting
            time.sleep(delay)
            return True
        else:
            print(f"  ❌ Failed to download image for: {card_name}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error downloading {card_name}: {e}")
        return False

def main():
    """Download both faces of the double-faced card individually"""
    
    print(f"🎴 Fixing double-faced card downloads...")
    print("=" * 50)
    
    # Try downloading each face as individual cards
    faces = ["Walk-In Closet", "Forgotten Cellar"]
    
    successful = 0
    failed = []
    
    for face in faces:
        print(f"\n🔄 Downloading: {face}")
        if download_individual_card(face):
            successful += 1
        else:
            failed.append(face)
    
    print("\n" + "=" * 50)
    print(f"🎉 Fix complete!")
    print(f"✅ Successful: {successful}")
    
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for card in failed:
            print(f"  - {card}")
    else:
        print("🎊 Both faces downloaded successfully!")

if __name__ == "__main__":
    main()