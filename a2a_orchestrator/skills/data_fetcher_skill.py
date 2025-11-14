"""DataFetcher skill class wrapper for A2A orchestration."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'a2a_orchestrator' / 'vendor'))

from mcp_a2a_server import Skill, MessageType, A2AMessage


class DataFetcherSkill(Skill):
    """
    Skill wrapper for fetching resources from APIs.

    Wraps .claude/skills/data/fetch-from-api.py subprocess execution.
    """

    def __init__(self, skill_name: str = "data-fetcher"):
        """Initialize DataFetcher skill."""
        super().__init__(skill_name, "Fetch resources from APIs with rate limiting and caching")
        self.script_path = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "data" / "fetch-from-api.py"

    async def process_request(self, request_message: A2AMessage) -> A2AMessage:
        """
        Process fetch request by invoking subprocess.

        Args:
            request_message: A2A REQUEST message with payload:
                - decklist_path: Path to decklist file
                - output_dir: Directory for downloaded resources
                - manifest_path: Optional manifest output path

        Returns:
            A2A RESPONSE message with result or ERROR message
        """
        try:
            # Build subprocess command
            command = self._build_command(request_message.payload)

            # Execute subprocess asynchronously with timeout
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=180.0  # 3 minutes for large decklists (77 cards * 0.1s + network = ~10-20s typical, 180s safe)
                )
                result_returncode = process.returncode
                result_stdout = stdout.decode('utf-8') if stdout else ""
                result_stderr = stderr.decode('utf-8') if stderr else ""
            except asyncio.TimeoutError:
                process.kill()
                return self.create_error_response(
                    original_message=request_message,
                    error="Skill execution timeout (180 seconds exceeded)"
                )

            # Parse output
            if result_returncode == 0:
                # Parse JSON from stdout (aggregate all JSON lines)
                try:
                    output_lines = result_stdout.strip().split('\n')
                    json_lines = []
                    in_json = False
                    current_json = []

                    for line in output_lines:
                        stripped = line.strip()
                        if stripped.startswith('{'):
                            in_json = True
                            current_json = [line]
                        elif in_json:
                            current_json.append(line)
                            if stripped.endswith('}'):
                                json_lines.append('\n'.join(current_json))
                                in_json = False

                    if json_lines:
                        # Parse the last complete JSON object
                        output_data = json.loads(json_lines[-1])
                    else:
                        output_data = {"status": "success"}

                    return self.create_response(
                        original_message=request_message,
                        result=output_data
                    )
                except json.JSONDecodeError as e:
                    return self.create_error_response(
                        original_message=request_message,
                        error=f"Failed to parse skill output as JSON: {str(e)}"
                    )
            else:
                error_info = self._parse_error(result_returncode, result_stdout, result_stderr)
                return self.create_error_response(
                    original_message=request_message,
                    error=error_info['error']
                )

        except Exception as e:
            return self.create_error_response(
                original_message=request_message,
                error=f"Unexpected error: {str(e)}"
            )

    def _build_command(self, payload: Dict[str, Any]) -> list[str]:
        """
        Build subprocess command from payload.

        Args:
            payload: Request payload with decklist_path, output_dir, manifest_path,
                     api_url, schema, size_hints (all required except manifest_path)

        Returns:
            List of command arguments
        """
        command = [
            "python3",
            str(self.script_path),
            "--decklist", payload["decklist_path"],
            "--output-dir", payload.get("output_dir", "images")
        ]

        if "manifest_path" in payload:
            command.extend(["--manifest", payload["manifest_path"]])

        # Required parameters (must be present or use defaults)
        if "api_url" in payload:
            command.extend(["--api-url", payload["api_url"]])
        else:
            # Default to Scryfall API for MTG cards
            command.extend(["--api-url", "https://api.scryfall.com/cards/named?fuzzy={identifier}"])

        if "schema" in payload:
            import json
            schema_json = json.dumps(payload["schema"])
            command.extend(["--schema", schema_json])
        else:
            # Default schema for Scryfall API
            import json
            default_schema = {"image_url": "image_uris.png", "name": "name"}
            command.extend(["--schema", json.dumps(default_schema)])

        if "size_hints" in payload:
            import json
            size_hints_json = json.dumps(payload["size_hints"])
            command.extend(["--size-hints", size_hints_json])
        else:
            # Default size hints for MTG proxy printing
            import json
            default_size_hints = {
                "width_px": 750,
                "height_px": 1050,
                "dpi": 300,
                "source": "provider"
            }
            command.extend(["--size-hints", json.dumps(default_size_hints)])

        return command

    def _parse_error(self, returncode: int, stdout: str, stderr: str) -> Dict[str, Any]:
        """
        Parse error from subprocess result.

        Args:
            returncode: Subprocess exit code
            stdout: Subprocess stdout
            stderr: Subprocess stderr

        Returns:
            Dictionary with error message and context
        """
        try:
            error_data = json.loads(stderr)
            return error_data
        except json.JSONDecodeError:
            return {
                "error": f"Subprocess failed with exit code {returncode}",
                "context": {"stderr": stderr, "stdout": stdout}
            }
