"""Unit tests for SQLiteRepository.

Tests the SQLite implementation of SessionRepository, including:
- Database initialization and schema creation
- Session CRUD operations
- Event storage and retrieval
- Filtering and pagination
- Cascade deletion

References:
- https://docs.python.org/3/library/sqlite3.html
- https://aiosqlite.omnilib.dev/en/stable/
"""

from datetime import datetime, timedelta

import pytest

from collab_sims.persistence.sqlite_repository import SQLiteRepository


class TestSQLiteRepositoryInitialization:
    """Test database initialization and connection."""

    async def test_initialize_creates_database(self, temp_db_path):
        """Test that initialize creates database and schema."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()

        # Verify database is connected
        assert repo.db is not None

        # Verify tables exist
        cursor = await repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in await cursor.fetchall()]
        assert "session" in tables
        assert "event" in tables

        await repo.close()

    async def test_initialize_is_idempotent(self, temp_db_path):
        """Test that calling initialize multiple times is safe."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()
        await repo.initialize()  # Should not raise

        assert repo.db is not None
        await repo.close()

    async def test_close_disconnects_database(self, temp_db_path):
        """Test that close properly disconnects."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()
        await repo.close()

        assert repo.db is None


class TestSQLiteRepositorySessionOperations:
    """Test session CRUD operations."""

    @pytest.fixture
    async def repo(self, temp_db_path):
        """Create and initialize a repository for testing."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()
        yield repo
        await repo.close()

    async def test_create_session_basic(self, repo):
        """Test creating a basic session."""
        session_id = "test-session-123"
        user_id = "user-456"
        created_at = datetime.now()

        await repo.create_session(session_id, user_id, created_at, project_name="test-project")

        # Verify session was created
        session = await repo.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["user_id"] == user_id
        assert session["status"] == "active"
        assert session["query_count"] == 0

    async def test_create_session_with_metadata(self, repo):
        """Test creating session with metadata."""
        session_id = "test-session-456"
        metadata = {"role": "worker", "tags": ["dev", "test"]}
        created_at = datetime.now()

        await repo.create_session(
            session_id, None, created_at, project_name="test-project", metadata=metadata
        )

        session = await repo.get_session(session_id)
        assert session["metadata"] == metadata

    async def test_update_session_status(self, repo):
        """Test updating session status."""
        session_id = "test-session-789"
        await repo.create_session(session_id, None, datetime.now(), project_name="test-project")

        # Update status
        await repo.update_session(session_id, status="closed")

        session = await repo.get_session(session_id)
        assert session["status"] == "closed"

    async def test_update_session_query_count(self, repo):
        """Test updating session query count."""
        session_id = "test-session-101"
        await repo.create_session(session_id, None, datetime.now(), project_name="test-project")

        await repo.update_session(session_id, query_count=5)

        session = await repo.get_session(session_id)
        assert session["query_count"] == 5

    async def test_update_session_closed_at(self, repo):
        """Test updating session closed_at timestamp."""
        session_id = "test-session-102"
        await repo.create_session(session_id, None, datetime.now(), project_name="test-project")

        closed_at = datetime.now()
        await repo.update_session(session_id, closed_at=closed_at)

        session = await repo.get_session(session_id)
        assert session["closed_at"] is not None

    async def test_get_session_not_found(self, repo):
        """Test getting non-existent session returns None."""
        session = await repo.get_session("non-existent")
        assert session is None

    async def test_delete_session(self, repo):
        """Test deleting a session."""
        session_id = "test-session-delete"
        await repo.create_session(session_id, None, datetime.now(), project_name="test-project")

        await repo.delete_session(session_id)

        session = await repo.get_session(session_id)
        assert session is None


