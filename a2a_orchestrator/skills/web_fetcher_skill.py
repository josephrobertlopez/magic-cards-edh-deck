"""WebFetcher skill wrapper for A2A orchestration."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'a2a_orchestrator' / 'vendor'))

from mcp_a2a_server import Skill, MessageType, A2AMessage


class WebFetcherSkill(Skill):
    """Skill wrapper for fetching web pages."""

    def __init__(self, skill_name: str = "web-fetcher"):
        super().__init__(skill_name, "Fetch web pages and save HTML")
        self.script_path = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "data" / "fetch-web-page.py"

    async def process_request(self, request_message: A2AMessage) -> A2AMessage:
        """Process web fetch request."""
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
                    timeout=60.0
                )
                result_returncode = process.returncode
                result_stdout = stdout.decode('utf-8') if stdout else ""
                result_stderr = stderr.decode('utf-8') if stderr else ""
            except asyncio.TimeoutError:
                process.kill()
                return self.create_error_response(
                    original_message=request_message,
                    error="Skill execution timeout (60 seconds exceeded)"
                )

            if result_returncode == 0:
                try:
                    lines = result_stdout.strip().split('\n')
                    for line in reversed(lines):
                        if line.strip().startswith('{'):
                            output_data = json.loads(line)
                            return self.create_response(
                                original_message=request_message,
                                result=output_data
                            )
                    return self.create_error_response(
                        original_message=request_message,
                        error="No JSON output found"
                    )
                except json.JSONDecodeError as e:
                    return self.create_error_response(
                        original_message=request_message,
                        error=f"Failed to parse output: {str(e)}"
                    )
            else:
                return self.create_error_response(
                    original_message=request_message,
                    error=f"Subprocess failed: {result_stderr}"
                )

        except Exception as e:
            return self.create_error_response(
                original_message=request_message,
                error=f"Unexpected error: {str(e)}"
            )

    def _build_command(self, payload: Dict[str, Any]) -> list[str]:
        """Build subprocess command from payload."""
        url = payload.get("url", "")
        output_dir = payload.get("output_dir", ".claude/downloads")
        
        return [
            "python3",
            str(self.script_path),
            url,
            output_dir
        ]
