#!/usr/bin/env python3
"""
Download additional Forest cards to complete the EDH deck
An EDH deck needs 100 cards total, we have 75, so we need 25 more basic lands
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
    return name.strip()

def download_card_image(card_name, output_dir="images", delay=0.1, suffix=""):
    """
    Download a card image from Scryfall
    """
    try:
        # Clean the card name for API call
        clean_name = card_name.strip()
        
        # URL encode the card name
        encoded_name = urllib.parse.quote(clean_name)
        
        # Scryfall API endpoint for fuzzy name search
        api_url = f"https://api.scryfall.com/cards/named?fuzzy={encoded_name}"
        
        print(f"🔍 Searching for: {card_name}{suffix}")
        
        # Get card data from Scryfall
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ Card not found: {card_name} (HTTP {response.status_code})")
            return False
        
        card_data = response.json()
        
        # Get the image URL (prefer normal quality)
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
            # Create filename with suffix
            safe_name = sanitize_filename(card_name)
            filename = f"{safe_name}{suffix}.jpg"
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

def main():
    """Download 25 additional Forest cards to complete the EDH deck"""
    
    print(f"🌲 Downloading 25 additional Forest cards to complete EDH deck...")
    print("=" * 60)
    
    successful_downloads = 0
    failed_downloads = []
    
    # Download 25 Forest cards with numbered suffixes
    for i in range(2, 27):  # Start from 2 since we already have Forest.jpg
        suffix = f"_{i:02d}"
        print(f"\n[{i-1}/25] Forest{suffix}")
        
        if download_card_image("Forest", suffix=suffix):
            successful_downloads += 1
        else:
            failed_downloads.append(f"Forest{suffix}")
    
    print("\n" + "=" * 60)
    print(f"🎉 Download complete!")
    print(f"✅ Successful: {successful_downloads}/25")
    
    if failed_downloads:
        print(f"❌ Failed downloads: {len(failed_downloads)}")
        for card in failed_downloads:
            print(f"  - {card}")
    else:
        print("🎊 All Forest cards downloaded successfully!")
    
    # Show total deck count
    total_images = len([f for f in os.listdir("images") if f.endswith(".jpg")])
    print(f"\n🎴 Total cards in deck: {total_images}/100")

if __name__ == "__main__":
    main()