"""Configuration management for LeetCode Interactive generator."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
import yaml
from dotenv import load_dotenv
import os


@dataclass
class GenerationConfig:
    """Generation behavior settings."""
    default_agent: str = "claude"
    default_batch_size: int = 5
    default_parallelism: int = 5


@dataclass
class AgentConfig:
    """Per-agent configuration."""
    enabled: bool = True
    command_template: Optional[str] = None
    timeout_seconds: int = 600


@dataclass
class AppConfig:
    """Top-level application configuration."""
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    db_path: Path = Path("database/leetcode.db")
    leetcode_session_cookie: Optional[str] = None
    leetcode_csrf_token: Optional[str] = None


def load_config(config_path: Path = Path("config.yaml")) -> AppConfig:
    """Load configuration from YAML + environment variables."""
    load_dotenv()

    app_config = AppConfig()

    # Load from YAML if it exists
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

        # Generation config
        gen_data = yaml_data.get("generation", {})
        app_config.generation = GenerationConfig(
            default_agent=gen_data.get("default_agent", "claude"),
            default_batch_size=gen_data.get("default_batch_size", 5),
            default_parallelism=gen_data.get("default_parallelism", 5),
        )

        # Agent configs
        agents_data = yaml_data.get("agents", {})
        for agent_name, agent_data in agents_data.items():
            app_config.agents[agent_name] = AgentConfig(
                enabled=agent_data.get("enabled", True),
                command_template=agent_data.get("command_template"),
                timeout_seconds=agent_data.get("timeout_seconds", 600),
            )

        # Database path
        if "db_path" in yaml_data:
            app_config.db_path = Path(yaml_data["db_path"])

    # Environment variable overrides
    app_config.leetcode_session_cookie = os.getenv("LEETCODE_SESSION")
    app_config.leetcode_csrf_token = os.getenv("LEETCODE_CSRF_TOKEN")

    # Ensure default agents have entries
    for agent_name in ["claude", "codex", "gemini"]:
        if agent_name not in app_config.agents:
            app_config.agents[agent_name] = AgentConfig(enabled=True)

    return app_config


def create_default_config(config_path: Path = Path("config.yaml")) -> None:
    """Create a default config.yaml file if it doesn't exist."""
    if config_path.exists():
        return

    default_yaml = """# LeetCode Interactive Generator Configuration

generation:
  default_agent: claude          # claude | codex | gemini | generic
  default_batch_size: 5
  default_parallelism: 5

agents:
  claude:
    enabled: true
    timeout_seconds: 600

  codex:
    enabled: true
    timeout_seconds: 600

  gemini:
    enabled: true
    timeout_seconds: 600

  generic:
    enabled: false
    command_template: ""         # Example: "my-ai-tool --input {problem_file} --output {output_file}"
    timeout_seconds: 600

db_path: database/leetcode.db

# Environment variables (in .env file):
# LEETCODE_SESSION=<cookie>
# LEETCODE_CSRF_TOKEN=<token>
"""

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(default_yaml)
