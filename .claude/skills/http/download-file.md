---
name: "http/download-file"
description: "Download files from URLs to local filesystem"
version: "1.0.0"
supports_batch: true

inputs:
  - name: url
    type: string
    required: true
    description: "URL to download from (http:// or https://)"

  - name: output_dir
    type: string
    required: true
    description: "Directory to save downloaded file"

  - name: filename
    type: string
    required: false
    default: null
    description: "Custom filename (auto-detected from URL if not provided)"

  - name: overwrite
    type: boolean
    required: false
    default: true
    description: "Overwrite existing file (false = skip if exists)"

  - name: timeout
    type: integer
    required: false
    default: 60
    description: "Download timeout in seconds"

outputs:
  - name: path
    type: string
    description: "Full path to downloaded file"

  - name: size_bytes
    type: integer
    description: "File size in bytes"

  - name: skipped
    type: boolean
    description: "True if download was skipped (file exists, overwrite=false)"

  - name: items
    type: list
    description: "List of downloaded file paths (batch mode only)"
---

# http/download-file

Download files from URLs to local filesystem with automatic directory creation and overwrite control.

## Purpose

This skill provides domain-agnostic file downloading from any URL. It works with any file type including images (JPG, PNG, GIF), documents (PDF, DOCX, XLSX), videos (MP4, AVI), archives (ZIP, TAR), and any other downloadable content.

## Implementation

### Prerequisites

- Python 3.9+
- requests library
- pathlib (stdlib)
- os (stdlib)

### Algorithm

1. **Parse URL**: Extract filename from URL if not provided
2. **Create Directory**: Create output_dir if it doesn't exist (including parent directories)
3. **Check Existing**: If overwrite=false and file exists, return skipped=true
4. **Download File**: Use requests.get() with streaming for large files
5. **Write to Disk**: Save content to output_dir/filename
6. **Return Result**: Return {path, size_bytes, skipped}

### Error Handling

- **Network timeout**: Retry with exponential backoff (if batch mode with retry_policy)
- **Connection refused**: Raise CONNECTION_REFUSED error
- **HTTP 404**: Raise FILE_NOT_FOUND error
- **HTTP 403/401**: Raise PERMISSION_DENIED error
- **Disk full**: Raise DISK_FULL error
- **Invalid URL**: Raise INVALID_URL error

### Pseudo-code

```python
import requests
from pathlib import Path

def execute_http_download_file(args):
    url = args["url"]
    output_dir = Path(args["output_dir"])
    filename = args.get("filename")
    overwrite = args.get("overwrite", True)
    timeout = args.get("timeout", 60)

    # Extract filename from URL if not provided
    if not filename:
        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            filename = "downloaded_file"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full output path
    output_path = output_dir / filename

    # Check if file exists and overwrite=false
    if output_path.exists() and not overwrite:
        return {
            "path": str(output_path),
            "size_bytes": output_path.stat().st_size,
            "skipped": True
        }

    # Download file
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        # Write to disk
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Get file size
        file_size = output_path.stat().st_size

        return {
            "path": str(output_path),
            "size_bytes": file_size,
            "skipped": False
        }

    except requests.Timeout:
        raise Exception("NETWORK_TIMEOUT")
    except requests.ConnectionError:
        raise Exception("CONNECTION_REFUSED")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception("FILE_NOT_FOUND")
        elif e.response.status_code in (401, 403):
            raise Exception("PERMISSION_DENIED")
        else:
            raise
```

## Usage Examples

### Example 1: Download Single File

```yaml
- name: download_image
  skill: http/download-file
  args:
    url: "https://example.com/image.jpg"
    output_dir: "/tmp/downloads"
    overwrite: true
    timeout: 30
  outputs:
    image_path: "{{result.path}}"
```

### Example 2: Batch Download Multiple Files

```yaml
- name: download_images
  skill: http/download-file
  batch_mode: true
  args:
    url: "{{item}}"
    output_dir: "/tmp/images"
    overwrite: false
  outputs:
    image_paths: "{{result.items}}"
```

### Example 3: Download with Custom Filename

```yaml
- name: download_pdf
  skill: http/download-file
  args:
    url: "https://example.com/report.pdf?v=123"
    output_dir: "/tmp/reports"
    filename: "monthly_report.pdf"
    timeout: 120
  outputs:
    report_path: "{{result.path}}"
```

### Example 4: Skip If Already Downloaded

```yaml
- name: download_video
  skill: http/download-file
  args:
    url: "https://example.com/tutorial.mp4"
    output_dir: "/tmp/videos"
    overwrite: false
  outputs:
    video_path: "{{result.path}}"
    was_skipped: "{{result.skipped}}"
```

## Batch Mode Support

When `batch_mode: true`, the skill processes multiple URLs in parallel:

- **Input**: List of URLs (via `{{item}}` template)
- **Output**: `result.items` contains list of downloaded file paths
- **Concurrency**: Controlled by `batch_config.max_concurrent`
- **Retry**: Automatic retry on transient failures (timeouts, 5xx errors)

## Domain-Agnostic Design

This skill contains **zero domain-specific logic**. It works equally well for:

- E-commerce: Product images, catalogs, PDFs
- Media: Videos, audio files, thumbnails
- Documents: Reports, spreadsheets, presentations
- Data: CSV files, JSON exports, XML data
- Archives: ZIP files, tarballs, backups

The skill accepts any URL and downloads any file type without special handling for specific domains or content types.
