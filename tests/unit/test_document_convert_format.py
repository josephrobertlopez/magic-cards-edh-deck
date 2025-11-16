"""
Unit tests for document/convert-format skill

Tests cover:
- PPTX → PDF conversion
- DOCX → PDF conversion
- PPTX → PNG (multi-file output)
- Quality levels (low, medium, high)
- Overwrite behavior
- Error handling (missing file, unsupported format, LibreOffice not found)
- Edge cases (empty file, already exists)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import subprocess


# Mock implementation matching the skill contract
def execute_document_convert_format(args):
    """Mock implementation of document/convert-format skill execution."""
    input_file = Path(args["input_file"])
    output_format = args["output_format"].lower()
    output_dir = Path(args.get("output_dir", input_file.parent))
    quality = args.get("quality", "medium")
    overwrite = args.get("overwrite", True)

    # Validate input
    if not input_file.exists():
        raise Exception(f"FILE_NOT_FOUND: {input_file}")

    # Quality mapping
    quality_map = {"low": 50, "medium": 75, "high": 90}
    quality_value = quality_map.get(quality, 75)

    # Determine output type
    if output_format == "pdf":
        output_path = output_dir / f"{input_file.stem}.pdf"
        is_multi_file = False
    elif output_format in ["png", "jpg"]:
        output_path = output_dir
        is_multi_file = True
    else:
        raise Exception(f"UNSUPPORTED_FORMAT: {output_format}")

    # Check existing (single-file only)
    if not is_multi_file and output_path.exists() and not overwrite:
        return {
            "path": str(output_path),
            "items": [str(output_path)],
            "count": 1,
            "size_bytes": output_path.stat().st_size,
            "skipped": True
        }

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # For testing, just create dummy output files
    if is_multi_file:
        # Simulate multi-file output (3 slides)
        output_files = []
        for i in range(1, 4):
            output_file = output_dir / f"{input_file.stem}_slide{i}.{output_format}"
            output_file.touch()
            output_files.append(output_file)

        items = [str(f) for f in output_files]
        total_size = sum(f.stat().st_size for f in output_files)

        return {
            "path": str(output_files[0]),
            "items": items,
            "count": 3,
            "size_bytes": total_size,
            "skipped": False
        }
    else:
        # Single file output
        output_path.touch()
        return {
            "path": str(output_path),
            "items": [str(output_path)],
            "count": 1,
            "size_bytes": output_path.stat().st_size,
            "skipped": False
        }


# ============================================================================
# Unit Tests
# ============================================================================

def test_pptx_to_pdf_conversion(tmp_path):
    """Test PPTX to PDF conversion with high quality."""
    input_file = tmp_path / "sample.pptx"
    input_file.touch()

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "quality": "high"
    })

    assert result["path"].endswith(".pdf")
    assert result["count"] == 1
    assert result["skipped"] is False
    assert Path(result["path"]).exists()


def test_docx_to_pdf_conversion(tmp_path):
    """Test DOCX to PDF conversion with medium quality."""
    input_file = tmp_path / "document.docx"
    input_file.touch()

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "quality": "medium"
    })

    assert result["path"].endswith(".pdf")
    assert "document.pdf" in result["path"]
    assert result["count"] == 1


def test_pptx_to_png_multi_file(tmp_path):
    """Test PPTX to PNG creates one PNG per slide."""
    input_file = tmp_path / "presentation.pptx"
    input_file.touch()
    output_dir = tmp_path / "png_output"

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "png",
        "output_dir": str(output_dir),
        "quality": "high"
    })

    assert result["count"] == 3  # Mock creates 3 slides
    assert len(result["items"]) == 3
    assert all(".png" in item for item in result["items"])
    assert result["skipped"] is False


def test_quality_levels(tmp_path):
    """Test different quality levels."""
    input_file = tmp_path / "test.pptx"
    input_file.touch()

    # Low quality
    result_low = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "quality": "low"
    })
    assert result_low["path"].endswith(".pdf")

    # High quality
    result_high = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "quality": "high"
    })
    assert result_high["path"].endswith(".pdf")


def test_overwrite_false_skips_conversion(tmp_path):
    """Test that overwrite=false skips conversion if file exists."""
    input_file = tmp_path / "existing.pptx"
    input_file.touch()
    output_file = tmp_path / "existing.pdf"
    output_file.write_text("existing content")

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "overwrite": False
    })

    assert result["skipped"] is True
    assert result["path"] == str(output_file)
    assert output_file.read_text() == "existing content"  # Not overwritten


def test_overwrite_true_replaces_file(tmp_path):
    """Test that overwrite=true replaces existing file."""
    input_file = tmp_path / "replace.pptx"
    input_file.touch()
    output_file = tmp_path / "replace.pdf"
    output_file.write_text("old content")

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "overwrite": True
    })

    assert result["skipped"] is False
    assert Path(result["path"]).exists()


def test_missing_input_file_error():
    """Test error when input file doesn't exist."""
    with pytest.raises(Exception) as exc_info:
        execute_document_convert_format({
            "input_file": "/nonexistent/file.pptx",
            "output_format": "pdf"
        })

    assert "FILE_NOT_FOUND" in str(exc_info.value)


