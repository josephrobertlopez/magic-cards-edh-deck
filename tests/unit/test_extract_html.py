"""Unit tests for extract-content-from-html.py skill."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = PROJECT_ROOT / ".claude/skills/data/extract-content-from-html.py"
FIXTURES = PROJECT_ROOT / "tests/fixtures/html_samples"


def run_extractor(html_file, extract_type, selector, output_file=None):
    """Run extractor and return parsed JSON output."""
    cmd = [
        sys.executable,
        str(EXTRACTOR),
        "--content-file", str(html_file),
        "--extract-type", extract_type,
        "--selector", selector
    ]
    if output_file:
        cmd.extend(["--output", str(output_file)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse A2A JSON output (multiline formatted)
    return json.loads(result.stdout), result.returncode


class TestListExtraction:
    """Test list extraction mode."""

    def test_mtg_decklist_extraction(self):
        """Extract MTG cards from decklist HTML."""
        output, code = run_extractor(
            FIXTURES / "mtg_decklist.html",
            "list",
            ".card-item"
        )

        assert code == 0
        assert output["status"] == "success"
        assert output["result"]["count"] == 8
        assert "The Gitrog Monster" in output["result"]["items"]
        assert "Forest" in output["result"]["items"]

    def test_pokemon_list_extraction(self):
        """Extract Pokemon from list HTML."""
        output, code = run_extractor(
            FIXTURES / "pokemon_list.html",
            "list",
            ".pokemon-name"
        )

        assert code == 0
        assert output["status"] == "success"
        assert output["result"]["count"] == 6
        assert "Pikachu" in output["result"]["items"]
        assert "Charizard" in output["result"]["items"]


class TestTableExtraction:
    """Test table extraction mode."""

    def test_recipe_table_extraction(self):
        """Extract recipe ingredients table."""
        output, code = run_extractor(
            FIXTURES / "recipe_table.html",
            "table",
            "table.ingredients"
        )

        assert code == 0
        assert output["status"] == "success"
        assert output["result"]["count"] == 4

        rows = output["result"]["rows"]
        assert rows[0]["Ingredient"] == "Flour"
        assert rows[0]["Amount"] == "2 cups"
        assert rows[2]["Ingredient"] == "Cocoa powder"


class TestOutputFiles:
    """Test output file generation."""

    def test_list_output_file(self, tmp_path):
        """Verify list extraction writes to file."""
        output_file = tmp_path / "cards.txt"

        output, code = run_extractor(
            FIXTURES / "mtg_decklist.html",
            "list",
            ".card-item",
            output_file
        )

        assert code == 0
        assert output_file.exists()

        content = output_file.read_text()
        lines = content.strip().split('\n')
        assert len(lines) == 8
        assert "The Gitrog Monster" in lines


class TestErrorHandling:
    """Test error conditions."""

    def test_missing_selector(self):
        """Extract with non-existent selector returns empty."""
        output, code = run_extractor(
            FIXTURES / "mtg_decklist.html",
            "list",
            ".nonexistent-class"
        )

        assert code == 0
        assert output["status"] == "success"
        assert output["result"]["count"] == 0
        assert output["result"]["items"] == []

    def test_missing_file(self):
        """Non-existent file raises error."""
        cmd = [
            sys.executable,
            str(EXTRACTOR),
            "--content-file", "/tmp/nonexistent.html",
            "--extract-type", "list",
            "--selector", ".test"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0
