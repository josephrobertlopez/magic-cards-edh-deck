#!/usr/bin/env python3
"""
HTTP JSON Fetch Skill Executor

Generic HTTP request skill that works with any JSON REST API.
Supports GET, POST, PUT, DELETE, PATCH methods with configurable timeouts and retries.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session_with_retries(max_retries: int = 3) -> requests.Session:
    """Create requests session with retry strategy."""
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def execute_http_fetch_json(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Execute HTTP request and return JSON response.

    Args:
        url: Target URL
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Optional request headers
        body: Optional request body (for POST/PUT/PATCH)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Dictionary with keys:
        - data: Parsed JSON response
        - status_code: HTTP status code
        - success: Boolean indicating success

    Raises:
        Exception: On request failure with error details
    """
    session = create_session_with_retries(max_retries)

    try:
        response = session.request(
            method=method.upper(),
            url=url,
            headers=headers or {},
            json=body,
            timeout=timeout
        )

        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError:
            raise Exception(f"INVALID_JSON: Response is not valid JSON: {response.text[:200]}")

        return {
            "data": data,
            "status_code": response.status_code,
            "success": True
        }

    except requests.exceptions.Timeout:
        raise Exception(f"REQUEST_TIMEOUT: Request exceeded {timeout} seconds")

    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP_ERROR: {e.response.status_code} - {e.response.text[:200]}")

    except requests.exceptions.ConnectionError:
        raise Exception(f"CONNECTION_ERROR: Failed to connect to {url}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"REQUEST_FAILED: {str(e)}")

    finally:
        session.close()


def main():
    """CLI entry point for skill executor."""
    parser = argparse.ArgumentParser(description="Fetch JSON from HTTP API")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "DELETE", "PATCH"])
    parser.add_argument("--headers", type=json.loads, help="JSON headers object")
    parser.add_argument("--body", type=json.loads, help="JSON body object")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry attempts")

    args = parser.parse_args()

    try:
        result = execute_http_fetch_json(
            url=args.url,
            method=args.method,
            headers=args.headers,
            body=args.body,
            timeout=args.timeout,
            max_retries=args.max_retries
        )

        # Output JSON result to stdout (orchestrator expects this)
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "data": None
        }
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
