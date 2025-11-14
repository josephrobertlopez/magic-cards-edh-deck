"""
Integration tests for skill CLI invocation

Tests cover:
- Subprocess invocation of skills
- JSON output parsing
- File artifact creation (images, PPTX, PDF)
"""

import pytest
import json
import subprocess
import tempfile
import os
from pathlib import Path


# --- Fixtures ---

@pytest.fixture
def temp_output_dir():
    """Create temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_decklist():
    """Create minimal test decklist with 3 cards"""
    content = """Forest
Island
Mountain
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(content)
        yield f.name
    os.unlink(f.name)


# --- Integration Tests ---

def test_data_fetcher_cli(test_decklist, temp_output_dir):
    """Test data/fetch-from-api.py skill CLI invocation"""
    manifest_path = os.path.join(temp_output_dir, "manifest.json")

    cmd = [
        "python3",
        ".claude/skills/data/fetch-from-api.py",
        "--decklist", test_decklist,
        "--output-dir", temp_output_dir,
        "--manifest", manifest_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # Verify success (print stderr for debugging failures)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        print(f"STDOUT: {result.stdout}")
    assert result.returncode == 0

    # Parse JSON output from stdout (handles pretty-printed JSON)
    output_text = result.stdout.strip()
    # Extract JSON object from output (may span multiple lines)
    json_start = output_text.find('{')
    if json_start >= 0:
        json_text = output_text[json_start:]
        json_output = json.loads(json_text)
    else:
        json_output = None

    assert json_output is not None
    assert json_output["status"] == "success"
    assert json_output["manifest_path"] == manifest_path

    # Verify manifest created
    assert os.path.exists(manifest_path)

    # Verify manifest contents
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    assert manifest["successful"] >= 3  # At least 3 cards fetched
    assert len(manifest["items"]) >= 3


@pytest.mark.slow
def test_document_generator_cli(temp_output_dir):
    """Test presentation/place-images-in-pptx.py skill CLI invocation"""
    # Create minimal manifest
    manifest_data = {
        "timestamp": "2025-01-01T00:00:00",
        "source_file": "test.txt",
        "total_resources": 1,
        "successful": 1,
        "failed": 0,
        "items": [
            {
                "name": "Forest",
                "path": "images/Forest.jpg",  # Use existing image
                "status": "success"
            }
        ]
    }
    manifest_path = os.path.join(temp_output_dir, "test_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f)

    output_pptx = os.path.join(temp_output_dir, "output.pptx")

    cmd = [
        "python3",
        ".claude/skills/presentation/place-images-in-pptx.py",
        "--manifest", manifest_path,
        "--template", "template_2v6h_FIXED.pptx",
        "--output", output_pptx
    ]

    # Only run if template exists
    if not os.path.exists("template_2v6h_FIXED.pptx"):
        pytest.skip("Template file not found")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # Verify success
    assert result.returncode == 0

    # Parse JSON output (handles pretty-printed JSON)
    output_text = result.stdout.strip()
    json_start = output_text.find('{')
    if json_start >= 0:
        json_text = output_text[json_start:]
        json_output = json.loads(json_text)
    else:
        json_output = None

    assert json_output is not None
    assert json_output["status"] == "success"

    # Verify PPTX created
    assert os.path.exists(output_pptx)


@pytest.mark.slow
def test_pdf_converter_cli(temp_output_dir):
    """Test pdf/convert-to-pdf.py skill CLI invocation"""
    # Create dummy PPTX (or skip if template doesn't exist)
    if not os.path.exists("template_2v6h_FIXED.pptx"):
        pytest.skip("Template file not found")

    from pptx import Presentation
    prs = Presentation("template_2v6h_FIXED.pptx")
    test_pptx = os.path.join(temp_output_dir, "test.pptx")
    prs.save(test_pptx)

    cmd = [
        "python3",
        ".claude/skills/pdf/convert-to-pdf.py",
        "--source", test_pptx,
        "--output-dir", temp_output_dir
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # PDF conversion requires LibreOffice - may not be available in CI
    if result.returncode != 0 and "soffice" in result.stderr:
        pytest.skip("LibreOffice not available")

    assert result.returncode == 0

    # Parse JSON output (handles pretty-printed JSON)
    output_text = result.stdout.strip()
    json_start = output_text.find('{')
    if json_start >= 0:
        json_text = output_text[json_start:]
        json_output = json.loads(json_text)
    else:
        json_output = None

    assert json_output is not None
    assert json_output["status"] == "success"

    # Verify PDF created
    pdf_path = os.path.join(temp_output_dir, "test.pdf")
    assert os.path.exists(pdf_path)
