"""Claude Code CLI agent for problem generation."""

import shutil
import json
from pathlib import Path

from .base import BaseAgent
from ..models import AgentResult


class ClaudeAgent(BaseAgent):
    """Uses the Claude Code CLI to generate problem explanations."""

    name = "claude"

    def is_available(self) -> bool:
        """Check if claude CLI is installed."""
        return shutil.which("claude") is not None

    def generate(
        self,
        problem_file: Path,
        instruction_file: Path,
        output_file: Path,
        timeout_seconds: float = 600,
    ) -> AgentResult:
        """Invoke claude CLI with the problem and instructions."""
        problem_file = Path(problem_file).resolve()
        instruction_file = Path(instruction_file).resolve()
        output_file = Path(output_file).resolve()

        # Read problem JSON for inlining as fallback
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

        # Build prompt: instructions + problem data + output requirement
        prompt = f"""{instructions}

## Problem to solve

Problem file: {problem_file}
Output file: {output_file}

If you cannot read the file above, use this problem data instead:

```json
{json.dumps(problem_data, indent=2)}
```

## Output requirement

Write exactly one HTML file to: {output_file}

Do not write to any other file.
Do not modify index.html, app.js, problems.json, or anything in the generator/ directory.
Do not interact with the database.

Output the HTML now:
"""

        # Run claude CLI
        exit_code, stdout, stderr, duration = self._run_subprocess(
            ["claude", "-p"],
            input_text=prompt,
            timeout=timeout_seconds,
        )

        # Check completion
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
