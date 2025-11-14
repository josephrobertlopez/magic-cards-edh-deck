"""
GraphQL-Inspired Schema Resolver for API Response Mapping

Provides JSONPath-like syntax for extracting fields from arbitrary API responses.

Syntax Support:
  - "field.nested.value"           → dict navigation
  - "array[].field"                → array iteration
  - "field.array[0].value"         → array indexing
  - "field1|field2"                → fallback (try field1, then field2)

Examples:
  resolve(data, "sprites.front_default")
  resolve(data, "card_faces[].image_uris.normal")
  resolve(data, "image_uris.normal|sprites.default")
"""

from typing import Any, Dict, List, Optional, Union


class SchemaResolver:
    """Resolve nested fields in JSON responses using path expressions."""

    @staticmethod
    def resolve(data: Any, path: str) -> Optional[Union[str, List[str]]]:
        """
        Resolve a path expression against JSON data.

        Args:
            data: JSON-like dict/list structure
            path: Path expression (e.g., "sprites.front_default")

        Returns:
            Resolved value (string, list of strings, or None if not found)

        Examples:
            >>> resolver = SchemaResolver()
            >>> data = {"sprites": {"front_default": "http://example.com/image.png"}}
            >>> resolver.resolve(data, "sprites.front_default")
            "http://example.com/image.png"

            >>> data = {"card_faces": [{"image_uris": {"normal": "url1"}}, {"image_uris": {"normal": "url2"}}]}
            >>> resolver.resolve(data, "card_faces[].image_uris.normal")
            ["url1", "url2"]
        """
        # Handle fallback syntax: "field1|field2|field3"
        if "|" in path:
            for fallback_path in path.split("|"):
                result = SchemaResolver._resolve_single(data, fallback_path.strip())
                if result is not None:
                    return result
            return None

        return SchemaResolver._resolve_single(data, path)

    @staticmethod
    def _resolve_single(data: Any, path: str) -> Optional[Union[str, List[str]]]:
        """Resolve a single path expression (no fallbacks)."""
        if not path:
            return data

        parts = path.split(".")
        current = data

        for i, part in enumerate(parts):
            # Handle array iteration: "field[]" or "field[0]"
            if "[" in part and "]" in part:
                field_name = part[:part.index("[")]
                index_expr = part[part.index("[")+1:part.index("]")]

                # Navigate to array field
                if field_name:
                    if isinstance(current, dict) and field_name in current:
                        current = current[field_name]
                    else:
                        return None

                # Handle array iteration []
                if index_expr == "":
                    if not isinstance(current, list):
                        return None

                    # Iterate array and resolve remaining path for each item
                    remaining_path = ".".join(parts[i+1:])
                    if remaining_path:
                        results = []
                        for item in current:
                            resolved = SchemaResolver._resolve_single(item, remaining_path)
                            if resolved is not None:
                                if isinstance(resolved, list):
                                    results.extend(resolved)
                                else:
                                    results.append(resolved)
                        return results if results else None
                    else:
                        return current

                # Handle array indexing [0]
                else:
                    try:
                        idx = int(index_expr)
                        if isinstance(current, list) and 0 <= idx < len(current):
                            current = current[idx]
                        else:
                            return None
                    except ValueError:
                        return None

            # Regular field navigation
            else:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None

        return current

    @staticmethod
    def resolve_schema(data: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Resolve all fields in a schema against JSON data.

        Args:
            data: JSON response from API
            schema: Schema dict with field mappings

        Returns:
            Dict with resolved values

        Example:
            >>> schema = {
            ...     "image_url": "sprites.front_default",
            ...     "name": "name"
            ... }
            >>> data = {"sprites": {"front_default": "http://..."}, "name": "Pikachu"}
            >>> SchemaResolver.resolve_schema(data, schema)
            {"image_url": "http://...", "name": "Pikachu"}
        """
        resolved = {}
        for key, path in schema.items():
            value = SchemaResolver.resolve(data, path)
            if value is not None:
                resolved[key] = value
        return resolved


# Convenience function for quick access
def resolve_field(data: Any, path: str) -> Optional[Union[str, List[str]]]:
    """Convenience function to resolve a single field."""
    return SchemaResolver.resolve(data, path)


def extract_image_variants(data: Dict[str, Any], image_field_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Extract all available image size variants from API response.

    This function attempts to extract multiple image URLs representing different
    size variants (e.g., "small", "normal", "large", "png") from an API response.

    Args:
        data: JSON response from API
        image_field_paths: List of JSONPath expressions to try (in priority order)
                          Example: ["image_uris.large", "image_uris.normal", "image_uris.small"]

    Returns:
        List of variant dicts, each containing:
        - url: str - Image URL
        - variant_name: str - Variant identifier (e.g., "large", "normal")
        - dimensions: Optional[tuple] - (width_px, height_px) if available in response

    Example:
        >>> data = {
        ...     "image_uris": {
        ...         "small": "https://api.example.com/cards/123/small.jpg",
        ...         "normal": "https://api.example.com/cards/123/normal.jpg",
        ...         "large": "https://api.example.com/cards/123/large.jpg"
        ...     }
        ... }
        >>> paths = ["image_uris.small", "image_uris.normal", "image_uris.large"]
        >>> extract_image_variants(data, paths)
        [
            {"url": "https://api.example.com/cards/123/small.jpg", "variant_name": "small", "dimensions": None},
            {"url": "https://api.example.com/cards/123/normal.jpg", "variant_name": "normal", "dimensions": None},
            {"url": "https://api.example.com/cards/123/large.jpg", "variant_name": "large", "dimensions": None}
        ]
    """
    variants = []
    seen_urls = set()  # Deduplicate in case paths overlap

    for path in image_field_paths:
        url = SchemaResolver.resolve(data, path)

        if url and url not in seen_urls:
            # Extract variant name from path (last segment before array or end)
            # E.g., "image_uris.large" -> "large", "sprites.front_default" -> "front_default"
            variant_name = path.split(".")[-1].replace("[]", "").strip()

            variants.append({
                "url": url,
                "variant_name": variant_name,
                "dimensions": None  # Will be populated after download via Pillow
            })
            seen_urls.add(url)

    return variants
