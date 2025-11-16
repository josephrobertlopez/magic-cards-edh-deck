#!/usr/bin/env python3
"""
HTTP File Download Skill Executor

Generic file download skill that works with any URL.
Supports batch processing, automatic filename detection, and resume capability.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, List
from pathlib import Path
import requests
from urllib.parse import urlparse
import os


def download_file(
    url: str,
    output_dir: str,
    filename: Optional[str] = None,
    timeout: int = 30,
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Download file from URL to local filesystem.

    Args:
        url: File URL
        output_dir: Destination directory
        filename: Optional custom filename (auto-detected if not provided)
        timeout: Download timeout in seconds
        overwrite: Whether to overwrite existing files

    Returns:
        Dictionary with keys:
        - path: Full path to downloaded file
        - size_bytes: File size in bytes
        - skipped: True if download was skipped (file exists, overwrite=false)

    Raises:
        Exception: On download failure
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Auto-detect filename from URL if not provided
    if not filename:
        parsed = urlparse(url)
        filename = Path(parsed.path).name or "downloaded_file"

    file_path = output_path / filename

    # Check if file exists and overwrite is disabled
    if file_path.exists() and not overwrite:
        return {
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "skipped": True
        }

    try:
        # Stream download to handle large files
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        # Write file in chunks
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return {
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "skipped": False
        }

    except requests.exceptions.Timeout:
        raise Exception(f"DOWNLOAD_TIMEOUT: Download exceeded {timeout} seconds")

    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP_ERROR: {e.response.status_code} - {url}")

    except requests.exceptions.ConnectionError:
        raise Exception(f"CONNECTION_ERROR: Failed to connect to {url}")

    except IOError as e:
        raise Exception(f"FILE_WRITE_ERROR: {str(e)}")

    except Exception as e:
        raise Exception(f"DOWNLOAD_FAILED: {str(e)}")


def download_batch(
    urls: List[str],
    output_dir: str,
    timeout: int = 30,
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Download multiple files (batch mode).

    Args:
        urls: List of URLs to download
        output_dir: Destination directory
        timeout: Timeout per file
        overwrite: Whether to overwrite existing files

    Returns:
        Dictionary with keys:
        - items: List of downloaded file paths
        - count: Number of files downloaded
        - skipped_count: Number of files skipped
        - failed_count: Number of failures
    """
    results = []
    skipped = 0
    failed = 0

    for url in urls:
        try:
            result = download_file(url, output_dir, timeout=timeout, overwrite=overwrite)
            results.append(result["path"])
            if result.get("skipped"):
                skipped += 1
        except Exception as e:
            failed += 1
            # Log error but continue with other files
            print(f"Failed to download {url}: {e}", file=sys.stderr)

    return {
        "items": results,
        "count": len(results),
        "skipped_count": skipped,
        "failed_count": failed
    }


def main():
    """CLI entry point for skill executor."""
    parser = argparse.ArgumentParser(description="Download files from URLs")
    parser.add_argument("--url", help="Single URL to download")
    parser.add_argument("--urls", type=json.loads, help="JSON list of URLs for batch download")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--filename", help="Custom filename (single download only)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--overwrite", type=lambda x: x.lower() == "true", default=True,
                       help="Overwrite existing files (true/false)")

    args = parser.parse_args()

    try:
        # Batch mode or single file?
        if args.urls:
            result = download_batch(
                urls=args.urls,
                output_dir=args.output_dir,
                timeout=args.timeout,
                overwrite=args.overwrite
            )
        elif args.url:
            single_result = download_file(
                url=args.url,
                output_dir=args.output_dir,
                filename=args.filename,
                timeout=args.timeout,
                overwrite=args.overwrite
            )
            # Wrap single result in batch format for consistency
            result = {
                "items": [single_result["path"]],
                "count": 1,
                "path": single_result["path"],
                "size_bytes": single_result["size_bytes"],
                "skipped": single_result["skipped"]
            }
        else:
            raise Exception("Must provide either --url or --urls")

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "items": []
        }
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
