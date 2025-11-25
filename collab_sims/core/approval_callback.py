"""Approval callback for Claude Agent SDK can_use_tool hook."""

import uuid
from collections.abc import Awaitable, Callable

from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

# Note: ApprovalManager import will be resolved at runtime
# from collab_sims.api.services.approval_manager import ApprovalManager
from collab_sims.core.events import AgentEvent, ApprovalRequestEvent, ApprovalResponseEvent


class ApprovalCallback:
    """Callback for SDK can_use_tool hook to handle approval workflow."""

    def __init__(
        self,
        approval_manager,  # ApprovalManager type annotation removed to avoid circular import
        session_id: str,
        event_emitter: Callable[[AgentEvent], Awaitable[None]],
    ):
        """
        Initialize the approval callback.

        Args:
            approval_manager: ApprovalManager instance
            session_id: Session identifier
            event_emitter: Async function to emit events
        """
        self.approval_manager = approval_manager
        self.session_id = session_id
        self.event_emitter = event_emitter

    async def __call__(
        self, tool_name: str, tool_input: dict, context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """
        Called by SDK before each tool execution.

        Args:
            tool_name: Name of tool being used
            tool_input: Input parameters for the tool
            context: Permission context with suggestions and signal

        Returns:
            Either allow or deny the tool execution
        """
        # Check if approval needed
        if not self.approval_manager.should_request_approval(self.session_id, tool_name):
            return PermissionResultAllow()

        # Generate tool_use_id for tracking
        tool_use_id = str(uuid.uuid4())

        # Get risk level from config
        config = self.approval_manager._approval_config.get(self.session_id, {})
        tool_policies = config.get("tool_policies", {})
        risk_level = tool_policies.get(tool_name, "medium")

        # Emit approval request event to frontend
        event = ApprovalRequestEvent(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,  # Use raw input (no path normalization needed for local execution)
            session_id=self.session_id,
            status="pending",
            risk_level=risk_level,
        )
        await self.event_emitter(event)

        # Wait for user decision (blocks here)
        approved, reason, remember = await self.approval_manager.request_approval(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=self.session_id,
        )

        # Emit approval response event to frontend
        response_event = ApprovalResponseEvent(
            tool_use_id=tool_use_id,
            approved=approved,
            remember=remember,
            reason=reason,
            session_id=self.session_id,
        )
        await self.event_emitter(response_event)

        if approved:
            return PermissionResultAllow()
        else:
            return PermissionResultDeny(
                message=reason or "User rejected this action",
                interrupt=False,  # Continue execution, just skip this tool
            )