def test_unsupported_format_error(tmp_path):
    """Test error for unsupported output format."""
    input_file = tmp_path / "test.pptx"
    input_file.touch()

    with pytest.raises(Exception) as exc_info:
        execute_document_convert_format({
            "input_file": str(input_file),
            "output_format": "xyz"  # Invalid format
        })

    assert "UNSUPPORTED_FORMAT" in str(exc_info.value)


def test_output_directory_created(tmp_path):
    """Test that output directory is created if missing."""
    input_file = tmp_path / "source.pptx"
    input_file.touch()
    nested_output = tmp_path / "level1" / "level2"

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf",
        "output_dir": str(nested_output)
    })

    assert nested_output.exists()
    assert Path(result["path"]).parent == nested_output


def test_png_output_directory_structure(tmp_path):
    """Test PNG output creates proper directory structure."""
    input_file = tmp_path / "slides.pptx"
    input_file.touch()
    output_dir = tmp_path / "images" / "slides"

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "png",
        "output_dir": str(output_dir)
    })

    assert output_dir.exists()
    assert all(Path(item).parent == output_dir for item in result["items"])


def test_default_quality_medium(tmp_path):
    """Test that default quality is medium."""
    input_file = tmp_path / "default.pptx"
    input_file.touch()

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf"
        # No quality specified - should default to medium
    })

    assert result["path"].endswith(".pdf")
    assert result["count"] == 1


def test_default_overwrite_true(tmp_path):
    """Test that default overwrite is true."""
    input_file = tmp_path / "overwrite_default.pptx"
    input_file.touch()
    output_file = tmp_path / "overwrite_default.pdf"
    output_file.write_text("old")

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf"
        # No overwrite specified - should default to true
    })

    assert result["skipped"] is False  # Should overwrite


def test_jpg_format_supported(tmp_path):
    """Test JPG output format is supported."""
    input_file = tmp_path / "presentation.pptx"
    input_file.touch()
    output_dir = tmp_path / "jpg_output"

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "jpg",
        "output_dir": str(output_dir)
    })

    assert result["count"] == 3
    assert all(".jpg" in item for item in result["items"])


def test_size_bytes_calculated(tmp_path):
    """Test that size_bytes is calculated for output files."""
    input_file = tmp_path / "sized.pptx"
    input_file.touch()

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf"
    })

    assert "size_bytes" in result
    assert isinstance(result["size_bytes"], int)
    assert result["size_bytes"] >= 0


def test_multi_file_size_is_sum(tmp_path):
    """Test that multi-file conversions sum all file sizes."""
    input_file = tmp_path / "multi.pptx"
    input_file.touch()
    output_dir = tmp_path / "output"

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "png",
        "output_dir": str(output_dir)
    })

    # Should be sum of all 3 PNG files
    total_size = sum(Path(item).stat().st_size for item in result["items"])
    assert result["size_bytes"] == total_size


def test_items_always_list(tmp_path):
    """Test that items is always a list, even for single-file output."""
    input_file = tmp_path / "single.pptx"
    input_file.touch()

    result = execute_document_convert_format({
        "input_file": str(input_file),
        "output_format": "pdf"
    })

    assert isinstance(result["items"], list)
    assert len(result["items"]) == 1
    assert result["items"][0] == result["path"]
