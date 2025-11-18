"""Response schemas for API endpoints"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventResponse(BaseModel):
    """Single event from the agent execution"""

    event_type: str = Field(..., description="Type of event")
    timestamp: str = Field(..., description="ISO formatted timestamp")
    data: Dict[str, Any] = Field(..., description="Event-specific data")


class ExecuteResponse(BaseModel):
    """Response from single-turn execution"""

    events: List[EventResponse] = Field(..., description="List of events generated")
    status: str = Field(..., description="Execution status (completed, error)")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SessionResponse(BaseModel):
    """Information about a session"""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: str = Field(..., description="ISO formatted creation timestamp")
    config: Dict[str, Any] = Field(default_factory=dict, description="Session configuration")
    status: str = Field(..., description="Session status (active, closed)")
    execution_state: str = Field(default="idle", description="Runtime execution state (idle, executing)")
    query_count: int = Field(default=0, description="Number of queries in this session")


class SessionListResponse(BaseModel):
    """List of sessions"""

    sessions: List[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")


class ErrorResponse(BaseModel):
    """Error response"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")
