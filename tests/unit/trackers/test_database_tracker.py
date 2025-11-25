"""Unit tests for DatabaseTracker.

Tests the database tracker that persists events to a repository.

References:
- https://docs.python.org/3/library/unittest.mock.html
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

# Import directly from module files to avoid circular imports via __init__.py
from collab_sims.core.events import (
    CompleteEvent,
    MessageEvent,
    QueryEvent,
    SessionEndEvent,
    SessionStartEvent,
)
from collab_sims.trackers.database import DatabaseTracker


class TestDatabaseTrackerSetup:
    """Test tracker initialization and cleanup."""

    async def test_setup_initializes_repository(self):
        """Test that setup initializes the repository."""
        mock_repo = MagicMock()
        mock_repo.initialize = AsyncMock()

        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()

        mock_repo.initialize.assert_called_once()

    async def test_setup_is_idempotent(self):
        """Test that calling setup multiple times is safe."""
        mock_repo = MagicMock()
        mock_repo.initialize = AsyncMock()

        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()
        await tracker.setup()  # Second call should be no-op

        # Should only initialize once
        mock_repo.initialize.assert_called_once()

    async def test_teardown_closes_repository(self):
        """Test that teardown closes the repository."""
        mock_repo = MagicMock()
        mock_repo.initialize = AsyncMock()
        mock_repo.close = AsyncMock()

        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()
        await tracker.teardown()

        mock_repo.close.assert_called_once()

    async def test_teardown_is_idempotent(self):
        """Test that calling teardown multiple times is safe."""
        mock_repo = MagicMock()
        mock_repo.initialize = AsyncMock()
        mock_repo.close = AsyncMock()

        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()
        await tracker.teardown()
        await tracker.teardown()  # Second call should be no-op

        # Should only close once
        mock_repo.close.assert_called_once()


class TestDatabaseTrackerSessionEvents:
    """Test tracking session lifecycle events."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.initialize = AsyncMock()
        repo.create_session = AsyncMock()
        repo.update_session = AsyncMock()
        repo.add_event = AsyncMock()
        repo.close = AsyncMock()
        return repo

    @pytest.fixture
    async def tracker(self, mock_repo):
        """Create and setup a tracker with mock repository."""
        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()
        return tracker

    async def test_on_session_start_creates_session(self, tracker, mock_repo):
        """Test that session start creates session record."""
        event = SessionStartEvent(
            session_id="test-session",
            user_id="test-user",
            tags=["test"],
            metadata={"role": "worker"},
        )

        await tracker.on_session_start(event)

        mock_repo.create_session.assert_called_once()
        call_args = mock_repo.create_session.call_args
        assert call_args.kwargs["session_id"] == "test-session"
        assert call_args.kwargs["user_id"] == "test-user"
        assert call_args.kwargs["metadata"] == {"role": "worker"}

    async def test_on_session_end_updates_session(self, tracker, mock_repo):
        """Test that session end updates session record."""
        event = SessionEndEvent(session_id="test-session", total_queries=5, total_duration_ms=30000)

        await tracker.on_session_end(event)

        mock_repo.update_session.assert_called_once()
        call_args = mock_repo.update_session.call_args
        assert call_args.kwargs["session_id"] == "test-session"
        assert call_args.kwargs["status"] == "closed"

    async def test_on_query_tracks_query_index(self, tracker):
        """Test that query event updates query index."""
        event = QueryEvent(prompt="Test query", query_number=1, session_id="test-session")

        await tracker.on_query(event)

        # Query number 1 should map to index 0
        assert tracker._query_index == 0


class TestDatabaseTrackerEventPersistence:
    """Test persisting events to database."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.initialize = AsyncMock()
        repo.add_event = AsyncMock()
        repo.update_session = AsyncMock()
        repo.close = AsyncMock()
        return repo

    @pytest.fixture
    async def tracker(self, mock_repo):
        """Create and setup a tracker with mock repository."""
        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()
        return tracker

    async def test_on_event_persists_message(self, tracker, mock_repo):
        """Test that message events are persisted."""
        event = MessageEvent(role="assistant", content="Test message", session_id="test-session")

        await tracker.on_event(event)

        mock_repo.add_event.assert_called_once()
        call_args = mock_repo.add_event.call_args
        assert call_args.kwargs["session_id"] == "test-session"
        assert call_args.kwargs["event_type"] == "message"

    async def test_on_event_skips_without_session_id(self, tracker, mock_repo):
        """Test that events without session_id are skipped."""
        event = MessageEvent(
            role="assistant",
            content="Test message",
            session_id=None,  # No session ID
        )

        await tracker.on_event(event)

        # Should not persist
        mock_repo.add_event.assert_not_called()

    async def test_on_event_updates_query_count_on_complete(self, tracker, mock_repo):
        """Test that CompleteEvent updates session query count."""
        # Set up query index
        tracker._query_index = 2

        event = CompleteEvent(session_id="test-session", duration_ms=1000)

        await tracker.on_event(event)

        # Should update query count to 3 (index + 1)
        mock_repo.update_session.assert_called_once()
        call_args = mock_repo.update_session.call_args
        assert call_args.kwargs["query_count"] == 3


class TestDatabaseTrackerErrorHandling:
    """Test error handling in tracker."""

    async def test_handles_repository_errors_gracefully(self):
        """Test that repository errors don't crash the tracker."""
        mock_repo = MagicMock()
        mock_repo.initialize = AsyncMock()
        mock_repo.add_event = AsyncMock(side_effect=Exception("DB error"))

        tracker = DatabaseTracker(mock_repo)
        await tracker.setup()

        event = MessageEvent(role="assistant", content="Test", session_id="test-session")

        # Should not raise exception
        await tracker.on_event(event)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
