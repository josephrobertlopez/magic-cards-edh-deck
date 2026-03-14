#!/usr/bin/env python3
"""Download files with streaming, retry, and progress. Standalone — no dependencies beyond requests."""

import argparse
import os
import random
import sys
import time

import requests


def download_file(url, output_path, retries=3, initial_delay=1.0, timeout=60, chunk_size=8192):
    """Download a file with streaming and exponential backoff retry.

    Args:
        url: File URL
        output_path: Local output path
        retries: Max retry attempts
        initial_delay: Initial backoff delay
        timeout: Request timeout
        chunk_size: Download chunk size in bytes

    Returns:
        True on success, False on failure
    """
    transient_codes = {429, 500, 502, 503, 504}
    delay = initial_delay

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, stream=True, timeout=timeout)

            if resp.status_code == 200:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = (downloaded / total) * 100
                            print(f"\r  {downloaded}/{total} bytes ({pct:.0f}%)", end="", file=sys.stderr)

                if total:
                    print(file=sys.stderr)
                return True

            if resp.status_code in transient_codes and attempt < retries:
                jitter = delay * random.uniform(0.75, 1.25)
                print(f"[retry {attempt+1}/{retries}] HTTP {resp.status_code}, waiting {jitter:.1f}s", file=sys.stderr)
                time.sleep(jitter)
                delay *= 2
                continue

            print(f"HTTP {resp.status_code}: {resp.reason}", file=sys.stderr)
            return False

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < retries:
                jitter = delay * random.uniform(0.75, 1.25)
                print(f"[retry {attempt+1}/{retries}] {type(e).__name__}, waiting {jitter:.1f}s", file=sys.stderr)
                time.sleep(jitter)
                delay *= 2
                continue
            print(f"Failed: {e}", file=sys.stderr)
            return False

    return False


def batch_download(urls_and_outputs, retries=3, delay_between=0.1):
    """Download multiple files sequentially with rate limiting.

    Args:
        urls_and_outputs: List of (url, output_path) tuples
        retries: Max retries per file
        delay_between: Delay between downloads (rate limiting)

    Returns:
        Dict with success/failure counts and details
    """
    results = {"success": 0, "failed": 0, "files": []}

    for i, (url, output) in enumerate(urls_and_outputs):
        print(f"[{i+1}/{len(urls_and_outputs)}] {os.path.basename(output)}", file=sys.stderr)
        ok = download_file(url, output, retries=retries)
        results["files"].append({"url": url, "output": output, "success": ok})
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1
        if delay_between and i < len(urls_and_outputs) - 1:
            time.sleep(delay_between)

    return results


def main():
    parser = argparse.ArgumentParser(description="Download files with retry and progress")
    parser.add_argument("url", help="URL to download")
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--retries", type=int, default=3, help="Max retries (default: 3)")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    args = parser.parse_args()

    ok = download_file(args.url, args.output, retries=args.retries, timeout=args.timeout)
    if ok:
        size = os.path.getsize(args.output)
        print(f"Downloaded: {args.output} ({size:,} bytes)")
    else:
        print(f"Failed to download: {args.url}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
