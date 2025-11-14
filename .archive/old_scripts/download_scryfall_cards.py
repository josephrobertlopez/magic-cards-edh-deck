#!/usr/bin/env python3
"""
Download Magic card images from Scryfall API based on decklist
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

def download_card_image(card_name, output_dir="images", delay=0.1):
    """
    Download a card image from Scryfall
    """
    try:
        # Clean the card name for API call
        clean_name = card_name.strip()
        
        # Special handling for double-faced cards
        if "//" in clean_name:
            # Use the first part for the search
            clean_name = clean_name.split("//")[0].strip()
        
        # URL encode the card name
        encoded_name = urllib.parse.quote(clean_name)
        
        # Scryfall API endpoint for fuzzy name search
        api_url = f"https://api.scryfall.com/cards/named?fuzzy={encoded_name}"
        
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
            # For double-faced cards, use the front face
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

def main():
    """Main function to download all cards from the decklist"""
    
    # Your complete decklist
    decklist = [
        # Commander
        "Tifa Lockhart",
        
        # Creatures (16)
        "Bane of Progress",
        "Cultivator Colossus", 
        "Horizon Explorer",
        "Jumbo Cactuar",
        "Mightform Harmonizer",
        "Ohran Frostfang",
        "Oracle of Mul Daya",
        "Quilled Greatwurm",
        "Rampaging Baloths",
        "Sakura-Tribe Scout",
        "Scute Swarm",
        "Summon: Titan",
        "Tireless Tracker",
        "Titania, Nature's Force",
        "Toski, Bearer of Secrets",
        "Wayward Swordtooth",
        
        # Instants
        "Archdruid's Charm",
        "Beast Within",
        "Entish Restoration",
        "Fog",
        "Harrow",
        "Naturalize",
        "Nature's Claim",
        "Ram Through",
        "Tifa's Limit Break",
        
        # Sorceries
        "Cultivate",
        "Harmonize",
        "Kodama's Reach",
        "Rampant Growth",
        "Reshape the Earth",
        "Rishkar's Expertise",
        "Scale Up",
        "Skyshroud Claim",
        "Tempt with Discovery",
        "Threats Undetected",
        "Three Visits",
        "Titania's Command",
        "Traverse the Outlands",
        "Whirlwind",
        "Will of the Sultai",
        
        # Artifacts
        "Blackblade Reforged",
        "Conduit of Worlds",
        "Endless Atlas",
        "Genji Glove",
        "Nevinyrral's Disk",
        "Seer's Sundial",
        "Skyclave Pick-Axe",
        "Smoke Bomb",
        "Sol Ring",
        "Staff of Titania",
        "Swiftfoot Boots",
        "Sword of the Animist",
        
        # Enchantments
        "Case of the Locked Hothouse",
        "Ride the Shoopuf",
        "Thickest in the Thicket",
        "Tribute to the World Tree",
        "Unnatural Growth",
        "Walk-In Closet // Forgotten Cellar",
        "Zendikar's Roil",
        
        # Planeswalkers
        "Nissa, Vital Force",
        "Wrenn and Seven",
        
        # Lands
        "Bant Panorama",
        "Brokers Hideout",
        "Cabaretti Courtyard",
        "Evolving Wilds",
        "Forest",
        "Jund Panorama",
        "Naya Panorama",
        "Riveteers Overlook",
        "Rogue's Passage",
        "Scavenger Grounds",
        "Terramorphic Expanse",
        "Vibrant Cityscape",
        "War Room"
    ]
    
    print(f"🎴 Starting download of {len(decklist)} cards from Scryfall...")
    print("=" * 60)
    
    successful_downloads = 0
    failed_downloads = []
    
    for i, card_name in enumerate(decklist, 1):
        print(f"\n[{i}/{len(decklist)}] {card_name}")
        
        if download_card_image(card_name):
            successful_downloads += 1
        else:
            failed_downloads.append(card_name)
    
    print("\n" + "=" * 60)
    print(f"🎉 Download complete!")
    print(f"✅ Successful: {successful_downloads}/{len(decklist)}")
    
    if failed_downloads:
        print(f"❌ Failed downloads: {len(failed_downloads)}")
        for card in failed_downloads:
            print(f"  - {card}")
    else:
        print("🎊 All cards downloaded successfully!")

if __name__ == "__main__":
    main()