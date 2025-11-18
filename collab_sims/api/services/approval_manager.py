"""Approval manager for tool execution approval workflow."""

import time
from asyncio import Future
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ApprovalRequest:
    """Pending approval request."""
    tool_use_id: str
    tool_name: str
    tool_input: dict
    session_id: str
    future: Future
    created_at: float
    remember: bool = False  # Track if user wants to remember this approval


class ApprovalManager:
    """Manages approval requests and user responses for tool execution."""

    def __init__(self):
        """Initialize the approval manager."""
        self._pending: Dict[str, ApprovalRequest] = {}
        self._approval_config: Dict[str, dict] = {}  # per-session config

    def set_config(self, session_id: str, config: dict):
        """
        Set approval configuration for a session.

        Args:
            session_id: Session identifier
            config: Configuration dict with keys:
                - mode: "auto" | "interactive" | "manual"
                - tool_policies: Dict[tool_name, risk_level]
                - auto_approved_tools: List of tool names
        """
        self._approval_config[session_id] = {
            "mode": config.get("mode", "interactive"),
            "tool_policies": config.get("tool_policies", {}),
            "auto_approved_tools": config.get("auto_approved_tools", [])
        }

    def should_request_approval(
        self,
        session_id: str,
        tool_name: str
    ) -> bool:
        """
        Determine if tool needs approval based on configuration.

        Args:
            session_id: Session identifier
            tool_name: Name of the tool

        Returns:
            True if approval is required, False otherwise
        """
        config = self._approval_config.get(session_id, {})
        mode = config.get("mode", "interactive")

        if mode == "auto":
            return False  # Auto-approve everything

        if mode == "manual":
            return True  # Require approval for everything

        # Interactive mode - check tool policies
        tool_policies = config.get("tool_policies", {})
        risk_level = tool_policies.get(tool_name, "medium")

        # Check session memory
        auto_approved = config.get("auto_approved_tools", [])
        if tool_name in auto_approved:
            return False

        # Check risk level
        if risk_level == "safe":
            return False

        return True  # Needs approval

    async def request_approval(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict,
        session_id: str
    ) -> tuple[bool, Optional[str], bool]:
        """
        Request approval and wait for user response.

        Args:
            tool_use_id: Unique identifier for this tool use
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            session_id: Session identifier

        Returns:
            Tuple of (approved: bool, reason: Optional[str], remember: bool)
        """
        future = Future()
        request = ApprovalRequest(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=session_id,
            future=future,
            created_at=time.time()
        )

        self._pending[tool_use_id] = request

        # Wait for user response (blocks until approved/rejected)
        result = await future

        # Get remember flag from request before cleanup
        remember = request.remember

        # Clean up
        del self._pending[tool_use_id]

        return (*result, remember)

    def approve(self, tool_use_id: str, remember: bool = False):
        """
        Approve a pending request.

        Args:
            tool_use_id: Unique identifier for the tool use
            remember: If True, remember approval for this tool in session

        Raises:
            ValueError: If no pending approval exists for tool_use_id
        """
        if tool_use_id not in self._pending:
            raise ValueError(f"No pending approval for {tool_use_id}")

        request = self._pending[tool_use_id]

        # Store remember flag in request
        request.remember = remember

        # Remember for this session if requested
        if remember:
            config = self._approval_config.get(request.session_id, {})
            auto_approved = config.get("auto_approved_tools", [])
            if request.tool_name not in auto_approved:
                auto_approved.append(request.tool_name)

        # Resolve the future
        request.future.set_result((True, None))

    def reject(self, tool_use_id: str, reason: str = "User rejected"):
        """
        Reject a pending request.

        Args:
            tool_use_id: Unique identifier for the tool use
            reason: Reason for rejection

        Raises:
            ValueError: If no pending approval exists for tool_use_id
        """
        if tool_use_id not in self._pending:
            raise ValueError(f"No pending approval for {tool_use_id}")

        request = self._pending[tool_use_id]
        request.future.set_result((False, reason))

    def get_pending(self, session_id: str) -> list[ApprovalRequest]:
        """
        Get all pending approvals for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of pending ApprovalRequests for the session
        """
        return [
            req for req in self._pending.values()
            if req.session_id == session_id
        ]
