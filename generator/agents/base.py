"""Base agent abstraction for problem generation."""

from abc import ABC, abstractmethod
from pathlib import Path
import subprocess
import time
from typing import Tuple

from ..models import AgentResult


class BaseAgent(ABC):
    """Abstract base class for AI CLI agents."""

    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the agent's CLI is installed/available."""
        pass

    @abstractmethod
    def generate(
        self,
        problem_file: Path,
        instruction_file: Path,
        output_file: Path,
        timeout_seconds: float = 600,
    ) -> AgentResult:
        """Generate HTML for one problem.

        Args:
            problem_file: Path to problem JSON (data/fetched/<id>-<slug>.json)
            instruction_file: Path to instruction markdown (generator/prompts/leetcode-animator.md)
            output_file: Path where HTML should be written (data/staging/<id>-<slug>.html)
            timeout_seconds: Max time to wait for agent completion

        Returns:
            AgentResult with success flag, output_file path, duration, stdout, stderr, error

        Must NOT raise exceptions for expected failure modes (CLI missing, timeout, nonzero exit).
        May raise only for programmer errors.
        Must NOT modify any files except output_file.
        """
        pass

    @staticmethod
    def _run_subprocess(
        args,
        cwd: Path = None,
        timeout: float = 600,
        input_text: str = None,
    ) -> Tuple[int, str, str, float]:
        """Run a subprocess and capture output.

        Args:
            args: Command as string or list
            cwd: Working directory
            timeout: Timeout in seconds
            input_text: Text to pipe to stdin

        Returns:
            (exit_code, stdout, stderr, duration_seconds)
        """
        start = time.time()
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                input=input_text,
                shell=isinstance(args, str),
            )
            duration = time.time() - start
            return result.returncode, result.stdout, result.stderr, duration
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return -1, "", f"Timeout after {timeout}s", duration
        except Exception as e:
            duration = time.time() - start
            return -1, "", str(e), duration
