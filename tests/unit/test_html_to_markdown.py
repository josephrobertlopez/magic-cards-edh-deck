"""Unit tests for html-to-markdown.py skill."""
import json
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONVERTER = PROJECT_ROOT / ".claude/skills/data/html-to-markdown.py"
FIXTURES = PROJECT_ROOT / "tests/fixtures/html_samples"


def run_converter(html_file, output_file=None, no_links=False, no_images=False):
    """Run HTML to Markdown converter and return parsed JSON output."""
    cmd = [
        sys.executable,
        str(CONVERTER),
        "--content-file", str(html_file)
    ]
    if output_file:
        cmd.extend(["--output", str(output_file)])
    if no_links:
        cmd.append("--no-links")
    if no_images:
        cmd.append("--no-images")

    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout), result.returncode


class TestBasicConversion:
    """Test basic HTML to Markdown conversion."""

    def test_convert_mtg_decklist(self):
        """Convert MTG decklist HTML to Markdown."""
        with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            output, code = run_converter(
                FIXTURES / "mtg_decklist.html",
                output_path
            )

            assert code == 0
            assert output["status"] == "success"
            assert output["markdown_length"] > 0
            assert output["output_file"] == str(output_path)

            # Verify markdown content
            markdown = output_path.read_text()
            assert "## Frog Tribal Commander" in markdown
            assert "The Gitrog Monster" in markdown
            assert "Forest" in markdown

        finally:
            output_path.unlink(missing_ok=True)

    def test_convert_pokemon_list(self):
        """Convert Pokemon list HTML to Markdown."""
        with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            output, code = run_converter(
                FIXTURES / "pokemon_list.html",
                output_path
            )

            assert code == 0
            markdown = output_path.read_text()
            assert "## My Champion Team" in markdown
            assert "Pikachu" in markdown
            assert "Charizard" in markdown

        finally:
            output_path.unlink(missing_ok=True)


class TestOptions:
    """Test conversion options."""

    def test_strip_links(self):
        """Verify --no-links option strips links."""
        html_with_links = """
        <html>
        <body>
            <p>Check out <a href="https://example.com">this site</a></p>
        </body>
        </html>
        """

        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as html_file:
            html_file.write(html_with_links)
            html_path = Path(html_file.name)

        with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            output, code = run_converter(
                html_path,
                output_path,
                no_links=True
            )

            assert code == 0
            markdown = output_path.read_text()
            # Links should be stripped
            assert "https://example.com" not in markdown or "[" not in markdown

        finally:
            html_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def test_preserve_headings(self):
        """Verify heading conversion."""
        html_with_headings = """
        <html>
        <body>
            <h1>Main Title</h1>
            <h2>Subtitle</h2>
            <p>Content here</p>
        </body>
        </html>
        """

        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as html_file:
            html_file.write(html_with_headings)
            html_path = Path(html_file.name)

        with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            output, code = run_converter(html_path, output_path)

            assert code == 0
            markdown = output_path.read_text()
            assert "# Main Title" in markdown
            assert "## Subtitle" in markdown

        finally:
            html_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)


class TestErrorHandling:
    """Test error conditions."""

    def test_missing_file(self):
        """Non-existent file raises error."""
        cmd = [
            sys.executable,
            str(CONVERTER),
            "--content-file", "/tmp/nonexistent.html"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0
        assert "File not found" in result.stderr or "not found" in result.stderr.lower()
