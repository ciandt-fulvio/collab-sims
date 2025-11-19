"""Base tracker interface."""

from abc import ABC, abstractmethod

from ..core.events import AgentEvent


class BaseTracker(ABC):
    """Abstract base class for event trackers.

    Trackers can implement specific hooks for different event types,
    or override on_event() to handle all events uniformly.
    """

    async def on_start(self, event: AgentEvent) -> None:  # noqa: B027
        """Called when execution starts (single-turn API).

        Args:
            event: StartEvent with prompt and options
        """
        ...

    async def on_complete(self, event: AgentEvent) -> None:  # noqa: B027
        """Called when execution completes.

        Args:
            event: CompleteEvent with results and metrics
        """
        ...

    async def on_session_start(self, event: AgentEvent) -> None:  # noqa: B027
        """Called when a session starts (multi-turn API).

        Args:
            event: SessionStartEvent with session_id, user_id, tags, metadata
        """
        ...

    async def on_session_end(self, event: AgentEvent) -> None:  # noqa: B027
        """Called when a session ends (multi-turn API).

        Args:
            event: SessionEndEvent with session_id, total_queries, duration
        """
        ...

    async def on_query(self, event: AgentEvent) -> None:  # noqa: B027
        """Called when a query is sent in a session.

        Args:
            event: QueryEvent with prompt, query_number, session_id
        """
        ...

    @abstractmethod
    async def on_event(self, event: AgentEvent) -> None:
        """Handle an event.

        This is called for ALL events after specific hooks.
        Implement this to handle events uniformly, or use specific hooks above.

        Args:
            event: Any AgentEvent subclass
        """
        pass

    async def on_error(self, event: AgentEvent) -> None:  # noqa: B027
        """Called when an error occurs.

        Args:
            event: ErrorEvent with error details
        """
        ...

    def should_handle(self, event: AgentEvent) -> bool:
        """Filter to determine if this tracker should handle the event.

        Override this method to implement event filtering logic.
        For example, filter by user_id, tags, event type, etc.

        Args:
            event: The event to check

        Returns:
            True if the tracker should process this event, False otherwise

        Example:
            >>> def should_handle(self, event):
            ...     # Only track events for specific users
            ...     return event.user_id in ["user1", "user2"]
        """
        return True

    async def __aenter__(self):
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.teardown()

    async def setup(self) -> None:  # noqa: B027
        """Setup tracker (e.g., open file, connect to DB)."""
        ...

    async def teardown(self) -> None:  # noqa: B027
        """Cleanup tracker (e.g., close file, disconnect from DB)."""
        ...