class TestSQLiteRepositorySessionListing:
    """Test session listing and filtering."""

    @pytest.fixture
    async def repo_with_sessions(self, temp_db_path):
        """Create repository with test sessions."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()

        # Create multiple test sessions
        base_time = datetime.now()
        sessions = [
            ("session-1", "user-1", "active", base_time),
            ("session-2", "user-1", "closed", base_time + timedelta(minutes=1)),
            ("session-3", "user-2", "active", base_time + timedelta(minutes=2)),
            ("session-4", None, "active", base_time + timedelta(minutes=3)),
        ]

        for session_id, user_id, status, created_at in sessions:
            await repo.create_session(session_id, user_id, created_at, project_name="test-project")
            # Add at least 1 query to each session so they pass the query_count > 0 filter
            await repo.update_session(session_id, query_count=1)
            if status != "active":
                await repo.update_session(session_id, status=status)

        yield repo
        await repo.close()

    async def test_list_all_sessions(self, repo_with_sessions):
        """Test listing all sessions."""
        sessions = await repo_with_sessions.list_sessions()
        assert len(sessions) == 4

    async def test_list_sessions_by_user(self, repo_with_sessions):
        """Test filtering sessions by user_id."""
        sessions = await repo_with_sessions.list_sessions(user_id="user-1")
        assert len(sessions) == 2
        assert all(s["user_id"] == "user-1" for s in sessions)

    async def test_list_sessions_by_status(self, repo_with_sessions):
        """Test filtering sessions by status."""
        sessions = await repo_with_sessions.list_sessions(status="active")
        assert len(sessions) == 3
        assert all(s["status"] == "active" for s in sessions)

    async def test_list_sessions_with_pagination(self, repo_with_sessions):
        """Test session pagination."""
        # First page
        page1 = await repo_with_sessions.list_sessions(limit=2, offset=0)
        assert len(page1) == 2

        # Second page
        page2 = await repo_with_sessions.list_sessions(limit=2, offset=2)
        assert len(page2) == 2

        # No overlap
        page1_ids = {s["session_id"] for s in page1}
        page2_ids = {s["session_id"] for s in page2}
        assert len(page1_ids & page2_ids) == 0

    async def test_count_sessions(self, repo_with_sessions):
        """Test counting sessions."""
        total = await repo_with_sessions.count_sessions()
        assert total == 4

    async def test_count_sessions_filtered(self, repo_with_sessions):
        """Test counting filtered sessions."""
        count = await repo_with_sessions.count_sessions(status="active")
        assert count == 3


class TestSQLiteRepositoryEventOperations:
    """Test event storage and retrieval."""

    @pytest.fixture
    async def repo_with_session(self, temp_db_path):
        """Create repository with a test session."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()

        # Create test session
        await repo.create_session(
            "test-session", "user-1", datetime.now(), project_name="test-project"
        )

        yield repo
        await repo.close()

    async def test_add_event_basic(self, repo_with_session):
        """Test adding a basic event."""
        event_data = {"type": "message", "role": "assistant", "content": "Hello!"}

        await repo_with_session.add_event(
            session_id="test-session",
            event_type="message",
            timestamp=datetime.now(),
            data=event_data,
        )

        events = await repo_with_session.get_events("test-session")
        assert len(events) == 1
        assert events[0]["event_type"] == "message"
        assert events[0]["data"] == event_data

    async def test_add_event_with_query_index(self, repo_with_session):
        """Test adding event with query index."""
        event_data = {"type": "query", "prompt": "test"}

        await repo_with_session.add_event(
            session_id="test-session",
            event_type="query",
            timestamp=datetime.now(),
            data=event_data,
            query_index=1,
        )

        events = await repo_with_session.get_events("test-session")
        assert events[0]["query_index"] == 1

    async def test_add_event_with_message_id(self, repo_with_session):
        """Test adding event with message ID."""
        event_data = {"type": "tool_use"}

        await repo_with_session.add_event(
            session_id="test-session",
            event_type="tool_use",
            timestamp=datetime.now(),
            data=event_data,
            message_id="msg_123",
        )

        events = await repo_with_session.get_events("test-session")
        assert events[0]["message_id"] == "msg_123"

    async def test_get_events_filtered_by_type(self, repo_with_session):
        """Test filtering events by type."""
        # Add multiple events of different types
        timestamp = datetime.now()
        for event_type in ["message", "tool_use", "message"]:
            await repo_with_session.add_event(
                session_id="test-session",
                event_type=event_type,
                timestamp=timestamp,
                data={"type": event_type},
            )

        # Filter by type
        messages = await repo_with_session.get_events("test-session", event_type="message")
        assert len(messages) == 2
        assert all(e["event_type"] == "message" for e in messages)

    async def test_get_events_with_pagination(self, repo_with_session):
        """Test event pagination."""
        # Add multiple events
        timestamp = datetime.now()
        for i in range(5):
            await repo_with_session.add_event(
                session_id="test-session",
                event_type="message",
                timestamp=timestamp,
                data={"index": i},
            )

        # Get first page
        page1 = await repo_with_session.get_events("test-session", limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = await repo_with_session.get_events("test-session", limit=2, offset=2)
        assert len(page2) == 2

    async def test_count_events(self, repo_with_session):
        """Test counting events."""
        # Add events
        timestamp = datetime.now()
        for i in range(3):
            await repo_with_session.add_event(
                session_id="test-session",
                event_type="message",
                timestamp=timestamp,
                data={"index": i},
            )

        count = await repo_with_session.count_events("test-session")
        assert count == 3

    async def test_count_events_filtered(self, repo_with_session):
        """Test counting filtered events."""
        timestamp = datetime.now()
        for event_type in ["message", "tool_use", "message"]:
            await repo_with_session.add_event(
                session_id="test-session",
                event_type=event_type,
                timestamp=timestamp,
                data={"type": event_type},
            )

        count = await repo_with_session.count_events("test-session", event_type="message")
        assert count == 2


class TestSQLiteRepositoryCascadeDeletion:
    """Test cascade deletion of events when session is deleted."""

    @pytest.fixture
    async def repo(self, temp_db_path):
        """Create and initialize a repository for testing."""
        repo = SQLiteRepository(temp_db_path)
        await repo.initialize()
        yield repo
        await repo.close()

    async def test_delete_session_cascades_events(self, repo):
        """Test that deleting session also deletes its events."""
        # Create session and add events
        session_id = "test-cascade"
        await repo.create_session(session_id, None, datetime.now(), project_name="test-project")

        timestamp = datetime.now()
        for i in range(3):
            await repo.add_event(
                session_id=session_id, event_type="message", timestamp=timestamp, data={"index": i}
            )

        # Verify events exist
        events_before = await repo.get_events(session_id)
        assert len(events_before) == 3

        # Delete session
        await repo.delete_session(session_id)

        # Verify events are also deleted
        events_after = await repo.get_events(session_id)
        assert len(events_after) == 0


if __name__ == "__main__":
    import sys

    # Run tests with pytest
    sys.exit(pytest.main([__file__, "-v"]))
