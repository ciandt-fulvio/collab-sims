"""Service for managing multi-turn sessions"""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime

# Import only from collab_sims (no CollabSims dependencies)
from ...persistence import SQLiteRepository
from ...trackers import StreamTracker, DatabaseTracker
from ...core.events import EventType
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
    error: Optional[str] = None


class SessionManager:
    """
    Manages lifecycle of sessions without CollabSims SDK.

    Responsibilities:
    - Create/destroy sessions
    - Track session metadata
    - Execute queries within session context (simulated)
    - Provide event streaming per query
    """

    def __init__(self, approval_manager: Optional[ApprovalManager] = None):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._active_queries: Dict[str, QueryTask] = {}
        self._event_subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.approval_manager = approval_manager or ApprovalManager()
        self._cleanup_task: Optional[asyncio.Task] = None

        # Initialize database tracker for persistence
        self.db_tracker = self._init_database_tracker()

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

        This allows sessions to persist across server restarts.
        Only restores sessions marked as 'active' in the database.
        """
        try:
            # Get all active sessions from database
            active_sessions = await self.db_tracker.repository.list_sessions(
                status="active",
                limit=1000
            )

            restored_count = 0
            for session_data in active_sessions:
                session_id = session_data["session_id"]

                # Create a stream tracker for this session
                stream_tracker = StreamTracker()

                # Store in memory (matching the structure from create_session)
                self._sessions[session_id] = {
                    "session_id": session_id,
                    "tracker": stream_tracker,
                    "config": session_data.get("metadata", {}),
                    "created_at": session_data["created_at"],
                    "status": session_data.get("status", "active"),
                    "execution_state": "idle",  # Always start idle on restore
                    "current_query_id": None,
                    "query_count": session_data.get("query_count", 0),
                    "session_type": session_data.get("metadata", {}).get("session_type", "worker"),
                }

                restored_count += 1

            if restored_count > 0:
                logger.info(f"✅ Restored {restored_count} active session(s) from database")

        except Exception as e:
            logger.error(f"Failed to restore sessions from database: {e}")

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
        config: Optional[Dict[str, Any]] = None,
        session_type: str = "worker"
    ) -> Dict[str, Any]:
        """
        Create a new multi-turn session.

        Args:
            config: Optional session configuration
            session_type: Type of session (worker/scout)

        Returns:
            Session metadata
        """
        # Ensure cleanup task is running
        self._ensure_cleanup_task_started()

        session_id = f"session-{uuid.uuid4()}"
        created_at = datetime.now()

        # Create trackers for this session
        stream_tracker = StreamTracker()

        # Create session in database
        await self.db_tracker.repository.create_session(
            session_id=session_id,
            user_id=config.get("user_id") if config else None,
            created_at=created_at,
            metadata={
                **(config or {}),
                "session_type": session_type
            }
        )

        # Store session data in memory
        self._sessions[session_id] = {
            "session_id": session_id,
            "tracker": stream_tracker,
            "config": config or {},
            "created_at": created_at.isoformat(),
            "status": "active",
            "execution_state": "idle",  # Runtime execution state: "idle" | "executing"
            "current_query_id": None,  # ID of currently executing query (if any)
            "query_count": 0,
            "session_type": session_type,
        }

        logger.info(f"Created session {session_id} (type: {session_type})")

        return self._get_session_metadata(session_id)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        # Check in-memory first (active sessions)
        if session_id in self._sessions:
            return self._get_session_metadata(session_id)

        # Fall back to database (sessions from previous runs)
        try:
            return await self.db_tracker.repository.get_session(session_id)
        except Exception as e:
            logger.error(f"Failed to get session {session_id} from database: {e}")
            return None

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions from database"""
        try:
            # Fetch all sessions from database
            db_sessions = await self.db_tracker.repository.list_sessions()
            sessions = []
            for db_session in db_sessions:
                # Merge with in-memory data if available
                session_id = db_session.get("session_id")
                if session_id in self._sessions:
                    sessions.append(self._get_session_metadata(session_id))
                else:
                    # Use database data (for sessions from previous runs)
                    sessions.append(db_session)
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions from database: {e}")
            # Fallback to in-memory sessions only
            return [self._get_session_metadata(sid) for sid in self._sessions.keys()]

    async def query_session(
        self, session_id: str, prompt: str
    ) -> tuple[List[Dict[str, Any]], str, Optional[str]]:
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
        tracker: StreamTracker = session_data["tracker"]

        # Clear previous query events
        tracker.clear_events()

        try:
            # Simulate agent response (similar to api_simple.py)
            events = await self._simulate_agent_response(prompt, session_id)

            # Update query count
            session_data["query_count"] += 1

            return events, "completed", None

        except Exception as e:
            return tracker.get_events(), "error", str(e)

    async def _broadcast_event(self, session_id: str, event: Dict[str, Any]):
        """Broadcast event to all SSE subscribers for this session"""
        if session_id in self._event_subscribers:
            # Send to all connected clients
            dead_queues = []
            for queue in self._event_subscribers[session_id]:
                try:
                    queue.put_nowait(event)
                except:
                    dead_queues.append(queue)

            # Cleanup dead queues
            for queue in dead_queues:
                self._event_subscribers[session_id].remove(queue)

    async def subscribe_to_session_events(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
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

    def _get_active_query_for_session(self, session_id: str) -> Optional[QueryTask]:
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

    async def _simulate_agent_response(self, prompt: str, session_id: str) -> List[Dict[str, Any]]:
        """Simulate an agent response (no CollabSims SDK required)"""
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
        """Background task that generates simulated events and broadcasts them

        This task continues running even if SSE disconnects.
        Events are captured by DatabaseTracker and broadcast to live subscribers.
        """
        try:
            # Generate simulated events
            events = await self._simulate_agent_response_streaming(prompt, session_id)

            # Broadcast each event
            for event in events:
                await self._broadcast_event(session_id, event)
                await asyncio.sleep(0.05)  # Small delay between events

            # Mark as completed
            if query_id in self._active_queries:
                self._active_queries[query_id].status = "completed"

            # Update session query count
            if session_id in self._sessions:
                self._sessions[session_id]["query_count"] += 1

        except Exception as e:
            # Mark as error
            if query_id in self._active_queries:
                self._active_queries[query_id].status = "error"
                self._active_queries[query_id].error = str(e)

            # Broadcast error event
            error_event = {
                'type': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            await self._broadcast_event(session_id, error_event)

        finally:
            # Transition: executing -> idle
            if session_id in self._sessions:
                logger.info(f"🔄 Session {session_id[:12]} transitioning: executing -> idle")
                self._sessions[session_id]["execution_state"] = "idle"
                self._sessions[session_id]["current_query_id"] = None

    async def _simulate_agent_response_streaming(self, prompt: str, session_id: str) -> List[Dict[str, Any]]:
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
                query_id = await self.start_query_background(session_id, prompt)

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

    def _get_session_metadata(self, session_id: str) -> Dict[str, Any]:
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
        """Shutdown session manager and cancel background tasks"""
        logger.info("SessionManager shutdown initiated...")

        # Close all active sessions first
        session_ids = list(self._sessions.keys())
        if session_ids:
            logger.debug(f"Closing {len(session_ids)} active sessions")
            for session_id in session_ids:
                try:
                    await self.close_session(session_id)
                except Exception as e:
                    logger.warning(f"Error closing session {session_id}: {e}")

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
