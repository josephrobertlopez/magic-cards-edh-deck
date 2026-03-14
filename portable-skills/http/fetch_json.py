#!/usr/bin/env python3
"""Fetch JSON from any REST API with retry and jitter. Standalone — no dependencies beyond requests."""

import argparse
import json
import random
import sys
import time

import requests


def fetch_json(url, headers=None, retries=3, initial_delay=1.0, timeout=30):
    """Fetch JSON from URL with exponential backoff + jitter.

    Args:
        url: Target URL
        headers: Optional HTTP headers dict
        retries: Max retry attempts for transient errors
        initial_delay: Initial backoff delay in seconds
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response
    """
    transient_codes = {429, 500, 502, 503, 504}
    delay = initial_delay

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers or {}, timeout=timeout)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code in transient_codes and attempt < retries:
                jitter = delay * random.uniform(0.75, 1.25)
                print(f"[retry {attempt+1}/{retries}] HTTP {resp.status_code}, waiting {jitter:.1f}s", file=sys.stderr)
                time.sleep(jitter)
                delay *= 2
                continue

            resp.raise_for_status()

        except requests.exceptions.Timeout:
            if attempt < retries:
                jitter = delay * random.uniform(0.75, 1.25)
                print(f"[retry {attempt+1}/{retries}] Timeout, waiting {jitter:.1f}s", file=sys.stderr)
                time.sleep(jitter)
                delay *= 2
                continue
            raise

        except requests.exceptions.ConnectionError:
            if attempt < retries:
                jitter = delay * random.uniform(0.75, 1.25)
                print(f"[retry {attempt+1}/{retries}] Connection error, waiting {jitter:.1f}s", file=sys.stderr)
                time.sleep(jitter)
                delay *= 2
                continue
            raise

    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch JSON from any REST API")
    parser.add_argument("url", help="API URL to fetch")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--header", "-H", action="append", default=[], help="HTTP header (Key: Value)")
    parser.add_argument("--retries", type=int, default=3, help="Max retries (default: 3)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    headers = {}
    for h in args.header:
        key, _, value = h.partition(":")
        headers[key.strip()] = value.strip()

    data = fetch_json(args.url, headers=headers, retries=args.retries, timeout=args.timeout)

    if data is None:
        print("Failed to fetch JSON after retries", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    output = json.dumps(data, indent=indent)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
