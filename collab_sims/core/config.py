"""Session configuration for Collab Sims."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_collab_sims_config_dir() -> str:
    """Get Collab Sims configuration directory.

    Returns ~/.collab_sims/ for session storage, isolated from personal Claude Code sessions.
    Can be overridden with COLLAB_SIMS_CONFIG_DIR environment variable.

    Returns:
        Absolute path to Collab Sims config directory
    """
    config_dir = os.environ.get("COLLAB_SIMS_CONFIG_DIR")
    if config_dir:
        return config_dir

    # Default to ~/.collab_sims/
    home = Path.home()
    return str(home / ".collab_sims")


def get_default_working_dir() -> str:
    """Get default working directory from environment.

    Returns:
        Working directory path (absolute)

    Behavior:
        - Reads COLLAB_SIMS_WORKSPACE_DIR from environment (loaded from .env)
        - Falls back to current working directory if not set
    """
    env_dir = os.environ.get("COLLAB_SIMS_WORKSPACE_DIR")
    if env_dir:
        return env_dir

    # Fallback to current working directory
    return os.getcwd()


@dataclass
class SessionConfig:
    """Configuration for creating an agent session.

    Attributes:
        project_name: Project name (references MD file in data/projects/) - REQUIRED
        agent_name: Agent persona to use (references MD file in data/agents/)
        user_id: Optional user identifier for multi-tenant tracking
        tags: List of tags for categorizing/filtering sessions
        metadata: Arbitrary metadata dictionary for custom data
        resume_session_id: Optional session ID to resume (future feature)
        include_partial_messages: Enable word-by-word streaming for real-time text updates
        approval_config: Configuration for tool approval workflow
        working_dir: Working directory for agent file operations.
                    If None, reads COLLAB_SIMS_WORKSPACE_DIR env var (defaults to CWD).
                    Use '.' for current directory or provide absolute path.

    Example:
        >>> config = SessionConfig(
        ...     project_name="design-sprint-q1",
        ...     agent_name="facilitator",
        ...     user_id="user123",
        ...     tags=["production", "support"],
        ...     metadata={"source": "web_ui", "region": "us-west"},
        ...     include_partial_messages=True,
        ...     working_dir=".",  # or None for default (CWD)
        ...     approval_config={
        ...         "mode": "interactive",
        ...         "tool_policies": {"Bash": "high", "Write": "medium"}
        ...     }
        ... )
    """

    project_name: str = "default-project"  # Required for API, default for simple usage
    agent_name: str | None = None
    user_id: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    resume_session_id: str | None = None
    include_partial_messages: bool = False
    approval_config: dict[str, Any] | None = None
    working_dir: str | None = None
