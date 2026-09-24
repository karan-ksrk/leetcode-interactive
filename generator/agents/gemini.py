"""Google Gemini CLI agent for problem generation.

NOTE: Exact CLI flags (--yolo vs other approval mode) are best-effort and
should be verified against locally installed gemini CLI before first use.
Update this file with confirmed flags.
"""

import shutil
import json
from pathlib import Path

from .base import BaseAgent
from ..models import AgentResult


class GeminiAgent(BaseAgent):
    """Uses the Google Gemini CLI to generate problem explanations."""

    name = "gemini"

    def is_available(self) -> bool:
        """Check if gemini CLI is installed."""
        return shutil.which("gemini") is not None

    def generate(
        self,
        problem_file: Path,
        instruction_file: Path,
        output_file: Path,
        timeout_seconds: float = 600,
    ) -> AgentResult:
        """Invoke gemini CLI with the problem and instructions."""
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

        # Read instruction file
        try:
            with open(instruction_file, "r", encoding="utf-8") as f:
                instructions = f.read()
        except Exception as e:
            return AgentResult(
                success=False,
                output_file=output_file,
                duration_seconds=0,
                stdout="",
                stderr=f"Failed to read instruction file: {e}",
                error=str(e),
            )

        # Build prompt
        prompt = f"""{instructions}

## Problem to solve

```json
{json.dumps(problem_data, indent=2)}
```

## Output requirement

Write exactly one HTML file to: {output_file}

Do not write to any other file.
"""

        # Run gemini CLI (best-effort command structure)
        # TODO: Verify exact flags against installed gemini --help
        exit_code, stdout, stderr, duration = self._run_subprocess(
            ["gemini", "-p", "--yolo"],
            input_text=prompt,
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
