"""HTMLExtractor skill wrapper for A2A orchestration."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'a2a_orchestrator' / 'vendor'))

from mcp_a2a_server import Skill, MessageType, A2AMessage


class HTMLExtractorSkill(Skill):
    """Skill wrapper for extracting card names from HTML."""

    def __init__(self, skill_name: str = "html-extractor"):
        super().__init__(skill_name, "Extract card names from HTML files")
        self.script_path = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "data" / "extract-cards-from-html.py"

    async def process_request(self, request_message: A2AMessage) -> A2AMessage:
        """Process HTML extraction request."""
        try:
            command = self._build_command(request_message.payload)

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0
                )
                result_returncode = process.returncode
                result_stdout = stdout.decode('utf-8') if stdout else ""
            except asyncio.TimeoutError:
                process.kill()
                return self.create_error_response(
                    original_message=request_message,
                    error="Skill execution timeout (30 seconds exceeded)"
                )

            if result_returncode == 0:
                try:
                    output_data = json.loads(result_stdout.strip())
                    return self.create_response(
                        original_message=request_message,
                        result=output_data
                    )
                except json.JSONDecodeError as e:
                    return self.create_error_response(
                        original_message=request_message,
                        error=f"Failed to parse output: {str(e)}"
                    )
            else:
                return self.create_error_response(
                    original_message=request_message,
                    error=f"Subprocess failed with exit code {result_returncode}"
                )

        except Exception as e:
            return self.create_error_response(
                original_message=request_message,
                error=f"Unexpected error: {str(e)}"
            )

    def _build_command(self, payload: Dict[str, Any]) -> list[str]:
        """Build subprocess command from payload."""
        html_file = payload.get("html_file", "")
        output_file = payload.get("output_file", "decklist.txt")
        max_cards = payload.get("max_cards", 100)
        
        return [
            "python3",
            str(self.script_path),
            html_file,
            output_file,
            str(max_cards)
        ]
