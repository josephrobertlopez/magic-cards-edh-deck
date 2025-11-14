"""
Protocol Response Wrapper: Handle multiple response formats (JSON/XML/YAML/binary)

Provides a thin wrapper over requests.Response to support protocol-first API integration
with automatic content-type detection and format conversion.
"""

import json
from dataclasses import dataclass
from typing import Dict, Any, Optional
import requests


@dataclass
class ProtocolResponse:
    """
    Wrapper for HTTP responses supporting multiple content formats.

    Handles common CRUD API response types:
    - application/json → .json()
    - application/xml, text/xml → .text() (caller parses)
    - text/yaml, application/yaml → .text() (caller parses)
    - image/*, application/octet-stream → .bytes()
    - text/html (error pages) → .text()

    Examples:
        >>> resp = ProtocolResponse(requests_response)
        >>> if resp.is_json:
        ...     data = resp.json()
        >>> elif resp.is_image:
        ...     binary = resp.bytes()
    """

    _raw: requests.Response

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._raw.status_code

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return dict(self._raw.headers)

    @property
    def content_type(self) -> str:
        """Content-Type header value (e.g., 'application/json')."""
        return self._raw.headers.get('Content-Type', 'application/octet-stream').split(';')[0].strip()

    @property
    def is_json(self) -> bool:
        """True if response is JSON format."""
        return 'json' in self.content_type.lower()

    @property
    def is_xml(self) -> bool:
        """True if response is XML format."""
        ct = self.content_type.lower()
        return 'xml' in ct

    @property
    def is_yaml(self) -> bool:
        """True if response is YAML format."""
        ct = self.content_type.lower()
        return 'yaml' in ct or 'yml' in ct

    @property
    def is_image(self) -> bool:
        """True if response is image (PNG, JPG, etc.)."""
        return self.content_type.lower().startswith('image/')

    @property
    def is_binary(self) -> bool:
        """True if response is binary data."""
        ct = self.content_type.lower()
        return ct.startswith('image/') or 'octet-stream' in ct or 'application/pdf' in ct

    def json(self) -> Dict[str, Any]:
        """
        Parse response as JSON.

        Returns:
            Dict containing parsed JSON data

        Raises:
            ValueError: If response is not valid JSON
        """
        if not self.is_json:
            raise ValueError(
                f"Cannot parse as JSON: content-type is '{self.content_type}'. "
                f"Use .text() or .bytes() instead."
            )
        try:
            return self._raw.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {str(e)}")

    def text(self) -> str:
        """
        Get response as text string (for XML, YAML, HTML, plain text).

        Returns:
            Response body as UTF-8 decoded string
        """
        return self._raw.text

    def bytes(self) -> bytes:
        """
        Get response as raw bytes (for images, PDFs, binary data).

        Returns:
            Response body as bytes
        """
        return self._raw.content

    def auto_parse(self) -> Any:
        """
        Automatically parse response based on content-type.

        Returns:
            - Dict for JSON responses
            - str for text/XML/YAML responses
            - bytes for binary/image responses

        Raises:
            ValueError: If content-type cannot be auto-detected
        """
        if self.is_json:
            return self.json()
        elif self.is_binary or self.is_image:
            return self.bytes()
        else:
            return self.text()

    def raise_for_status(self) -> None:
        """Raise HTTPError for bad status codes (4xx, 5xx)."""
        self._raw.raise_for_status()


def wrap_response(response: requests.Response) -> ProtocolResponse:
    """
    Wrap a requests.Response in ProtocolResponse.

    Args:
        response: Standard requests library Response object

    Returns:
        ProtocolResponse wrapper with content-type detection

    Examples:
        >>> import requests
        >>> resp = requests.get("https://api.example.com/data")
        >>> wrapped = wrap_response(resp)
        >>> if wrapped.is_json:
        ...     data = wrapped.json()
    """
    return ProtocolResponse(_raw=response)
