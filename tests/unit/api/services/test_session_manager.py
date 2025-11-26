"""Unit tests for SessionManager session reactivation.

Tests the automatic reactivation of closed sessions when users return to them.

References:
- https://docs.python.org/3/library/unittest.mock.html
- https://docs.pytest.org/en/stable/how-to/fixtures.html
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSessionReactivation:
    """Test automatic session reactivation from database."""

    @pytest.fixture
    def mock_db_tracker(self):
        """Create a mock database tracker with repository."""
        tracker = MagicMock()
        tracker.repository = MagicMock()
        tracker.repository.get_session = AsyncMock()
        tracker.repository.update_session = AsyncMock()
        tracker.repository.list_sessions = AsyncMock(return_value=[])
        tracker.repository.initialize = AsyncMock()
        tracker.repository.close = AsyncMock()
        return tracker

    @pytest.fixture
    def session_manager(self, mock_db_tracker):
        """Create a SessionManager with mocked dependencies."""
        from collab_sims.api.services.session_manager import SessionManager

        manager = SessionManager()
        manager.db_tracker = mock_db_tracker
        return manager

    async def test_reactivate_session_returns_true_if_already_active(self, session_manager):
        """Test that _reactivate_session returns True if session is already in memory."""
        session_id = "test-session-123"

        # Add session to memory
        session_manager._sessions[session_id] = {
            "session_id": session_id,
            "project_name": "test-project",
            "status": "active",
        }

        result = await session_manager._reactivate_session(session_id)

        assert result is True
        # Should not query database
        session_manager.db_tracker.repository.get_session.assert_not_called()

    async def test_reactivate_session_returns_false_if_not_in_database(
        self, session_manager, mock_db_tracker
    ):
        """Test that _reactivate_session returns False if session not found in database."""
        session_id = "nonexistent-session"
        mock_db_tracker.repository.get_session.return_value = None

        result = await session_manager._reactivate_session(session_id)

        assert result is False
        mock_db_tracker.repository.get_session.assert_called_once_with(session_id)

    async def test_reactivate_session_returns_false_if_no_project_name(
        self, session_manager, mock_db_tracker
    ):
        """Test that _reactivate_session returns False if session has no project_name."""
        session_id = "bad-session"
        mock_db_tracker.repository.get_session.return_value = {
            "session_id": session_id,
            "project_name": None,  # Missing project_name
            "status": "closed",
        }

        result = await session_manager._reactivate_session(session_id)

        assert result is False

    @patch("collab_sims.api.services.session_manager.CollabSimsSession")
    @patch("collab_sims.api.services.session_manager.StreamTracker")
    async def test_reactivate_session_loads_from_database(
        self, mock_stream_tracker_class, mock_collab_session_class, session_manager, mock_db_tracker
    ):
        """Test that _reactivate_session loads session from database and activates it."""
        session_id = "closed-session-456"
        mock_db_tracker.repository.get_session.return_value = {
            "session_id": session_id,
            "project_name": "test-project",
            "agent_name": "test-agent",
            "session_name": "Test Session",
            "user_id": "user-123",
            "metadata": {"key": "value"},
            "query_count": 5,
            "status": "closed",
            "created_at": datetime.now(),
        }

        # Mock CollabSimsSession
        mock_claude_session = MagicMock()
        mock_claude_session._connect = AsyncMock()
        mock_collab_session_class.return_value = mock_claude_session

        # Mock StreamTracker
        mock_stream_tracker = MagicMock()
        mock_stream_tracker_class.return_value = mock_stream_tracker

        result = await session_manager._reactivate_session(session_id)

        assert result is True
        assert session_id in session_manager._sessions

        # Verify session data was loaded correctly
        session_data = session_manager._sessions[session_id]
        assert session_data["project_name"] == "test-project"
        assert session_data["agent_name"] == "test-agent"
        assert session_data["session_name"] == "Test Session"
        assert session_data["query_count"] == 5
        assert session_data["status"] == "active"
        assert session_data["execution_state"] == "idle"

        # Verify database was updated to mark as active
        mock_db_tracker.repository.update_session.assert_called_once_with(
            session_id=session_id, status="active"
        )

        # Verify Claude session was created with resume=True
        mock_collab_session_class.assert_called_once()
        call_kwargs = mock_collab_session_class.call_args.kwargs
        assert call_kwargs["session_id"] == session_id
        assert call_kwargs["resume"] is True


class TestEnsureSessionActive:
    """Test the _ensure_session_active helper method."""

    @pytest.fixture
    def mock_db_tracker(self):
        """Create a mock database tracker."""
        tracker = MagicMock()
        tracker.repository = MagicMock()
        tracker.repository.get_session = AsyncMock()
        tracker.repository.update_session = AsyncMock()
        tracker.repository.list_sessions = AsyncMock(return_value=[])
        tracker.repository.initialize = AsyncMock()
        return tracker

    @pytest.fixture
    def session_manager(self, mock_db_tracker):
        """Create a SessionManager with mocked dependencies."""
        from collab_sims.api.services.session_manager import SessionManager

        manager = SessionManager()
        manager.db_tracker = mock_db_tracker
        return manager

    async def test_ensure_session_active_returns_true_if_in_memory(self, session_manager):
        """Test that _ensure_session_active returns True if session is already active."""
        session_id = "active-session"
        session_manager._sessions[session_id] = {"session_id": session_id}

        result = await session_manager._ensure_session_active(session_id)

        assert result is True

    async def test_ensure_session_active_calls_reactivate_if_not_in_memory(
        self, session_manager, mock_db_tracker
    ):
        """Test that _ensure_session_active calls _reactivate_session if session not in memory."""
        session_id = "inactive-session"
        mock_db_tracker.repository.get_session.return_value = None

        result = await session_manager._ensure_session_active(session_id)

        assert result is False
        mock_db_tracker.repository.get_session.assert_called_once_with(session_id)


class TestQuerySessionReactivation:
    """Test that query methods reactivate sessions automatically."""

    @pytest.fixture
    def mock_db_tracker(self):
        """Create a mock database tracker."""
        tracker = MagicMock()
        tracker.repository = MagicMock()
        tracker.repository.get_session = AsyncMock()
        tracker.repository.update_session = AsyncMock()
        tracker.repository.list_sessions = AsyncMock(return_value=[])
        tracker.repository.initialize = AsyncMock()
        return tracker

    @pytest.fixture
    def session_manager(self, mock_db_tracker):
        """Create a SessionManager with mocked dependencies."""
        from collab_sims.api.services.session_manager import SessionManager

        manager = SessionManager()
        manager.db_tracker = mock_db_tracker
        return manager

    async def test_query_session_returns_error_if_session_not_found(
        self, session_manager, mock_db_tracker
    ):
        """Test that query_session returns error if session cannot be reactivated."""
        session_id = "nonexistent-session"
        mock_db_tracker.repository.get_session.return_value = None

        events, status, error = await session_manager.query_session(session_id, "test prompt")

        assert events == []
        assert status == "error"
        assert f"Session {session_id} not found" in error

    @patch("collab_sims.api.services.session_manager.CollabSimsSession")
    @patch("collab_sims.api.services.session_manager.StreamTracker")
    async def test_query_session_reactivates_closed_session(
        self, mock_stream_tracker_class, mock_collab_session_class, session_manager, mock_db_tracker
    ):
        """Test that query_session reactivates a closed session before executing."""
        session_id = "closed-session"
        mock_db_tracker.repository.get_session.return_value = {
            "session_id": session_id,
            "project_name": "test-project",
            "agent_name": None,
            "session_name": "Test",
            "user_id": None,
            "metadata": {},
            "query_count": 0,
            "status": "closed",
            "created_at": datetime.now(),
        }

        # Mock CollabSimsSession
        mock_claude_session = MagicMock()
        mock_claude_session._connect = AsyncMock()

        # Mock query to return empty async generator
        async def mock_query(prompt):
            return
            yield  # Make it a generator

        mock_claude_session.query = mock_query
        mock_collab_session_class.return_value = mock_claude_session

        # Execute query - should reactivate session first
        events, status, error = await session_manager.query_session(session_id, "test prompt")

        # Verify session was reactivated
        assert session_id in session_manager._sessions
        mock_db_tracker.repository.update_session.assert_called_with(
            session_id=session_id, status="active"
        )


class TestQuerySessionStreamReactivation:
    """Test that query_session_stream reactivates sessions automatically."""

    @pytest.fixture
    def mock_db_tracker(self):
        """Create a mock database tracker."""
        tracker = MagicMock()
        tracker.repository = MagicMock()
        tracker.repository.get_session = AsyncMock()
        tracker.repository.update_session = AsyncMock()
        tracker.repository.list_sessions = AsyncMock(return_value=[])
        tracker.repository.initialize = AsyncMock()
        return tracker

    @pytest.fixture
    def session_manager(self, mock_db_tracker):
        """Create a SessionManager with mocked dependencies."""
        from collab_sims.api.services.session_manager import SessionManager

        manager = SessionManager()
        manager.db_tracker = mock_db_tracker
        return manager

    async def test_query_session_stream_returns_error_if_session_not_found(
        self, session_manager, mock_db_tracker
    ):
        """Test that query_session_stream yields error if session cannot be reactivated."""
        session_id = "nonexistent-session"
        mock_db_tracker.repository.get_session.return_value = None

        events = []
        async for event in session_manager.query_session_stream(session_id, "test prompt"):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert f"Session {session_id} not found" in events[0]["error"]


class TestCloseSessionUpdatesDatabase:
    """Test that close_session marks sessions as closed in database."""

    @pytest.fixture
    def mock_db_tracker(self):
        """Create a mock database tracker."""
        tracker = MagicMock()
        tracker.repository = MagicMock()
        tracker.repository.get_session = AsyncMock()
        tracker.repository.update_session = AsyncMock()
        tracker.repository.list_sessions = AsyncMock(return_value=[])
        tracker.repository.initialize = AsyncMock()
        return tracker

    @pytest.fixture
    def session_manager(self, mock_db_tracker):
        """Create a SessionManager with mocked dependencies."""
        from collab_sims.api.services.session_manager import SessionManager

        manager = SessionManager()
        manager.db_tracker = mock_db_tracker
        return manager

    async def test_close_session_returns_false_if_not_in_memory(self, session_manager):
        """Test that close_session returns False if session not in memory."""
        session_id = "nonexistent-session"

        result = await session_manager.close_session(session_id)

        assert result is False

    async def test_close_session_marks_as_closed_in_database(
        self, session_manager, mock_db_tracker
    ):
        """Test that close_session updates status to 'closed' in database."""
        session_id = "active-session"

        # Add session to memory (without claude_session to avoid close() call)
        session_manager._sessions[session_id] = {
            "session_id": session_id,
            "project_name": "test-project",
            "status": "active",
        }

        result = await session_manager.close_session(session_id)

        assert result is True
        assert session_id not in session_manager._sessions

        # Verify database was updated
        mock_db_tracker.repository.update_session.assert_called_once()
        call_kwargs = mock_db_tracker.repository.update_session.call_args.kwargs
        assert call_kwargs["session_id"] == session_id
        assert call_kwargs["status"] == "closed"
        assert "closed_at" in call_kwargs

    async def test_close_session_closes_claude_session(self, session_manager, mock_db_tracker):
        """Test that close_session closes the Claude session gracefully."""
        session_id = "active-session"

        # Create mock Claude session
        mock_claude_session = MagicMock()
        mock_claude_session.close = AsyncMock()

        # Add session to memory with claude_session
        session_manager._sessions[session_id] = {
            "session_id": session_id,
            "project_name": "test-project",
            "status": "active",
            "claude_session": mock_claude_session,
        }

        result = await session_manager.close_session(session_id)

        assert result is True
        mock_claude_session.close.assert_called_once()


class TestUpdateSessionNameWithoutReactivation:
    """Test that update_session_name works for inactive sessions."""

    @pytest.fixture
    def mock_db_tracker(self):
        """Create a mock database tracker."""
        tracker = MagicMock()
        tracker.repository = MagicMock()
        tracker.repository.update_session_name = AsyncMock()
        tracker.repository.list_sessions = AsyncMock(return_value=[])
        tracker.repository.initialize = AsyncMock()
        return tracker

    @pytest.fixture
    def session_manager(self, mock_db_tracker):
        """Create a SessionManager with mocked dependencies."""
        from collab_sims.api.services.session_manager import SessionManager

        manager = SessionManager()
        manager.db_tracker = mock_db_tracker
        return manager

    async def test_update_session_name_updates_database_for_inactive_session(
        self, session_manager, mock_db_tracker
    ):
        """Test that update_session_name updates database even if session not in memory."""
        session_id = "inactive-session"
        new_name = "Updated Name"

        # Session NOT in memory - should still update database
        await session_manager.update_session_name(session_id, new_name)

        mock_db_tracker.repository.update_session_name.assert_called_once_with(session_id, new_name)

    async def test_update_session_name_updates_memory_if_active(
        self, session_manager, mock_db_tracker
    ):
        """Test that update_session_name also updates memory if session is active."""
        session_id = "active-session"
        new_name = "Updated Name"

        # Add session to memory
        session_manager._sessions[session_id] = {
            "session_id": session_id,
            "session_name": "Old Name",
        }

        await session_manager.update_session_name(session_id, new_name)

        # Verify both database and memory were updated
        mock_db_tracker.repository.update_session_name.assert_called_once_with(session_id, new_name)
        assert session_manager._sessions[session_id]["session_name"] == new_name


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
