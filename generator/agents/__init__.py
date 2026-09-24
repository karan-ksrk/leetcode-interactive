"""Agent implementations for problem HTML generation."""

from .base import BaseAgent
from .claude import ClaudeAgent
from .codex import CodexAgent
from .gemini import GeminiAgent
from .generic import GenericAgent

__all__ = [
    "BaseAgent",
    "ClaudeAgent",
    "CodexAgent",
    "GeminiAgent",
    "GenericAgent",
]


def get_agent(name: str, **kwargs) -> BaseAgent:
    """Factory to get an agent by name."""
    agents_map = {
        "claude": ClaudeAgent,
        "codex": CodexAgent,
        "gemini": GeminiAgent,
        "generic": GenericAgent,
    }
    agent_class = agents_map.get(name.lower())
    if not agent_class:
        raise ValueError(f"Unknown agent: {name}")
    return agent_class(**kwargs)
