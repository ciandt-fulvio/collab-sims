"""Schemas for approval configuration and responses"""

from typing import Literal

from pydantic import BaseModel, Field


class ApprovalConfig(BaseModel):
    """Configuration for tool approval workflow.

    Controls which tools require user approval before execution.
    """

    mode: Literal["auto", "interactive", "manual"] = Field(
        default="interactive",
        description=(
            "Approval mode:\n"
            "- 'auto': Auto-approve all tools (no user interaction)\n"
            "- 'interactive': Only approve dangerous tools based on tool_policies\n"
            "- 'manual': Require approval for every tool"
        ),
    )

    tool_policies: dict[str, Literal["safe", "medium", "high"]] = Field(
        default_factory=dict,
        description=(
            "Map of tool names to risk levels:\n"
            "- 'safe': Auto-approve without prompting user\n"
            "- 'medium': Require user approval\n"
            "- 'high': Require user approval\n"
            "\nCommon tool names: Bash, Write, Edit, Read, Glob, Grep, WebFetch, Task\n"
            "Unknown tools default to 'medium' risk level."
        ),
    )

    auto_approved_tools: list[str] = Field(
        default_factory=list,
        description=(
            "List of tool names to auto-approve for this session.\n"
            "Useful for pre-remembered user preferences or session-specific trust."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mode": "interactive",
                    "tool_policies": {
                        "Bash": "high",
                        "Write": "medium",
                        "Edit": "medium",
                        "Read": "safe",
                        "Glob": "safe",
                        "Grep": "safe",
                    },
                    "auto_approved_tools": [],
                },
                {"mode": "auto"},
                {"mode": "manual"},
            ]
        }
    }


class PendingApprovalInfo(BaseModel):
    """Information about a pending approval request"""

    tool_use_id: str = Field(description="Unique identifier for this tool execution")
    tool_name: str = Field(description="Name of the tool requesting approval")
    tool_input: dict = Field(description="Input parameters for the tool")
    created_at: float = Field(description="Unix timestamp when approval was requested")


class ApprovalRequestData(BaseModel):
    """Request to approve or reject a tool execution"""

    approved: bool = Field(description="True to approve, False to reject")
    remember: bool = Field(
        default=False, description="If true, remember this approval for the tool in this session"
    )
    reason: str | None = Field(default=None, description="Optional reason for rejection")


class PendingApprovalsResponse(BaseModel):
    """Response containing all pending approvals for a session"""

    pending: list[PendingApprovalInfo] = Field(description="List of pending approval requests")
    count: int = Field(description="Number of pending approvals")
