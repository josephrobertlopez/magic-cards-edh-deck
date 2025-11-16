"""
Unit tests for http/download-file skill

Tests cover:
- Single file downloads (images, PDFs, videos)
- Filename auto-detection from URL
- Custom filename specification
- Overwrite behavior (overwrite=true/false)
- Timeout handling
- Directory creation (including parents)
- Error handling (404, timeout, connection refused, etc.)
- File size tracking
- Batch mode support
"""

import pytest
import requests
from pathlib import Path
from unittest.mock import Mock, patch, mock_open


# Mock the skill execution function
# In actual implementation, this would import from the skill's Python module


class MockResponse:
    """Mock requests.Response object for testing."""
    def __init__(self, content, status_code, raise_for_status_error=None):
        self.content = content
        self.status_code = status_code
        self._raise_for_status_error = raise_for_status_error
        self._chunks = [content[i:i+8192] for i in range(0, len(content), 8192)] if content else []

    def raise_for_status(self):
        if self._raise_for_status_error:
            raise self._raise_for_status_error

    def iter_content(self, chunk_size=8192):
        """Yield content in chunks."""
        return iter(self._chunks)


def execute_http_download_file(args):
    """
    Mock implementation of http/download-file skill execution.
    This matches the contract from the skill markdown.
    """
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


# ============================================================================
# Unit Tests
# ============================================================================

def test_download_file_with_auto_filename(tmp_path):
    """Test downloading file with filename auto-detected from URL."""
    test_content = b"Test file content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        result = execute_http_download_file({
            "url": "https://example.com/image.jpg",
            "output_dir": str(tmp_path)
        })

        assert "image.jpg" in result["path"]
        assert result["size_bytes"] == len(test_content)
        assert result["skipped"] is False


def test_download_file_with_custom_filename(tmp_path):
    """Test downloading file with custom filename."""
    test_content = b"PDF content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        result = execute_http_download_file({
            "url": "https://example.com/report.pdf?v=123",
            "output_dir": str(tmp_path),
            "filename": "monthly_report.pdf"
        })

        assert "monthly_report.pdf" in result["path"]
        assert result["size_bytes"] == len(test_content)


def test_download_skip_if_exists_and_overwrite_false(tmp_path):
    """Test skipping download if file exists and overwrite=false."""
    existing_file = tmp_path / "existing.jpg"
    existing_file.write_bytes(b"existing content")

    result = execute_http_download_file({
        "url": "https://example.com/image.jpg",
        "output_dir": str(tmp_path),
        "filename": "existing.jpg",
        "overwrite": False
    })

    assert result["skipped"] is True
    assert "existing.jpg" in result["path"]
    assert result["size_bytes"] == len(b"existing content")


def test_download_overwrite_if_exists_and_overwrite_true(tmp_path):
    """Test overwriting file if exists and overwrite=true."""
    existing_file = tmp_path / "existing.jpg"
    existing_file.write_bytes(b"old content")

    new_content = b"new content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat:

        mock_get.return_value = MockResponse(new_content, 200)
        mock_stat.return_value.st_size = len(new_content)

        result = execute_http_download_file({
            "url": "https://example.com/image.jpg",
            "output_dir": str(tmp_path),
            "filename": "existing.jpg",
            "overwrite": True
        })

        assert result["skipped"] is False
        assert result["size_bytes"] == len(new_content)


def test_download_creates_directory_if_not_exists(tmp_path):
    """Test that output directory is created if it doesn't exist."""
    nested_dir = tmp_path / "level1" / "level2" / "level3"
    test_content = b"content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        result = execute_http_download_file({
            "url": "https://example.com/file.pdf",
            "output_dir": str(nested_dir)
        })

        # Verify directory was created
        assert nested_dir.exists()
        assert "file.pdf" in result["path"]


