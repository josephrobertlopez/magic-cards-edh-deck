"""Data fetcher module for downloading resources from APIs."""

import requests
import os
import time
import json
import urllib.parse
from pathlib import Path
from PIL import Image


def sanitize_filename(name):
    """Sanitize name for use as filename."""
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


def get_nested_value(data, path):
    """Get nested dict value using dot notation path like 'image_uris.png'."""
    parts = path.split('.')
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def fetch_resources_from_list(
    resource_list_file,
    output_dir,
    manifest_path,
    api_url_template,
    response_schema,
    size_hints,
    rate_limit_delay=0.1
):
    """
    Fetch resources from API based on list file.
    
    Args:
        resource_list_file: Path to file with one item per line
        output_dir: Directory to save downloaded images
        manifest_path: Path for output manifest JSON
        api_url_template: API URL with {identifier} placeholder
        response_schema: Dict mapping logical names to JSON paths
        size_hints: Dict with width_px, height_px, dpi, source
        rate_limit_delay: Delay between requests in seconds
        
    Returns:
        Exit code (0 = success, 1 = not found, 3 = network error)
    """
    # Read resource list
    with open(resource_list_file, 'r') as f:
        items = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    print(f"🎴 Fetching {len(items)} items from API...")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "source": resource_list_file,
        "total_items": len(items),
        "successful": 0,
        "failed": 0,
        "items": []
    }
    
    for idx, item in enumerate(items, 1):
        print(f"\n[{idx}/{len(items)}] {item}")
        
        try:
            # Handle double-faced cards
            clean_name = item.split("//")[0].strip() if "//" in item else item.strip()
            
            # Build API URL
            encoded_name = urllib.parse.quote(clean_name)
            api_url = api_url_template.replace("{identifier}", encoded_name)
            
            print(f"  🔍 Fetching from API...")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ Not found (HTTP {response.status_code})")
                manifest["failed"] += 1
                manifest["items"].append({
                    "name": item,
                    "status": "failed",
                    "error": f"HTTP {response.status_code}"
                })
                continue
            
            data = response.json()
            
            # Extract image URL using schema
            image_url_path = response_schema.get("image_url", "image_uris.png")
            image_url = get_nested_value(data, image_url_path)
            
            # Handle double-faced cards (Scryfall specific)
            if not image_url and 'card_faces' in data:
                front_face = data['card_faces'][0]
                image_url = get_nested_value(front_face, image_url_path)
            
            if not image_url:
                print(f"  ❌ No image URL found at path: {image_url_path}")
                manifest["failed"] += 1
                manifest["items"].append({
                    "name": item,
                    "status": "failed",
                    "error": "No image URL found"
                })
                continue
            
            # Download image
            print(f"  📥 Downloading image...")
            img_response = requests.get(image_url, timeout=30)
            
            if img_response.status_code != 200:
                print(f"  ❌ Image download failed")
                manifest["failed"] += 1
                manifest["items"].append({
                    "name": item,
                    "status": "failed",
                    "error": "Image download failed"
                })
                continue
            
            # Save image
            safe_name = sanitize_filename(item)
            filename = f"{safe_name}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Resize if size hints provided
            if size_hints and size_hints.get("source") == "provider":
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                
                # Resize to target dimensions
                target_width = size_hints.get("width_px", 750)
                target_height = size_hints.get("height_px", 1050)
                
                with Image.open(filepath) as img:
                    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    img_resized.save(filepath, "PNG")
            else:
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
            
            print(f"  ✅ Saved: {filename}")
            
            manifest["successful"] += 1
            manifest["items"].append({
                "name": item,
                "status": "success",
                "filename": filename,
                "filepath": filepath
            })
            
            # Rate limiting
            time.sleep(rate_limit_delay)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            manifest["failed"] += 1
            manifest["items"].append({
                "name": item,
                "status": "failed",
                "error": str(e)
            })
    
    # Save manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n🎉 Fetch complete!")
    print(f"✅ Successful: {manifest['successful']}/{manifest['total_items']}")
    print(f"📄 Manifest saved: {manifest_path}")
    
    # Return exit code
    if manifest["failed"] == manifest["total_items"]:
        return 3  # All failed - network error
    elif manifest["successful"] == 0:
        return 1  # None found
    else:
        return 0  # Success (at least some items fetched)
