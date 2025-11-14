"""DocumentGenerator skill class wrapper for A2A orchestration."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'a2a_orchestrator' / 'vendor'))

from mcp_a2a_server import Skill, MessageType, A2AMessage


class DocumentGeneratorSkill(Skill):
    """
    Skill wrapper for generating PowerPoint presentations.

    Wraps .claude/skills/presentation/place-images-in-pptx.py subprocess execution.
    """

    def __init__(self, skill_name: str = "document-generator"):
        """Initialize DocumentGenerator skill."""
        super().__init__(skill_name, "Generate PowerPoint presentations from image manifests")
        self.script_path = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "presentation" / "place-images-in-pptx.py"

    async def process_request(self, request_message: A2AMessage) -> A2AMessage:
        """
        Process generation request by invoking subprocess.

        Args:
            request_message: A2A REQUEST message with payload:
                - manifest_path: Path to manifest JSON
                - template_path: Path to PPTX template
                - output_path: Output PPTX path

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
                    timeout=120.0  # 2 minutes for PPTX generation (image resizing + placement)
                )
                result_returncode = process.returncode
                result_stdout = stdout.decode('utf-8') if stdout else ""
                result_stderr = stderr.decode('utf-8') if stderr else ""
            except asyncio.TimeoutError:
                process.kill()
                return self.create_error_response(
                    original_message=request_message,
                    error="Skill execution timeout (120 seconds exceeded)"
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
            payload: Request payload with manifest_path, template_path, output_path

        Returns:
            List of command arguments
        """
        command = [
            "python3",
            str(self.script_path),
            "--manifest", payload["manifest_path"],
            "--template", payload["template_path"],
            "--output", payload["output_path"]
        ]

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
