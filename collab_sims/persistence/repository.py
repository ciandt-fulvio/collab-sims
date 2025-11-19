"""Abstract repository interface for session persistence."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class SessionRepository(ABC):
    """Abstract base class for session persistence.

    Defines the interface for storing and retrieving session data.
    Implementations can use SQLite, MySQL, PostgreSQL, etc.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database connection and schema."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    async def create_session(
        self,
        session_id: str,
        user_id: str | None,
        created_at: datetime,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Create a new session record.

        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            created_at: Session creation timestamp
            metadata: Optional session metadata (will be JSON serialized)
        """
        pass

    @abstractmethod
    async def update_session(
        self,
        session_id: str,
        closed_at: datetime | None = None,
        status: str | None = None,
        query_count: int | None = None
    ) -> None:
        """Update session record.

        Args:
            session_id: Session identifier
            closed_at: Optional session close timestamp
            status: Optional session status ('active', 'closed', 'error')
            query_count: Optional query count
        """
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found
        """
        pass

    @abstractmethod
    async def list_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering.

        Args:
            user_id: Optional filter by user_id
            status: Optional filter by status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of session data dicts
        """
        pass

    @abstractmethod
    async def count_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None
    ) -> int:
        """Count sessions matching criteria.

        Args:
            user_id: Optional filter by user_id
            status: Optional filter by status

        Returns:
            Total count
        """
        pass

    @abstractmethod
    async def add_event(
        self,
        session_id: str,
        event_type: str,
        timestamp: datetime,
        data: dict[str, Any],
        query_index: int | None = None,
        message_id: str | None = None
    ) -> None:
        """Add an event to the database.

        Args:
            session_id: Session identifier
            event_type: Type of event (message, tool_use, etc.)
            timestamp: Event timestamp
            data: Event data (will be JSON serialized)
            query_index: Optional query index within session
            message_id: Optional message ID for linking
        """
        pass

    @abstractmethod
    async def get_events(
        self,
        session_id: str,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get events for a session.

        Args:
            session_id: Session identifier
            event_type: Optional filter by event type
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of event data dicts
        """
        pass

    @abstractmethod
    async def count_events(
        self,
        session_id: str,
        event_type: str | None = None
    ) -> int:
        """Count events for a session.

        Args:
            session_id: Session identifier
            event_type: Optional filter by event type

        Returns:
            Total count
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session and all its events (CASCADE).

        Args:
            session_id: Session identifier
        """
        pass
