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
    """Request to create a new multi-turn session with optional approval configuration.

    The config field accepts:
    - user_id (str): User identifier for tracking
    - tags (list): Tags for categorization
    - metadata (dict): Arbitrary metadata
    - approval_config (ApprovalConfig): Tool approval settings
    """

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

    session_type: str = Field(
        default="worker",
        description="Type of session: 'worker' or 'scout'"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
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
