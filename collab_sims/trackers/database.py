"""Database tracker for persisting sessions and events."""

import logging
from datetime import datetime
from typing import Optional

from .base import BaseTracker
from ..core.events import (
    AgentEvent,
    EventType,
    SessionStartEvent,
    SessionEndEvent,
    QueryEvent,
)
from ..persistence import SessionRepository

logger = logging.getLogger(__name__)


class DatabaseTracker(BaseTracker):
    """Tracker that persists all sessions and events to database.

    Automatically stores:
    - Session metadata (session_id, user_id, timestamps)
    - All events (messages, tool calls, plans, etc.)
    - Query information (derived from QueryEvent and CompleteEvent)

    Works with any SessionRepository implementation (SQLite, MySQL, etc.)
    """

    def __init__(self, repository: SessionRepository):
        """Initialize database tracker.

        Args:
            repository: SessionRepository implementation
        """
        super().__init__()
        self.repository = repository
        self._query_index = 0  # Track query number within session
        self._closed = False  # Track if already closed (for shared tracker)
        self._initialized = False  # Track if already initialized (for shared tracker)

    async def setup(self) -> None:
        """Initialize database connection.

        This is idempotent - safe to call multiple times.
        This is important because the database tracker is shared across sessions,
        so it may be initialized by both manager and session.
        """
        if self._initialized:
            logger.debug("DatabaseTracker already initialized, skipping")
            return

        self._initialized = True
        await self.repository.initialize()
        logger.info("DatabaseTracker initialized")

    async def teardown(self) -> None:
        """Close database connection.

        This is idempotent - safe to call multiple times.
        This is important because the database tracker is shared across sessions,
        so it may be closed by both session.close() and manager.shutdown().
        """
        if self._closed:
            logger.debug("DatabaseTracker already closed, skipping")
            return

        self._closed = True
        await self.repository.close()
        logger.info("DatabaseTracker closed")

    async def on_session_start(self, event: SessionStartEvent) -> None:
        """Create session record when session starts."""
        try:
            await self.repository.create_session(
                session_id=event.session_id,
                user_id=event.user_id,
                created_at=datetime.fromisoformat(event.timestamp),
                metadata=event.metadata
            )
            logger.debug(f"Session started: {event.session_id}")
        except Exception as e:
            logger.error(f"Failed to create session record: {e}")

    async def on_query(self, event: QueryEvent) -> None:
        """Track query index for event linking."""
        # Store query index for this session (QueryEvent uses query_number)
        self._query_index = event.query_number - 1 if hasattr(event, 'query_number') else 0

    async def on_session_end(self, event: SessionEndEvent) -> None:
        """Update session record when session ends."""
        try:
            await self.repository.update_session(
                session_id=event.session_id,
                closed_at=datetime.fromisoformat(event.timestamp),
                status='closed'
            )
            logger.debug(f"Session ended: {event.session_id}")
        except Exception as e:
            logger.error(f"Failed to update session record: {e}")

    async def on_event(self, event: AgentEvent) -> None:
        """Persist all events to database.

        This is called for EVERY event after specific hooks.
        Stores the full event as JSON for maximum flexibility.
        """
        # Skip if no session_id (shouldn't happen, but be safe)
        if not event.session_id:
            return

        try:
            # Extract query_index if available
            query_index = None
            if hasattr(event, 'query_index'):
                query_index = event.query_index
            elif event.type in [EventType.QUERY, EventType.MESSAGE, EventType.TOOL_USE, EventType.TOOL_RESULT]:
                query_index = self._query_index

            # Extract message_id for linking tool_use and tool_result
            message_id = None
            if hasattr(event, 'message_id'):
                message_id = event.message_id
            elif hasattr(event, 'tool_use_id'):
                message_id = event.tool_use_id

            # Store event
            await self.repository.add_event(
                session_id=event.session_id,
                event_type=event.type.value if hasattr(event.type, 'value') else str(event.type),
                timestamp=datetime.fromisoformat(event.timestamp),
                data=event.to_dict(),
                query_index=query_index,
                message_id=message_id
            )

            # Update query count on CompleteEvent
            if event.type == EventType.COMPLETE:
                await self.repository.update_session(
                    session_id=event.session_id,
                    query_count=self._query_index + 1
                )

        except Exception as e:
            # Don't let persistence errors crash the session
            logger.error(f"Failed to persist event {event.type}: {e}")
