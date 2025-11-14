"""
End-to-end tests for full proxy generation pipeline

Tests cover:
- Complete ETL workflow: decklist → images → PPTX → PDF
- Real external API calls (Scryfall)
- Real LibreOffice PDF conversion
- Artifact verification at each stage
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from a2a_orchestrator.orchestrator import YAMLWorkflowOrchestrator, load_yaml_workflow


# --- Fixtures ---

@pytest.fixture
def temp_output_dir():
    """Create temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def minimal_decklist():
    """Create minimal 3-card decklist for fast E2E testing"""
    content = """Forest
Island
Mountain
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(content)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def full_pipeline_workflow(temp_output_dir):
    """Create full pipeline workflow YAML"""
    workflow_content = f"""name: e2e-test-pipeline
description: End-to-end test workflow (3 cards)

steps:
  - name: extract-cards
    skill: data/fetch-from-api
    input:
      decklist_path: ${{input.decklist_path}}
      output_dir: {temp_output_dir}/images
      manifest_path: {temp_output_dir}/manifest.json
    output_var: manifest_path

  - name: generate-presentation
    skill: presentation/place-images-in-pptx
    input:
      manifest: {temp_output_dir}/manifest.json
      template: ${{input.template_path}}
      output: {temp_output_dir}/output.pptx
    output_var: pptx_path

  - name: convert-to-pdf
    skill: pdf/convert-to-pdf
    input:
      source: {temp_output_dir}/output.pptx
      output_dir: {temp_output_dir}
    output_var: pdf_path
    condition: ${{input.no_pdf}} == false

output:
  manifest: {temp_output_dir}/manifest.json
  pptx: {temp_output_dir}/output.pptx
  pdf: {temp_output_dir}/output.pdf
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        f.write(workflow_content)
        yield f.name
    os.unlink(f.name)


# --- E2E Tests ---

@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_pipeline(full_pipeline_workflow, minimal_decklist, temp_output_dir):
    """
    E2E test: Complete pipeline from decklist to PDF

    Stages:
    1. Fetch 3 card images from Scryfall API
    2. Generate PPTX from template
    3. Convert PPTX to PDF via LibreOffice

    Note: Marked @pytest.mark.slow due to:
    - External API calls (~3 seconds with rate limiting)
    - LibreOffice conversion (~5-10 seconds)
    """
    # Check prerequisites
    template_path = "template_2v6h_FIXED.pptx"
    if not os.path.exists(template_path):
        pytest.skip("Template file not found")

    # Load workflow
    workflow = load_yaml_workflow(full_pipeline_workflow)

    # Create orchestrator
    skills_dir = Path(".claude/skills")
    orchestrator = YAMLWorkflowOrchestrator(skills_dir)

    # Execute full pipeline
    inputs = {
        "decklist_path": minimal_decklist,
        "template_path": template_path,
        "no_pdf": False
    }

    result = await orchestrator.execute_workflow(workflow, inputs)

    # Verify Stage 1: Images fetched
    manifest_path = os.path.join(temp_output_dir, "manifest.json")
    assert os.path.exists(manifest_path), "Manifest not created"

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    assert manifest["successful"] >= 3, f"Expected 3+ cards, got {manifest['successful']}"

    images_dir = os.path.join(temp_output_dir, "images")
    assert os.path.exists(images_dir), "Images directory not created"

    images = [f for f in os.listdir(images_dir) if f.endswith('.jpg')]
    assert len(images) >= 3, f"Expected 3+ images, got {len(images)}"

    # Verify Stage 2: PPTX generated
    pptx_path = os.path.join(temp_output_dir, "output.pptx")
    assert os.path.exists(pptx_path), "PPTX not created"

    # Verify PPTX is valid
    from pptx import Presentation
    prs = Presentation(pptx_path)
    assert len(prs.slides) > 0, "PPTX has no slides"

    # Verify Stage 3: PDF converted
    pdf_path = os.path.join(temp_output_dir, "output.pdf")

    # PDF conversion requires LibreOffice - skip if not available
    if not os.path.exists(pdf_path):
        # Check if LibreOffice is available
        import subprocess
        try:
            subprocess.run(["soffice", "--version"], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("LibreOffice not available for PDF conversion")

    assert os.path.exists(pdf_path), "PDF not created"

    # Verify PDF is valid (basic check)
    with open(pdf_path, 'rb') as f:
        pdf_header = f.read(4)
    assert pdf_header == b'%PDF', "PDF file is invalid"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_pipeline_skip_pdf(full_pipeline_workflow, minimal_decklist, temp_output_dir):
    """Test pipeline with PDF conversion skipped via condition"""
    template_path = "template_2v6h_FIXED.pptx"
    if not os.path.exists(template_path):
        pytest.skip("Template file not found")

    workflow = load_yaml_workflow(full_pipeline_workflow)
    skills_dir = Path(".claude/skills")
    orchestrator = YAMLWorkflowOrchestrator(skills_dir)

    inputs = {
        "decklist_path": minimal_decklist,
        "template_path": template_path,
        "no_pdf": True
    }

    result = await orchestrator.execute_workflow(workflow, inputs)

    # PPTX should exist
    pptx_path = os.path.join(temp_output_dir, "output.pptx")
    assert os.path.exists(pptx_path)

    # PDF should NOT exist (step skipped)
    pdf_path = os.path.join(temp_output_dir, "output.pdf")
    assert not os.path.exists(pdf_path), "PDF should not be created when no_pdf=true"
