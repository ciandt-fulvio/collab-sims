"""Request schemas for API endpoints"""

from typing import Any

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """Request for single-turn execution"""

    prompt: str = Field(..., description="Prompt to send to Claude agent")
    config: dict[str, Any] | None = Field(
        default=None, description="Optional session configuration (user_id, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "What is the capital of France?",
                    "config": {"user_id": "user123"},
                }
            ]
        }
    }


class SessionCreateRequest(BaseModel):
    """Request to create a new multi-turn session for a project.

    Required:
    - project_name: Name of the project (references MD file in data/projects/)

    Optional:
    - agent_name: Agent persona to use (references MD file in data/agents/)
    - config: Additional session configuration (user_id, tags, approval_config, etc.)
    """

    project_name: str = Field(
        ...,
        description="Project name (required) - references MD file in data/projects/"
    )

    agent_name: str | None = Field(
        default=None,
        description="Agent persona to use (optional) - references MD file in data/agents/"
    )

    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional session configuration including:\n"
            "- user_id: User identifier\n"
            "- tags: List of tags\n"
            "- metadata: Custom metadata dict\n"
            "- approval_config: Tool approval settings (see ApprovalConfig schema)"
        )
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_name": "design-sprint-q1",
                    "agent_name": "facilitator",
                    "config": {
                        "user_id": "user123",
                        "tags": ["production"],
                        "approval_config": {
                            "mode": "interactive",
                            "tool_policies": {
                                "Bash": "high",
                                "Write": "medium",
                                "Read": "safe"
                            }
                        }
                    }
                },
                {
                    "project_name": "research-ux",
                    "agent_name": "researcher",
                    "config": {
                        "user_id": "user456",
                        "approval_config": {
                            "mode": "auto"
                        }
                    }
                }
            ]
        }
    }


class SessionQueryRequest(BaseModel):
    """Request to query an existing session"""

    prompt: str = Field(..., description="Prompt to send in the session context")

    model_config = {
        "json_schema_extra": {
            "examples": [{"prompt": "Tell me more about that"}]
        }
    }
