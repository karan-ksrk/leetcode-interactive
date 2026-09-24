"""Generic configurable CLI agent for problem generation."""

import shutil
import json
import shlex
from pathlib import Path
from typing import Optional

from .base import BaseAgent
from ..models import AgentResult


class GenericAgent(BaseAgent):
    """Uses a configurable command template to generate problems."""

    def __init__(self, name: str = "generic", command_template: str = ""):
        """Initialize with a command template.

        Template placeholders:
        - {problem_file}: path to problem JSON
        - {instruction_file}: path to instruction markdown
        - {output_file}: path where HTML should be written

        Example:
        "my-ai-tool --input {problem_file} --instructions {instruction_file} --output {output_file}"
        """
        self.name = name
        self.command_template = command_template

    def is_available(self) -> bool:
        """Check if the command's executable is installed."""
        if not self.command_template:
            return False

        # Extract first token (executable name)
        parts = shlex.split(self.command_template)
        if not parts:
            return False

        exe = parts[0]
        return shutil.which(exe) is not None

    def generate(
        self,
        problem_file: Path,
        instruction_file: Path,
        output_file: Path,
        timeout_seconds: float = 600,
    ) -> AgentResult:
        """Invoke the generic command template."""
        problem_file = Path(problem_file).resolve()
        instruction_file = Path(instruction_file).resolve()
        output_file = Path(output_file).resolve()

        # Read problem JSON
        try:
            with open(problem_file, "r", encoding="utf-8") as f:
                problem_data = json.load(f)
        except Exception as e:
            return AgentResult(
                success=False,
                output_file=output_file,
                duration_seconds=0,
                stdout="",
                stderr=f"Failed to read problem file: {e}",
                error=str(e),
            )

        # Format command with paths
        try:
            command = self.command_template.format(
                problem_file=str(problem_file),
                instruction_file=str(instruction_file),
                output_file=str(output_file),
            )
        except KeyError as e:
            return AgentResult(
                success=False,
                output_file=output_file,
                duration_seconds=0,
                stdout="",
                stderr=f"Command template has missing placeholder: {e}",
                error=str(e),
            )

        # Run the command
        exit_code, stdout, stderr, duration = self._run_subprocess(
            command,
            timeout=timeout_seconds,
        )

        success = (
            exit_code == 0
            and output_file.exists()
            and output_file.stat().st_size > 0
        )

        return AgentResult(
            success=success,
            output_file=output_file,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            error=None if success else f"Exit code {exit_code}",
        )
