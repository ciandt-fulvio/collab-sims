"""Single-turn execution endpoints"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import EventResponse, ExecuteRequest, ExecuteResponse
from ..services import ExecutionService

router = APIRouter(prefix="/api", tags=["execute"])


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    """
    Execute a single-turn prompt and return all events (buffered response).

    Returns all events after execution completes. For real-time streaming,
    use POST /api/execute/stream instead.

    Args:
        request: Execute request with prompt and optional config

    Returns:
        ExecuteResponse with all events, status, and optional error
    """
    try:
        events, status, error = await ExecutionService.execute(
            prompt=request.prompt, config=request.config
        )

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/stream")
async def execute_stream(request: ExecuteRequest):
    """
    Execute a single-turn prompt with Server-Sent Events streaming.

    Events are streamed in real-time as they occur during execution.
    Use this for live progress updates, UIs with loading states, etc.

    Args:
        request: Execute request with prompt and optional config

    Returns:
        StreamingResponse with SSE-formatted events
    """

    async def event_generator():
        """Generator that yields SSE-formatted events"""
        try:
            async for event in ExecutionService.execute_stream(
                prompt=request.prompt, config=request.config
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
