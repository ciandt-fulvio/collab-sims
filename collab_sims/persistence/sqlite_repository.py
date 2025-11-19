"""SQLite implementation of SessionRepository."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from .repository import SessionRepository

logger = logging.getLogger(__name__)


class SQLiteRepository(SessionRepository):
    """SQLite implementation of session persistence.

    Uses aiosqlite for async database operations.
    Database schema is automatically created on first connection.
    """

    def __init__(self, db_path: str):
        """Initialize SQLite repository.

        Args:
            db_path: Path to SQLite database file (will be created if doesn't exist)
        """
        self.db_path = db_path
        self.db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize database connection and create schema.

        This is idempotent - safe to call multiple times.
        """
        # Skip if already initialized
        if self.db is not None:
            logger.debug(f"SQLite database at {self.db_path} already initialized, skipping")
            return

        # Ensure parent directory exists
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row  # Return rows as dicts

        # Enable foreign keys
        await self.db.execute("PRAGMA foreign_keys = ON")

        # Create schema
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text()
        await self.db.executescript(schema)
        await self.db.commit()

        logger.info(f"Initialized SQLite database at {self.db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self.db:
            await self.db.close()
            self.db = None

    async def create_session(
        self,
        session_id: str,
        user_id: str | None,
        created_at: datetime,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Create a new session record."""
        metadata_json = json.dumps(metadata) if metadata else None

        await self.db.execute(
            """
            INSERT INTO session (session_id, user_id, created_at, status, query_count, metadata)
            VALUES (?, ?, ?, 'active', 0, ?)
            """,
            (session_id, user_id, created_at.isoformat(), metadata_json)
        )
        await self.db.commit()
        logger.debug(f"Created session {session_id}")

    async def update_session(
        self,
        session_id: str,
        closed_at: datetime | None = None,
        status: str | None = None,
        query_count: int | None = None
    ) -> None:
        """Update session record."""
        updates = []
        params = []

        if closed_at is not None:
            updates.append("closed_at = ?")
            params.append(closed_at.isoformat())

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if query_count is not None:
            updates.append("query_count = ?")
            params.append(query_count)

        if not updates:
            return

        params.append(session_id)
        query = f"UPDATE session SET {', '.join(updates)} WHERE session_id = ?"

        await self.db.execute(query, params)
        await self.db.commit()
        logger.debug(f"Updated session {session_id}")

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM session WHERE session_id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        result = dict(row)
        # Parse JSON metadata
        if result.get("metadata"):
            result["metadata"] = json.loads(result["metadata"])

        return result

    async def list_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering."""
        query = "SELECT * FROM session WHERE 1=1"
        params = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON metadata
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            results.append(result)

        return results

    async def count_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None
    ) -> int:
        """Count sessions matching criteria."""
        query = "SELECT COUNT(*) as count FROM session WHERE 1=1"
        params = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        cursor = await self.db.execute(query, params)
        row = await cursor.fetchone()
        return row["count"] if row else 0

    async def add_event(
        self,
        session_id: str,
        event_type: str,
        timestamp: datetime,
        data: dict[str, Any],
        query_index: int | None = None,
        message_id: str | None = None
    ) -> None:
        """Add an event to the database."""
        data_json = json.dumps(data)

        await self.db.execute(
            """
            INSERT INTO event (session_id, event_type, timestamp, data, query_index, message_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, event_type, timestamp.isoformat(), data_json, query_index, message_id)
        )
        await self.db.commit()

    async def get_events(
        self,
        session_id: str,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get events for a session."""
        query = "SELECT * FROM event WHERE session_id = ?"
        params = [session_id]

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY event_id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON data
            if result.get("data"):
                result["data"] = json.loads(result["data"])
            results.append(result)

        return results

    async def count_events(
        self,
        session_id: str,
        event_type: str | None = None
    ) -> int:
        """Count events for a session."""
        query = "SELECT COUNT(*) as count FROM event WHERE session_id = ?"
        params = [session_id]

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)

        cursor = await self.db.execute(query, params)
        row = await cursor.fetchone()
        return row["count"] if row else 0

    async def delete_session(self, session_id: str) -> None:
        """Delete session and all its events (CASCADE)."""
        await self.db.execute(
            "DELETE FROM session WHERE session_id = ?",
            (session_id,)
        )
        await self.db.commit()
        logger.debug(f"Deleted session {session_id}")
