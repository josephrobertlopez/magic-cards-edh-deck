"""Integration test: HTML → Extracted Decklist workflow."""
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = PROJECT_ROOT / ".claude/skills/data/extract-content-from-html.py"


def test_end_to_end_mtg_decklist_extraction():
    """
    End-to-end: User copies HTML from browser → Extracts decklist.

    Simulates:
    1. User visits deck site
    2. Right-clicks → "Copy outerHTML"
    3. Saves to file
    4. Runs extractor
    5. Gets clean decklist.txt
    """
    # Simulated HTML from user paste
    user_pasted_html = """
    <div class="deck-view">
        <div class="card-row">1x The Gitrog Monster</div>
        <div class="card-row">1x Grolnok, the Omnivore</div>
        <div class="card-row">1x Frog Tongue</div>
        <div class="card-row">10x Forest</div>
        <div class="card-row">5x Island</div>
        <div class="card-row">1x Command Tower</div>
    </div>
    """

    with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as html_file:
        html_file.write(user_pasted_html)
        html_path = Path(html_file.name)

    with NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as output_file:
        output_path = Path(output_file.name)

    try:
        # Extract cards using CSS selector
        cmd = [
            sys.executable,
            str(EXTRACTOR),
            "--content-file", str(html_path),
            "--extract-type", "list",
            "--selector", ".card-row",
            "--output", str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0, f"Extractor failed: {result.stderr}"

        # Verify decklist.txt contains cards
        decklist = output_path.read_text().strip().split('\n')

        assert len(decklist) == 6
        assert "1x The Gitrog Monster" in decklist
        assert "10x Forest" in decklist
        assert "1x Command Tower" in decklist

    finally:
        html_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def test_programmatic_fetch_then_extract():
    """
    Integration: fetch-content.py → extract-content-from-html.py.

    Workflow:
    1. Fetch HTML from URL (programmatic)
    2. Extract content with CSS selector
    3. Output decklist
    """
    # This test requires fetch-content.py skill
    fetch_skill = PROJECT_ROOT / ".claude/skills/web/fetch-content.py"

    if not fetch_skill.exists():
        pytest.skip("fetch-content.py not available")

    # Simulate fetched HTML content
    fetched_html = """
    <html>
    <body>
        <ul class="pokemon-team">
            <li>Pikachu</li>
            <li>Charizard</li>
            <li>Blastoise</li>
        </ul>
    </body>
    </html>
    """

    with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as html_file:
        html_file.write(fetched_html)
        html_path = Path(html_file.name)

    with NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as output_file:
        output_path = Path(output_file.name)

    try:
        cmd = [
            sys.executable,
            str(EXTRACTOR),
            "--content-file", str(html_path),
            "--extract-type", "list",
            "--selector", "ul.pokemon-team li",
            "--output", str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0

        pokemon_list = output_path.read_text().strip().split('\n')
        assert len(pokemon_list) == 3
        assert "Pikachu" in pokemon_list

    finally:
        html_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
