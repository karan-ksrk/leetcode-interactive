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

        # Build prompt: instructions + problem data
        # Don't mention output file to avoid Claude asking for write approval
        prompt = f"""{instructions}

## Problem Data

```json
{json.dumps(problem_data, indent=2)}
```

Output the HTML now:
"""

        # Run claude CLI
        exit_code, stdout, stderr, duration = self._run_subprocess(
            ["claude", "-p"],
            input_text=prompt,
            timeout=timeout_seconds,
        )

        # Extract HTML from stdout
        html_content = None

        # Try to find ```html code block
        import re
        html_block_match = re.search(r'```html\s*(.*?)\s*```', stdout, re.DOTALL)
        if html_block_match:
            html_content = html_block_match.group(1).strip()
        else:
            # Fall back to looking for <!DOCTYPE or <html tag
            if '<!DOCTYPE' in stdout or '<html' in stdout:
                start_idx = stdout.find('<!DOCTYPE')
                if start_idx == -1:
                    start_idx = stdout.find('<html')
                if start_idx != -1:
                    # Take from the HTML tag to the end (or until </html>)
                    html_part = stdout[start_idx:]
                    end_idx = html_part.find('</html>')
                    if end_idx != -1:
                        html_content = html_part[:end_idx+7]
                    else:
                        # If no closing tag, just take everything after the opening tag
                        html_content = html_part

        # Write extracted HTML to output file
        success = False
        if html_content:
            try:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                success = output_file.exists() and output_file.stat().st_size > 0
            except Exception as e:
                stderr = f"Failed to write output file: {e}"

        return AgentResult(
            success=success,
            output_file=output_file,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            error=None if success else (f"Exit code {exit_code}" if not html_content else "Failed to write file"),
        )