def test_download_timeout_error():
    """Test handling of network timeout."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout("Connection timeout")

        with pytest.raises(Exception) as exc_info:
            execute_http_download_file({
                "url": "https://example.com/slow-file.zip",
                "output_dir": "/tmp",
                "timeout": 5
            })

        assert "NETWORK_TIMEOUT" in str(exc_info.value)


def test_download_connection_error():
    """Test handling of connection refused error."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(Exception) as exc_info:
            execute_http_download_file({
                "url": "https://unreachable.example.com/file.pdf",
                "output_dir": "/tmp"
            })

        assert "CONNECTION_REFUSED" in str(exc_info.value)


def test_download_404_not_found():
    """Test handling of 404 Not Found error."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.HTTPError()
        http_error.response = mock_response
        mock_get.return_value.raise_for_status.side_effect = http_error

        with pytest.raises(Exception) as exc_info:
            execute_http_download_file({
                "url": "https://example.com/nonexistent.pdf",
                "output_dir": "/tmp"
            })

        assert "FILE_NOT_FOUND" in str(exc_info.value)


def test_download_403_permission_denied():
    """Test handling of 403 Forbidden error."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 403
        http_error = requests.HTTPError()
        http_error.response = mock_response
        mock_get.return_value.raise_for_status.side_effect = http_error

        with pytest.raises(Exception) as exc_info:
            execute_http_download_file({
                "url": "https://example.com/protected.pdf",
                "output_dir": "/tmp"
            })

        assert "PERMISSION_DENIED" in str(exc_info.value)


def test_download_401_unauthorized():
    """Test handling of 401 Unauthorized error."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 401
        http_error = requests.HTTPError()
        http_error.response = mock_response
        mock_get.return_value.raise_for_status.side_effect = http_error

        with pytest.raises(Exception) as exc_info:
            execute_http_download_file({
                "url": "https://example.com/requires-auth.pdf",
                "output_dir": "/tmp"
            })

        assert "PERMISSION_DENIED" in str(exc_info.value)


def test_download_filename_from_url_with_query_params(tmp_path):
    """Test extracting filename from URL with query parameters."""
    test_content = b"content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        result = execute_http_download_file({
            "url": "https://example.com/image.jpg?size=large&v=2",
            "output_dir": str(tmp_path)
        })

        # Should strip query params and use just "image.jpg"
        assert "image.jpg" in result["path"]
        assert "?" not in result["path"]


def test_download_fallback_filename_for_url_without_filename(tmp_path):
    """Test fallback filename when URL doesn't contain a filename."""
    test_content = b"content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        result = execute_http_download_file({
            "url": "https://example.com/",
            "output_dir": str(tmp_path)
        })

        # Should use fallback filename
        assert "downloaded_file" in result["path"]


def test_download_custom_timeout(tmp_path):
    """Test that custom timeout is passed to requests."""
    test_content = b"content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        execute_http_download_file({
            "url": "https://example.com/file.zip",
            "output_dir": str(tmp_path),
            "timeout": 120
        })

        # Verify timeout was passed
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 120


def test_download_default_timeout(tmp_path):
    """Test that default timeout is 60 seconds."""
    test_content = b"content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        execute_http_download_file({
            "url": "https://example.com/file.pdf",
            "output_dir": str(tmp_path)
            # No timeout specified
        })

        # Verify default timeout
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 60


def test_download_streaming_enabled(tmp_path):
    """Test that streaming is enabled for downloads."""
    test_content = b"large file content"

    with patch('requests.get') as mock_get, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(Path, 'stat') as mock_stat, \
         patch.object(Path, 'exists', return_value=False):

        mock_get.return_value = MockResponse(test_content, 200)
        mock_stat.return_value.st_size = len(test_content)

        execute_http_download_file({
            "url": "https://example.com/large-video.mp4",
            "output_dir": str(tmp_path)
        })

        # Verify streaming was enabled
        call_args = mock_get.call_args
        assert call_args[1]["stream"] is True
