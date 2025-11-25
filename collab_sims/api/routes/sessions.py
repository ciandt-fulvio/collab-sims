"""Multi-turn session management endpoints"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import (
    EventResponse,
    ExecuteResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionQueryRequest,
    SessionResponse,
)
from ..services import session_manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(request: SessionCreateRequest):
    """
    Create a new multi-turn conversation session for a project.

    The session maintains context across multiple queries,
    allowing Claude to remember previous interactions.

    Required: project_name
    Optional: agent_name, config
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"🔵 create_session endpoint called for project '{request.project_name}' with agent '{request.agent_name}'"
    )

    try:
        session_data = await session_manager.create_session(
            project_name=request.project_name, agent_name=request.agent_name, config=request.config
        )
        logger.info(
            f"🟢 create_session completed: {session_data['session_id']} for project '{request.project_name}'"
        )
        return SessionResponse(**session_data)
    except Exception as e:
        logger.error(f"🔴 create_session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=SessionListResponse)
async def list_sessions(status: str | None = None):
    """List sessions.

    Args:
        status: Filter by status ('active', 'closed', or None for all sessions).
                Default is None (all sessions from database).

    Returns:
        List of all sessions from database (not just active ones in memory)
    """
    # List all sessions from database (not just active ones in memory)
    sessions = await session_manager.list_all_sessions_from_database(status=status)
    return SessionListResponse(
        sessions=[SessionResponse(**s) for s in sessions], total=len(sessions)
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get details about a specific session"""
    session_data = await session_manager.get_session(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionResponse(**session_data)


@router.post("/{session_id}/query", response_model=ExecuteResponse)
async def query_session(session_id: str, request: SessionQueryRequest):
    """
    Send a query to an existing session (buffered response).

    The agent will respond with context from previous queries in this session.
    For real-time streaming, use POST /api/sessions/{session_id}/query/stream.

    Args:
        session_id: Session identifier
        request: Query request with prompt

    Returns:
        ExecuteResponse with all events, status, and optional error
    """
    events, status, error = await session_manager.query_session(
        session_id=session_id, prompt=request.prompt
    )

    if status == "error" and error and "not found" in error:
        raise HTTPException(status_code=404, detail=error)

    # Convert events to response models
    event_responses = [
        EventResponse(
            event_type=event.get("type", event.get("event_type", "unknown")),
            timestamp=event["timestamp"],
            data=event,
        )
        for event in events
    ]

    return ExecuteResponse(events=event_responses, status=status, error=error)


@router.post("/{session_id}/query/stream")
async def query_session_stream(session_id: str, request: SessionQueryRequest):
    """
    Send a query to an existing session with Server-Sent Events streaming.

    Events are streamed in real-time as they occur during execution.
    The session context is maintained - Claude remembers all previous queries.

    Args:
        session_id: Session identifier
        request: Query request with prompt

    Returns:
        StreamingResponse with SSE-formatted events
    """

    async def event_generator():
        """Generator that yields SSE-formatted events"""
        try:
            async for event in session_manager.query_session_stream(
                session_id=session_id, prompt=request.prompt
            ):
                # Format as SSE
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            # Send error event
            error_event = {
                "event_type": "error",
                "error": str(e),
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/{session_id}/interrupt", status_code=200)
async def interrupt_session(session_id: str):
    """
    Interrupt the currently executing query in a session.

    This stops Claude mid-execution and halts event streaming, similar to pressing
    ESC in Claude Code shell. The session remains connected and ready for new queries.

    Args:
        session_id: Session identifier

    Returns:
        Success response with session status

    Raises:
        404: Session not found
        400: Session not connected or no query is executing
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        success = await session_manager.interrupt_session(session_id)

        if not success:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found or cannot be interrupted"
            )

        return {
            "session_id": session_id,
            "status": "interrupted",
            "message": "Query execution interrupted successfully",
        }
    except Exception as e:
        logger.error(f"Failed to interrupt session {session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """
    Close and delete a session.

    This ends the conversation and frees up resources.
    """
    success = await session_manager.close_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return None


@router.get("/{session_id}/events")
async def get_session_events(
    session_id: str, event_type: str | None = None, page: int = 1, page_size: int = 100
):
    """
    Get all events for a session from database.

    This retrieves persisted events, allowing you to view session history
    even after the session has closed or the server restarted.

    Args:
        session_id: Session identifier
        event_type: Optional filter by event type (message, tool_use, etc.)
        page: Page number (1-indexed)
        page_size: Number of events per page (max 1000)

    Returns:
        Paginated list of events with metadata

    Example:
        GET /api/sessions/{id}/events?event_type=message&page=1&page_size=50
    """
    from ..services.session_manager import session_manager

    # Validate page_size
    page_size = min(page_size, 1000)
    offset = (page - 1) * page_size

    # Get database tracker
    db_tracker = session_manager.db_tracker
    repository = db_tracker.repository

    try:
        # Get events from database
        events = await repository.get_events(
            session_id=session_id, event_type=event_type, limit=page_size, offset=offset
        )

        # Get total count
        total = await repository.count_events(session_id=session_id, event_type=event_type)

        return {
            "session_id": session_id,
            "events": events,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")


@router.patch("/{session_id}/events/{event_id}")
async def update_event_data(session_id: str, event_id: int, request: dict):
    """
    Update the data field of an event (e.g., checkbox state in DoD).

    Request body: {"data": {...}} - The complete new data object for the event
    """
    import logging

    logger = logging.getLogger(__name__)

    data = request.get("data")
    if data is None:
        raise HTTPException(status_code=400, detail="data field is required")

    logger.info(f"🔵 Updating event {event_id} data in session {session_id}")

    try:
        # Get database tracker
        db_tracker = session_manager.db_tracker
        repository = db_tracker.repository

        # Update event data in database
        await repository.update_event_data(event_id=str(event_id), data=data)

        logger.info(f"🟢 Event {event_id} updated successfully")
        return {"session_id": session_id, "event_id": event_id, "status": "success"}
    except ValueError as e:
        logger.error(f"🔴 Event not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"🔴 Failed to update event data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}/name")
async def update_session_name(session_id: str, request: dict):
    """
    Update the session name (typically from first user message).

    Request body: {"name": "First 30 characters of message..."}
    """
    import logging

    logger = logging.getLogger(__name__)

    session_name = request.get("name")
    if not session_name:
        raise HTTPException(status_code=400, detail="name field is required")

    logger.info(f"🔵 Updating session {session_id} name to: {session_name}")

    try:
        await session_manager.update_session_name(session_id, session_name)
        return {"session_id": session_id, "name": session_name}
    except Exception as e:
        logger.error(f"🔴 Failed to update session name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/activity")
async def post_activity_card(session_id: str, request: dict):
    """
    Post an activity card event to the session.

    When user clicks on an activity in the Project tab, this endpoint
    creates an interactive card in the chat with activity details and action buttons.

    Request body: {
        "project_name": str,
        "stage_title": str,
        "activity_id": str,
        "activity_title": str,
        "activity_description": str,
        "activity_script": str,
        "activity_required": bool,
        "activity_completed": bool,
        "verifications": list[dict]
    }
    """
    import logging

    from ...core.events import ActivityCardEvent

    logger = logging.getLogger(__name__)

    logger.info(f"🔵 Creating activity card for session {session_id}")

    try:
        # Create activity card event
        event = ActivityCardEvent(
            session_id=session_id,
            project_name=request.get("project_name", ""),
            stage_title=request.get("stage_title", ""),
            activity_id=request.get("activity_id", ""),
            activity_title=request.get("activity_title", ""),
            activity_description=request.get("activity_description", ""),
            activity_script=request.get("activity_script", ""),
            activity_required=request.get("activity_required", False),
            activity_completed=request.get("activity_completed", False),
            verifications=request.get("verifications", []),
        )

        # Emit the event through the session manager
        await session_manager.emit_activity_card(session_id, event)

        logger.info(f"🟢 Activity card created successfully for session {session_id}")
        return {"session_id": session_id, "event_id": event.event_id, "status": "success"}
    except Exception as e:
        logger.error(f"🔴 Failed to create activity card: {e}")
        raise HTTPException(status_code=500, detail=str(e))
