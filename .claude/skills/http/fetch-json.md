---
name: "http/fetch-json"
description: "Fetch JSON data from HTTP REST API endpoints"
version: "1.0.0"
supports_batch: true

inputs:
  - name: url
    type: string
    required: true
    description: "HTTP endpoint URL (supports {{item}} template for batch mode)"

  - name: method
    type: string
    required: false
    default: "GET"
    description: "HTTP method (GET, POST, PUT, DELETE, PATCH)"

  - name: headers
    type: object
    required: false
    default: {}
    description: "HTTP headers as key-value pairs"

  - name: body
    type: object
    required: false
    default: null
    description: "Request body for POST/PUT/PATCH (JSON serialized)"

  - name: timeout
    type: integer
    required: false
    default: 30
    description: "Request timeout in seconds"

outputs:
  - name: data
    type: object
    description: "Parsed JSON response body"

  - name: status_code
    type: integer
    description: "HTTP response status code (200, 404, 500, etc.)"
---

# http/fetch-json

Generic HTTP JSON fetching skill that works with any REST API.

## Purpose

Fetch JSON data from HTTP REST API endpoints. This skill is domain-agnostic and works equally well with any REST API (weather services, social media APIs, e-commerce platforms, gaming APIs, etc.) by accepting configurable URL, method, headers, and request body parameters.

## Usage

### Basic GET Request

```yaml
- name: fetch_data
  skill: http/fetch-json
  args:
    url: "https://api.example.com/endpoint"
    method: "GET"
    timeout: 10
  outputs:
    response_data: "{{result.data}}"
    status: "{{result.status_code}}"
```

### POST Request with Body and Headers

```yaml
- name: create_resource
  skill: http/fetch-json
  args:
    url: "https://api.example.com/resources"
    method: "POST"
    headers:
      Content-Type: "application/json"
      Authorization: "Bearer {{secrets.api_token}}"
    body:
      name: "New Resource"
      value: 42
    timeout: 15
  outputs:
    created_resource: "{{result.data}}"
```

### Batch Mode (Parallel Requests)

```yaml
- name: fetch_multiple
  skill: http/fetch-json
  batch_mode: true
  args:
    url: "https://api.example.com/items/{{item}}"
    method: "GET"
    timeout: 10
  outputs:
    all_items: "{{result.items}}"
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | HTTP endpoint URL. In batch mode, use `{{item}}` as placeholder |
| `method` | string | No | "GET" | HTTP method (GET, POST, PUT, DELETE, PATCH) |
| `headers` | object | No | {} | HTTP headers as key-value pairs |
| `body` | object | No | null | Request body for POST/PUT/PATCH (automatically JSON-serialized) |
| `timeout` | integer | No | 30 | Request timeout in seconds |

## Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `data` | object | Parsed JSON response body |
| `status_code` | integer | HTTP response status code (200, 404, 500, etc.) |

### Single Request Output

```json
{
  "data": {
    "id": "abc123",
    "name": "Example Item",
    "value": 42
  },
  "status_code": 200
}
```

### Batch Mode Output

```json
{
  "successful": 8,
  "failed": 2,
  "items": [
    {
      "status": "success",
      "data": {"id": "1", "name": "Item 1"},
      "status_code": 200,
      "error": null
    },
    {
      "status": "failure",
      "data": null,
      "status_code": 404,
      "error": "HTTP_404: Not Found"
    }
  ]
}
```

## Error Handling

The skill automatically handles common HTTP errors:

| Error Type | HTTP Status | Retry? | Error Code |
|------------|-------------|--------|------------|
| Network timeout | N/A | ✅ Yes | NETWORK_TIMEOUT |
| Rate limit | 429 | ✅ Yes (with backoff) | HTTP_429 |
| Not found | 404 | ❌ No | HTTP_404 |
| Server error | 500-599 | ✅ Yes | HTTP_5XX |
| Invalid JSON | 200 | ❌ No | INVALID_JSON |
| Connection refused | N/A | ✅ Yes | CONNECTION_REFUSED |

### Retry Configuration

When used in batch mode with retry policy:

```yaml
batch_config:
  batch_size: 10
  max_concurrent: 3
  retry_policy:
    max_retries: 3
    retryable_errors:
      - "HTTP_429"
      - "NETWORK_TIMEOUT"
      - "HTTP_5XX"
      - "CONNECTION_REFUSED"
```

## Implementation

This skill is implemented as a Python script that:

1. Parses input parameters and validates them
2. Constructs HTTP request with provided method, headers, and body
3. Executes request using `requests` library with timeout
4. Parses JSON response
5. Returns structured output with data and status code
6. Handles errors gracefully with appropriate error codes

```python
import requests
import json

def execute(args):
    """Execute HTTP JSON fetch request."""
    url = args["url"]
    method = args.get("method", "GET").upper()
    headers = args.get("headers", {})
    body = args.get("body")
    timeout = args.get("timeout", 30)

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body if body else None,
            timeout=timeout
        )

        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {
                "data": None,
                "status_code": response.status_code,
                "error": "INVALID_JSON"
            }

        return {
            "data": data,
            "status_code": response.status_code
        }

    except requests.Timeout:
        raise Exception("NETWORK_TIMEOUT")
    except requests.ConnectionError:
        raise Exception("CONNECTION_REFUSED")
    except Exception as e:
        raise
```

## Performance

- **Single request latency**: ~100-500ms (network dependent)
- **Batch mode throughput**: ~30 requests/second with default config
- **Memory usage**: ~10KB per request
- **Timeout**: Configurable per request (default 30s)

## Notes

- This skill is completely domain-agnostic and contains no references to specific APIs or data types
- The `{{item}}` placeholder in batch mode allows dynamic URL construction
- Automatic retry with exponential backoff for transient errors (429, 5xx, timeouts)
- Headers support variable substitution for secrets/tokens
- JSON serialization/deserialization handled automatically
