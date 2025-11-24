"""Service for managing multi-turn sessions"""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

# Import from collab_sims core
from ...core import CollabSimsSession, SessionConfig
from ...core.events import AgentEvent
from ...persistence import SQLiteRepository
from ...trackers import DatabaseTracker, StreamTracker
from .approval_manager import ApprovalManager

logger = logging.getLogger(__name__)


@dataclass
class QueryTask:
    """Represents a running query in background"""
    query_id: str
    session_id: str
    prompt: str
    task: asyncio.Task
    status: str  # "running", "completed", "error"
    created_at: datetime
    error: str | None = None


class SessionManager:
    """
    Manages lifecycle of sessions without CollabSims SDK.

    Responsibilities:
    - Create/destroy sessions
    - Track session metadata
    - Execute queries within session context (simulated)
    - Provide event streaming per query
    """

    def __init__(self, approval_manager: ApprovalManager | None = None):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._active_queries: dict[str, QueryTask] = {}
        self._event_subscribers: dict[str, list[asyncio.Queue]] = {}
        self.approval_manager = approval_manager or ApprovalManager()
        self._cleanup_task: asyncio.Task | None = None

        # Initialize database tracker for persistence
        self.db_tracker = self._init_database_tracker()

        # Session restore status
        self._restore_status = "not_started"  # not_started, in_progress, completed, failed
        self._restore_count = 0
        self._restore_failed_count = 0

    def _init_database_tracker(self) -> DatabaseTracker:
        """Initialize database tracker with SQLite repository.

        Database location: ./api_sessions.db (configurable via COLLAB_SIMS_DB_PATH)
        """
        # Get database path from env or use default
        db_path = os.getenv("COLLAB_SIMS_DB_PATH", "./data/api_sessions.db")

        # Create repository and tracker
        repository = SQLiteRepository(db_path)
        return DatabaseTracker(repository)

    async def restore_sessions_from_database(self):
        """Restore active sessions from database on server startup.

        Uses Claude Agent SDK's resume feature to restore sessions with their conversation history.
        Sessions are recreated in memory and can continue receiving queries.

        This runs asynchronously in the background to avoid blocking server startup.
        """
        self._restore_status = "in_progress"
        logger.info("🔄 Starting session restore (background task)...")

        try:
            # Get all active sessions from database
            active_sessions = await self.db_tracker.repository.list_sessions(
                status="active",
                limit=1000
            )

            if not active_sessions:
                logger.info("   No active sessions to restore")
                self._restore_status = "completed"
                return

            logger.info(f"   Found {len(active_sessions)} active session(s) to restore")

            restored_count = 0
            failed_count = 0

            for session_data in active_sessions:
                session_id = session_data["session_id"]
                try:
                    # Extract fields from database
                    project_name = session_data.get("project_name")
                    if not project_name:
                        logger.warning(f"   ⚠️  Session {session_id} has no project_name, skipping restore")
                        continue

                    agent_name = session_data.get("agent_name")
                    session_name = session_data.get("session_name")
                    user_id = session_data.get("user_id")
                    metadata = session_data.get("metadata", {})

                    # Create session config from stored metadata
                    config_dict = dict(metadata)
                    if user_id:
                        config_dict["user_id"] = user_id

                    # Create stream tracker for this session
                    stream_tracker = StreamTracker()

                    # Create session configuration
                    session_config = SessionConfig(
                        project_name=project_name,
                        agent_name=agent_name,
                        include_partial_messages=config_dict.get("include_partial_messages", True),
                        user_id=user_id,
                    )

                    # Create CollabSimsSession with resume=True
                    claude_session = CollabSimsSession(
                        options=ClaudeAgentOptions(
                            permission_mode="bypassPermissions",
                            include_partial_messages=session_config.include_partial_messages
                        ),
                        config=session_config,
                        trackers=[self.db_tracker, stream_tracker],
                        approval_manager=self.approval_manager,
                        session_id=session_id,
                        resume=True,  # ✅ Resume existing session
                    )

                    # Connect (will use resume parameter)
                    await claude_session._connect()

                    # Get query count from database
                    query_count = session_data.get("query_count", 0)

                    # Store session data in memory
                    self._sessions[session_id] = {
                        "session_id": session_id,
                        "project_name": project_name,
                        "agent_name": agent_name,
                        "session_name": session_name,
                        "tracker": stream_tracker,
                        "claude_session": claude_session,
                        "config": config_dict,
                        "created_at": session_data.get("created_at", datetime.now()).isoformat()
                                     if isinstance(session_data.get("created_at"), datetime)
                                     else session_data.get("created_at", datetime.now().isoformat()),
                        "status": "active",
                        "execution_state": "idle",
                        "current_query_id": None,
                        "query_count": query_count,
                    }

                    restored_count += 1
                    logger.debug(f"   ✅ Resumed session {session_id[:12]} (queries: {query_count})")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"   ❌ Failed to resume session {session_id}: {e}")
                    # Mark failed session as closed
                    try:
                        await self.db_tracker.repository.update_session(
                            session_id=session_id,
                            status="closed",
                            closed_at=datetime.now()
                        )
                    except Exception:
                        pass

            # Update restore status
            self._restore_count = restored_count
            self._restore_failed_count = failed_count

            if restored_count > 0:
                logger.info(f"   ✅ Restored {restored_count} session(s) in background")
            if failed_count > 0:
                logger.warning(f"   ⚠️  Failed to restore {failed_count} session(s)")

            self._restore_status = "completed"
            logger.info("🏁 Session restore completed")

        except Exception as e:
            self._restore_status = "failed"
            logger.error(f"❌ Session restore failed: {e}")

    def _ensure_cleanup_task_started(self):
        """Start the cleanup task if not already running (lazy initialization)"""
        if self._cleanup_task is None:
            # Don't start cleanup task during tests
            import os
            if os.environ.get('PYTEST_CURRENT_TEST'):
                return

            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_completed_queries())
            except RuntimeError:
                # No event loop running yet
                pass

    async def create_session(
        self,
        project_name: str,
        agent_name: str | None = None,
        config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a new multi-turn session.

        Args:
            project_name: Project name (references MD file in data/projects/) - REQUIRED
            agent_name: Agent persona to use (references MD file in data/agents/)
            config: Optional session configuration

        Returns:
            Session metadata
        """
        # Ensure cleanup task is running
        self._ensure_cleanup_task_started()

        # Generate pure UUID (Claude SDK requires valid UUID format)
        session_id = str(uuid.uuid4())
        created_at = datetime.now()

        # Create trackers for this session
        stream_tracker = StreamTracker()

        # Create session in database with project_name and agent_name
        await self.db_tracker.repository.create_session(
            session_id=session_id,
            project_name=project_name,
            agent_name=agent_name,
            session_name=None,  # Will be auto-generated from first prompt
            user_id=config.get("user_id") if config else None,
            created_at=created_at,
            metadata=config or {}
        )

        # Create CollabSimsSession for real Claude integration
        session_config = SessionConfig(
            project_name=project_name,
            agent_name=agent_name,
            include_partial_messages=config.get("include_partial_messages", True) if config else True,
            user_id=config.get("user_id") if config else None,
        )

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",  # Use approval_manager instead
            include_partial_messages=session_config.include_partial_messages
        )

        claude_session = CollabSimsSession(
            options=options,
            config=session_config,
            trackers=[self.db_tracker, stream_tracker],
            approval_manager=self.approval_manager,
            session_id=session_id,
        )

        # Connect the session to Claude SDK
        await claude_session._connect()

        # Store session data in memory
        self._sessions[session_id] = {
            "session_id": session_id,
            "project_name": project_name,
            "agent_name": agent_name,
            "session_name": None,  # Will be set on first query
            "tracker": stream_tracker,
            "claude_session": claude_session,  # Store the real session
            "config": config or {},
            "created_at": created_at.isoformat(),
            "status": "active",
            "execution_state": "idle",  # Query execution state: "idle" | "executing"
            "current_query_id": None,  # ID of currently executing query (if any)
            "query_count": 0,
        }

        logger.info(f"Created session {session_id} for project '{project_name}' with agent '{agent_name or 'default'}'")

        return self._get_session_metadata(session_id)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session metadata"""
        # Check in-memory first (active sessions)
        if session_id in self._sessions:
            return self._get_session_metadata(session_id)

        # Fall back to database (sessions from previous runs)
        try:
            db_session = await self.db_tracker.repository.get_session(session_id)
            if db_session:
                return self._normalize_db_session(db_session)
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id} from database: {e}")
            return None

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions in memory.

        Active sessions are restored from database on startup using resume feature,
        so this returns all sessions that can receive queries.

        Returns:
            List of session metadata dicts
        """
        return [self._get_session_metadata(sid) for sid in self._sessions.keys()]

    async def query_session(
        self, session_id: str, prompt: str
    ) -> tuple[list[dict[str, Any]], str, str | None]:
        """
        Execute a query in a session context (buffered).

        Args:
            session_id: Session identifier
            prompt: User prompt

        Returns:
            Tuple of (events, status, error_message)
        """
        if session_id not in self._sessions:
            return [], "error", f"Session {session_id} not found"

        session_data = self._sessions[session_id]
        claude_session: CollabSimsSession = session_data["claude_session"]

        try:
            # Auto-generate session_name from first prompt (first 50 chars)
            if session_data["session_name"] is None and session_data["query_count"] == 0:
                session_name = prompt[:50].strip()
                session_data["session_name"] = session_name
                # Save to database
                await self.db_tracker.repository.update_session_name(
                    session_id=session_id,
                    session_name=session_name
                )
                logger.debug(f"Auto-generated session_name for {session_id}: {session_name}")

            # Execute real query using Claude SDK and collect all events
            events = []
            async for event in claude_session.query(prompt):
                event_dict = self._agent_event_to_dict(event, session_id)
                events.append(event_dict)

            # Update query count
            session_data["query_count"] += 1

            return events, "completed", None

        except Exception as e:
            logger.error(f"Error in query_session: {e}")
            return [], "error", str(e)

    async def _broadcast_event(self, session_id: str, event: dict[str, Any]):
        """Broadcast event to all SSE subscribers for this session"""
        if session_id in self._event_subscribers:
            # Send to all connected clients
            dead_queues = []
            for queue in self._event_subscribers[session_id]:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    dead_queues.append(queue)

            # Cleanup dead queues
            for queue in dead_queues:
                self._event_subscribers[session_id].remove(queue)

    async def subscribe_to_session_events(self, session_id: str) -> AsyncGenerator[dict[str, Any]]:
        """Subscribe to live events for a session (SSE-friendly)

        Args:
            session_id: Session identifier

        Yields:
            Events as they occur in real-time
        """
        queue = asyncio.Queue()

        if session_id not in self._event_subscribers:
            self._event_subscribers[session_id] = []
        self._event_subscribers[session_id].append(queue)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            # Cleanup on SSE disconnect
            if session_id in self._event_subscribers:
                try:
                    self._event_subscribers[session_id].remove(queue)
                    if not self._event_subscribers[session_id]:
                        del self._event_subscribers[session_id]
                except (ValueError, KeyError):
                    pass

    def _get_active_query_for_session(self, session_id: str) -> QueryTask | None:
        """Get currently running query for a session (if any)"""
        for query in self._active_queries.values():
            if query.session_id == session_id and query.status == "running":
                return query
        return None

    async def start_query_background(self, session_id: str, prompt: str) -> str:
        """Start a query in background (continues even if SSE disconnects)

        Args:
            session_id: Session identifier
            prompt: User prompt

        Returns:
            query_id: Unique identifier for this query

        Raises:
            ValueError: If session not found
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        query_id = f"{session_id}_{uuid.uuid4().hex[:8]}"
        session_data = self._sessions[session_id]

        # Transition: idle -> executing
        logger.info(f"🔄 Session {session_id[:12]} transitioning: idle -> executing (query: {query_id})")
        session_data["execution_state"] = "executing"
        session_data["current_query_id"] = query_id

        # Create background task
        task = asyncio.create_task(
            self._execute_query_background(prompt, query_id, session_id)
        )

        # Track the query
        self._active_queries[query_id] = QueryTask(
            query_id=query_id,
            session_id=session_id,
            prompt=prompt,
            task=task,
            status="running",
            created_at=datetime.now(),
        )

        return query_id

    def _agent_event_to_dict(self, event: AgentEvent, session_id: str) -> dict[str, Any]:
        """Convert AgentEvent from Claude SDK to dict format for API

        Args:
            event: AgentEvent from Claude SDK
            session_id: Session ID to add to event

        Returns:
            Dict representation of the event
        """
        from dataclasses import asdict, is_dataclass

        # Handle timestamp - it may already be a string (from AgentEvent default)
        timestamp = getattr(event, 'timestamp', datetime.now())
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        event_dict = {
            "type": event.type.value if hasattr(event.type, 'value') else str(event.type),
            "event_id": getattr(event, 'event_id', str(uuid.uuid4())),
            "timestamp": timestamp,
            "session_id": session_id,
        }

        # Add event-specific fields
        if hasattr(event, '__dict__'):
            for key, value in event.__dict__.items():
                if key not in ['type', 'event_id', 'timestamp'] and not key.startswith('_'):
                    # Convert datetime objects to ISO format
                    if isinstance(value, datetime):
                        event_dict[key] = value.isoformat()
                    # Convert dataclass objects to dictionaries
                    elif is_dataclass(value) and not isinstance(value, type):
                        event_dict[key] = asdict(value)
                    # Convert lists of dataclass objects
                    elif isinstance(value, list) and value and is_dataclass(value[0]) and not isinstance(value[0], type):
                        event_dict[key] = [asdict(item) for item in value]
                    # Skip non-serializable objects
                    elif not callable(value):
                        event_dict[key] = value

        return event_dict

    async def _simulate_agent_response(self, prompt: str, session_id: str) -> list[dict[str, Any]]:
        """Simulate an agent response (DEPRECATED - use real Claude SDK instead)"""
        logger.warning("Using simulated agent response - this should not happen in production")
        events = []

        # Event: Query started
        query_event = {
            "type": "query",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "prompt": prompt,
            "query_number": self._sessions[session_id]["query_count"] + 1,
        }
        events.append(query_event)

        # Event: Complete message
        message_text = f"Entendi sua pergunta: '{prompt}'. Esta é uma resposta simulada."
        message_event = {
            "type": "message",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "role": "assistant",
            "content": message_text,
        }
        events.append(message_event)

        # Event: Complete
        complete_event = {
            "type": "complete",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "metrics": {
                "input_tokens": 50,
                "output_tokens": 30,
                "total_cost_usd": 0.001,
            },
            "duration_ms": 500,
            "num_turns": 1,
        }
        events.append(complete_event)

        # Save events to database
        for event in events:
            await self.db_tracker.repository.add_event(
                session_id=session_id,
                event_type=event["type"],
                timestamp=datetime.fromisoformat(event["timestamp"]),
                data=event,
            )

        return events

    async def _execute_query_background(self, prompt: str, query_id: str, session_id: str):
        """Background task that executes real Claude query and broadcasts events

        This task continues running even if SSE disconnects.
        Events are captured by DatabaseTracker and broadcast to live subscribers.
        """
        try:
            session_data = self._sessions[session_id]
            claude_session: CollabSimsSession = session_data["claude_session"]

            logger.debug(f"Starting query execution for {query_id} in session {session_id[:12]}")

            # Execute real query using Claude SDK
            async for event in claude_session.query(prompt):
                # Convert AgentEvent to dict for broadcasting
                event_dict = self._agent_event_to_dict(event, session_id)

                # Broadcast event to SSE subscribers
                await self._broadcast_event(session_id, event_dict)

            logger.debug(f"Query {query_id} completed successfully")

            # Mark as completed
            if query_id in self._active_queries:
                self._active_queries[query_id].status = "completed"

            # Update session query count
            if session_id in self._sessions:
                self._sessions[session_id]["query_count"] += 1

        except asyncio.CancelledError:
            logger.info(f"Query {query_id} was cancelled")
            if query_id in self._active_queries:
                self._active_queries[query_id].status = "cancelled"
            raise
        except Exception as e:
            # Log full exception details for debugging
            import traceback
            logger.error(f"Error executing query {query_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")

            # Mark as error
            if query_id in self._active_queries:
                self._active_queries[query_id].status = "error"
                self._active_queries[query_id].error = str(e)

            # Broadcast error event
            error_event = {
                'type': 'error',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id,
                'event_id': str(uuid.uuid4()),
            }
            await self._broadcast_event(session_id, error_event)

        finally:
            # Transition: executing -> idle
            if session_id in self._sessions:
                logger.info(f"🔄 Session {session_id[:12]} transitioning: executing -> idle")
                self._sessions[session_id]["execution_state"] = "idle"
                self._sessions[session_id]["current_query_id"] = None

    async def _simulate_agent_response_streaming(self, prompt: str, session_id: str) -> list[dict[str, Any]]:
        """Simulate streaming agent response with partial messages"""
        events = []

        # Event: Query started
        query_event = {
            "type": "query",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "prompt": prompt,
            "query_number": self._sessions[session_id]["query_count"] + 1,
        }
        events.append(query_event)
        await self.db_tracker.repository.add_event(
            session_id=session_id,
            event_type="query",
            timestamp=datetime.fromisoformat(query_event["timestamp"]),
            data=query_event,
        )

        # Event: Partial messages (word by word)
        message_text = f"Entendi sua pergunta: '{prompt}'. Esta é uma resposta simulada."
        words = message_text.split()
        for i, word in enumerate(words):
            partial = {
                "type": "partial_message",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "delta": word + " ",
                "index": i,
            }
            events.append(partial)
            await self.db_tracker.repository.add_event(
                session_id=session_id,
                event_type="partial_message",
                timestamp=datetime.fromisoformat(partial["timestamp"]),
                data=partial,
            )

        # Event: Complete message
        message_event = {
            "type": "message",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "role": "assistant",
            "content": message_text,
        }
        events.append(message_event)
        await self.db_tracker.repository.add_event(
            session_id=session_id,
            event_type="message",
            timestamp=datetime.fromisoformat(message_event["timestamp"]),
            data=message_event,
        )

        # Event: Complete
        complete_event = {
            "type": "complete",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "metrics": {
                "input_tokens": 50,
                "output_tokens": 30,
                "total_cost_usd": 0.001,
            },
            "duration_ms": 500,
            "num_turns": 1,
        }
        events.append(complete_event)
        await self.db_tracker.repository.add_event(
            session_id=session_id,
            event_type="complete",
            timestamp=datetime.fromisoformat(complete_event["timestamp"]),
            data=complete_event,
        )

        return events

    async def _cleanup_completed_queries(self):
        """Periodically clean up old completed queries to prevent memory buildup"""
        try:
            while True:
                await asyncio.sleep(3600)  # Run every hour

                now = datetime.now()
                to_remove = []

                for query_id, query in self._active_queries.items():
                    if query.status in ["completed", "error"]:
                        age = (now - query.created_at).total_seconds()
                        if age > 3600:  # Remove after 1 hour
                            to_remove.append(query_id)

                for query_id in to_remove:
                    del self._active_queries[query_id]

                if to_remove:
                    logger.debug(f"Cleaned up {len(to_remove)} old queries")
        except asyncio.CancelledError:
            logger.debug("Cleanup task cancelled, shutting down")
            raise

    async def query_session_stream(self, session_id: str, prompt: str):
        """
        Execute a query in a session context with SSE streaming.

        The query runs in background and continues even if SSE disconnects.

        Args:
            session_id: Session identifier
            prompt: User prompt

        Yields:
            Events as they occur in real-time
        """
        if session_id not in self._sessions:
            yield {
                "type": "error",
                "error": f"Session {session_id} not found",
                "timestamp": datetime.now().isoformat()
            }
            return

        # Check if there's already a running query for this session
        active_query = self._get_active_query_for_session(session_id)

        if active_query:
            # Query already running - just subscribe to events
            async for event in self.subscribe_to_session_events(session_id):
                yield event
        elif prompt.strip():
            # Start new background query
            try:
                await self.start_query_background(session_id, prompt)

                # Subscribe to live events
                async for event in self.subscribe_to_session_events(session_id):
                    yield event

            except Exception as e:
                yield {
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # Empty prompt - just subscribe to existing events
            async for event in self.subscribe_to_session_events(session_id):
                yield event

    async def interrupt_session(self, session_id: str) -> bool:
        """
        Interrupt the currently executing query in a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was interrupted, False if not found
        """
        if session_id not in self._sessions:
            return False

        # Find active query
        active_query = self._get_active_query_for_session(session_id)
        if active_query and not active_query.task.done():
            # Cancel the task
            active_query.task.cancel()
            active_query.status = "interrupted"
            logger.info(f"Session {session_id} interrupted successfully")

        return True

    async def close_session(self, session_id: str) -> bool:
        """
        Close and remove a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was closed, False if not found
        """
        if session_id not in self._sessions:
            return False

        session_data = self._sessions[session_id]

        # Close the Claude session gracefully
        if "claude_session" in session_data:
            try:
                claude_session: CollabSimsSession = session_data["claude_session"]
                await claude_session.close()
                logger.info(f"Claude session {session_id} closed gracefully")
            except Exception as e:
                logger.error(f"Error closing Claude session: {e}")

        # Mark as closed in database
        try:
            session = await self.db_tracker.repository.get_session(session_id)
            if session:
                # Update status (we'd need an update_session method, but for now just delete)
                pass
        except Exception as e:
            logger.error(f"Error updating session status in database: {e}")

        # Remove from active sessions
        del self._sessions[session_id]

        logger.info(f"Session {session_id} closed")

        return True

    def _normalize_db_session(self, db_session: dict[str, Any]) -> dict[str, Any]:
        """Normalize database session data to match API response format.

        Args:
            db_session: Raw session data from database

        Returns:
            Normalized session data matching SessionResponse schema
        """
        # Extract metadata (stored as JSON in database)
        metadata = db_session.get("metadata", {})

        # Ensure created_at is a string (ISO format)
        created_at = db_session.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif not isinstance(created_at, str):
            created_at = str(created_at)

        return {
            "session_id": db_session.get("session_id", ""),
            "created_at": created_at,
            "config": metadata,  # Database stores config in metadata field
            "status": db_session.get("status", "active"),
            "execution_state": "idle",  # Database sessions are always idle
            "query_count": db_session.get("query_count", 0),
            "session_type": metadata.get("session_type", "worker"),
        }

    def _get_session_metadata(self, session_id: str) -> dict[str, Any]:
        """Extract public metadata for a session"""
        session_data = self._sessions[session_id]

        return {
            "session_id": session_data["session_id"],
            "created_at": session_data["created_at"],
            "config": session_data["config"],
            "status": session_data["status"],
            "execution_state": session_data.get("execution_state", "idle"),
            "query_count": session_data["query_count"],
            "session_type": session_data.get("session_type", "worker"),
        }

    async def shutdown(self):
        """Shutdown session manager and cancel background tasks.

        Sessions are left as 'active' in the database so they can be resumed on restart.
        """
        logger.info("SessionManager shutdown initiated...")

        # Disconnect Claude sessions but keep them as 'active' in database
        session_ids = list(self._sessions.keys())
        if session_ids:
            logger.debug(f"Disconnecting {len(session_ids)} active sessions (keeping as 'active' for resume)")
            for session_id in session_ids:
                try:
                    session_data = self._sessions[session_id]
                    # Close Claude SDK client without emitting session_end event
                    if "claude_session" in session_data:
                        claude_session = session_data["claude_session"]
                        # Disconnect client directly without calling close() (which emits session_end)
                        if claude_session.client:
                            try:
                                await claude_session.client.disconnect()
                            except Exception:
                                pass  # Ignore disconnect errors during shutdown

                    logger.debug(f"Disconnected session {session_id[:12]} (remains active in DB)")
                except Exception as e:
                    logger.warning(f"Error disconnecting session {session_id}: {e}")

        # Cancel all active query tasks
        tasks_to_cancel = []
        for query_id in list(self._active_queries.keys()):
            query_info = self._active_queries[query_id]
            if hasattr(query_info, 'task') and not query_info.task.done():
                query_info.task.cancel()
                tasks_to_cancel.append(query_info.task)

        # Clear data structures
        self._event_subscribers.clear()
        self._active_queries.clear()

        # Wait for query tasks to cancel
        if tasks_to_cancel:
            logger.debug(f"Waiting for {len(tasks_to_cancel)} query tasks to cancel")
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close database
        if self.db_tracker.repository:
            logger.debug("Closing database connection")
            await self.db_tracker.repository.close()

        logger.info("SessionManager shutdown complete")


# Global session manager instance
session_manager = SessionManager()
