"""Approval management endpoints for tool execution approval workflow"""

from fastapi import APIRouter, HTTPException
from ..schemas import ApprovalRequestData, PendingApprovalsResponse, PendingApprovalInfo, ApprovalConfig
from ..services import session_manager

router = APIRouter(prefix="/api/sessions/{session_id}/approvals", tags=["approvals"])


@router.get("/pending", response_model=PendingApprovalsResponse)
async def get_pending_approvals(session_id: str):
    """
    Get all pending approval requests for a session.

    Returns a list of tools waiting for user approval before execution.
    These approvals are blocking - the agent will wait until they are
    approved or rejected before continuing.

    Args:
        session_id: Session identifier

    Returns:
        PendingApprovalsResponse with list of pending approvals
    """
    approval_manager = session_manager.approval_manager
    pending = approval_manager.get_pending(session_id)

    return PendingApprovalsResponse(
        pending=[
            PendingApprovalInfo(
                tool_use_id=req.tool_use_id,
                tool_name=req.tool_name,
                tool_input=req.tool_input,
                created_at=req.created_at
            )
            for req in pending
        ],
        count=len(pending)
    )


@router.post("/{tool_use_id}/respond")
async def respond_to_approval(
    session_id: str,
    tool_use_id: str,
    response: ApprovalRequestData
):
    """
    Approve or reject a pending tool execution.

    When approved, the tool will execute immediately. When rejected,
    the tool will be skipped and execution will continue.

    Args:
        session_id: Session identifier
        tool_use_id: Unique identifier for the tool execution request
        response: Approval decision (approved/rejected) with optional settings

    Returns:
        Status confirmation

    Raises:
        HTTPException: 404 if no pending approval exists for this tool_use_id
    """
    approval_manager = session_manager.approval_manager

    try:
        if response.approved:
            approval_manager.approve(tool_use_id, remember=response.remember)
        else:
            approval_manager.reject(tool_use_id, reason=response.reason)

        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/config", response_model=ApprovalConfig)
async def get_approval_config(session_id: str):
    """
    Get current approval configuration for a session.

    Returns the approval mode and tool policies that determine
    which tools require user approval before execution.

    Args:
        session_id: Session identifier

    Returns:
        Current ApprovalConfig for the session

    Raises:
        HTTPException: 404 if session not found
    """
    approval_manager = session_manager.approval_manager
    config = approval_manager._approval_config.get(session_id)

    if config is None:
        raise HTTPException(status_code=404, detail="Session not found or no approval config")

    return ApprovalConfig(**config)


@router.put("/config")
async def update_approval_config(session_id: str, config: ApprovalConfig):
    """
    Update approval configuration for a session at runtime.

    This allows changing the approval mode and tool policies while
    the session is active. Changes take effect immediately for
    future tool executions.

    Args:
        session_id: Session identifier
        config: New approval configuration

    Returns:
        Updated configuration

    Example:
        # Switch to auto mode (no approvals)
        PUT /api/sessions/{id}/approvals/config
        {"mode": "auto"}

        # Switch to interactive with custom policies
        PUT /api/sessions/{id}/approvals/config
        {
            "mode": "interactive",
            "tool_policies": {
                "Bash": "high",
                "Write": "medium",
                "Read": "safe"
            }
        }
    """
    approval_manager = session_manager.approval_manager

    # Verify session exists
    if session_id not in session_manager._sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update config
    approval_manager.set_config(session_id, config.model_dump())

    return {"status": "ok", "config": config}
