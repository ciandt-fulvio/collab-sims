"""Session-based API for multi-turn conversations."""

import asyncio
import logging
import os
import traceback as tb
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
)

from ._session_base import _SessionBase
from .config import SessionConfig, get_collab_sims_config_dir, get_default_working_dir
from .events import (
    AgentEvent,
    ErrorEvent,
    QueryEvent,
    SessionEndEvent,
    SessionStartEvent,
)
from .prompts import get_session_prompt

logger = logging.getLogger(__name__)


class CollabSimsSession(_SessionBase):
    """Session for multi-turn agent conversations.

    Maintains a persistent connection to Claude SDK, allowing multiple
    queries in the same conversation context. Claude remembers all previous
    queries and responses within the session.

    Example:
        >>> agent = CollabSims()
        >>> session = await agent.create_session(SessionConfig(user_id="user123"))
        >>>
        >>> # First query
        >>> async for event in session.query("Create a web scraper"):
        ...     print(event)
        >>>
        >>> # Follow-up query - Claude remembers the web scraper!
        >>> async for event in session.query("Add error handling to it"):
        ...     print(event)
        >>>
        >>> await session.close()

    Or use as context manager:
        >>> async with await agent.create_session() as session:
        ...     async for event in session.query("First query"):
        ...         print(event)
        ...     async for event in session.query("Follow-up"):
        ...         print(event)
    """

    def __init__(
        self,
        options: ClaudeAgentOptions,
        config: SessionConfig,
        trackers: list = None,
        approval_manager=None,
        session_id: str | None = None,
        resume: bool = False,
    ):
        """Initialize session (internal - use CollabSims.create_session() instead).

        Args:
            options: Claude Agent options
            config: Session configuration
            trackers: List of event trackers (inherited from CollabSims)
            approval_manager: Optional ApprovalManager for tool approval workflow
            session_id: Optional session ID (if not provided, generates a new UUID)
            resume: If True, resume an existing session with the given session_id
        """
        super().__init__(trackers=trackers or [])
        self.config = config
        self.approval_manager = approval_manager
        self._resume = resume  # Store resume flag for use in _connect()

        # Session state
        self.client: ClaudeSDKClient | None = None
        self.is_connected = False
        self._session_id = session_id or str(uuid.uuid4())
        self._user_id = config.user_id
        self._query_count = 0
        self._start_time: datetime | None = None

        # Queue for events that need to be yielded (e.g., approval_request)
        self._event_queue: asyncio.Queue | None = None

        # Set Collab Sims config directory for Claude SDK session storage
        # This isolates Collab Sims sessions from personal Claude Code sessions in ~/.claude/
        collab_sims_config_dir = get_collab_sims_config_dir()
        os.environ["CLAUDE_CONFIG_DIR"] = collab_sims_config_dir
        logger.info(f"Using Collab Sims config directory: {collab_sims_config_dir}")

        # Set up working directory for local execution
        if config.working_dir is None:
            working_dir_str = get_default_working_dir()
            self._working_dir = Path(working_dir_str)
        else:
            self._working_dir = Path(config.working_dir)
            if not self._working_dir.is_absolute():
                self._working_dir = Path.cwd() / self._working_dir

        # Create working directory if it doesn't exist
        self._working_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using working directory: {self._working_dir}")

        # Store approval config if manager provided
        if approval_manager:
            approval_config = config.approval_config or {
                "mode": "interactive",
                "tool_policies": {},
                "auto_approved_tools": []
            }
            approval_manager.set_config(self._session_id, approval_config)

        # Configure SDK options for local execution
        self.options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",  # Auto-approve all tools by default
            include_partial_messages=config.include_partial_messages,
            cwd=str(self._working_dir),  # Use working directory directly
            extra_args={"session-id": self._session_id}
        )

    async def _connect(self):
        """Connect to Claude SDK and emit session start event.

        This is called internally by CollabSims.create_session().
        """
        self._start_time = datetime.now()

        # Setup trackers
        for tracker in self.trackers:
            await tracker.setup()

        # Get system prompt (skip for resumed sessions - they already have context)
        system_prompt = None if self._resume else get_session_prompt(self._session_id)

        # Build ClaudeAgentOptions for local execution (no MCP servers)
        final_options_kwargs = {
            "permission_mode": "bypassPermissions",
            "include_partial_messages": self.config.include_partial_messages,
            "cwd": str(self._working_dir),
            "setting_sources": ['user'],  # Enable user settings (includes file tools)
        }

        # Add resume parameter if resuming session
        if self._resume:
            # When resuming, use resume parameter (cannot use session-id with resume)
            final_options_kwargs["resume"] = self._session_id
            logger.info(f"Resuming session {self._session_id}")
        else:
            # Only set system_prompt and session-id for new sessions
            final_options_kwargs["system_prompt"] = system_prompt
            final_options_kwargs["extra_args"] = {"session-id": self._session_id}

        final_options = ClaudeAgentOptions(**final_options_kwargs)

        # Create and connect SDK client
        self.client = ClaudeSDKClient(options=final_options)
        await self.client.connect()
        self.is_connected = True

        # Get the system prompt that was actually sent to Claude Agent SDK
        actual_system_prompt = final_options.system_prompt if final_options else None

        # Emit session start event
        start_event = SessionStartEvent(
            session_id=self._session_id,
            user_id=self._user_id,
            tags=self.config.tags,
            metadata=self.config.metadata,
            system_prompt=actual_system_prompt  # Include actual system prompt sent to SDK
        )
        await self._emit_event(start_event)

    async def _emit_and_queue_event(self, event: AgentEvent) -> None:
        """Emit event to trackers AND queue it for yielding in query stream.

        Used by approval callback to ensure approval events reach the frontend.

        Args:
            event: Event to emit and queue
        """
        # Emit to trackers
        await self._emit_event(event)

        # Queue for yielding if queue exists
        if self._event_queue is not None:
            await self._event_queue.put(event)

    async def query(self, prompt: str) -> AsyncGenerator[AgentEvent]:
        """Send a query and stream response events.

        The query is sent in the existing conversation context. Claude
        remembers all previous queries and responses in this session.

        Args:
            prompt: The query/instruction for the agent

        Yields:
            AgentEvent objects (QueryEvent, PlanEvent, MessageEvent, etc.)

        Raises:
            RuntimeError: If session is not connected

        Example:
            >>> async for event in session.query("Create a file"):
            ...     if event.type == EventType.PLAN:
            ...         print(f"Tasks: {event.total_tasks}")
        """
        if not self.is_connected:
            raise RuntimeError(
                "Session not connected. This should not happen - "
                "sessions should be created via CollabSims.create_session()"
            )

        self._query_count += 1

        # Create event queue for this query
        self._event_queue = asyncio.Queue()

        # Merged event queue for both SDK and queued events
        merged_queue = asyncio.Queue()
        sdk_done = asyncio.Event()

        # Initialize task variables (will be assigned in try block)
        sdk_task = None
        queue_task = None

        async def sdk_consumer():
            """Consumer task for SDK messages."""
            try:
                async for message in self.client.receive_response():
                    await merged_queue.put(('sdk', message))
            finally:
                sdk_done.set()

        async def queue_consumer():
            """Consumer task for queued events (e.g., approval_request)."""
            while not sdk_done.is_set():
                try:
                    # Check if queue still exists (race condition with cleanup)
                    if self._event_queue is None:
                        break
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                    await merged_queue.put(('queued', event))
                except TimeoutError:
                    continue
            # Drain remaining events after SDK is done
            if self._event_queue is not None:
                while not self._event_queue.empty():
                    try:
                        event = self._event_queue.get_nowait()
                        await merged_queue.put(('queued', event))
                    except asyncio.QueueEmpty:
                        break

        try:
            # Emit query event
            query_event = QueryEvent(
                prompt=prompt,
                query_number=self._query_count,
                session_id=self._session_id,
                user_id=self._user_id,
                metadata=self.config.metadata
            )
            await self._emit_event(query_event)
            yield query_event

            # Send query to Claude SDK
            await self.client.query(prompt)

            # Start consumer tasks
            sdk_task = asyncio.create_task(sdk_consumer())
            queue_task = asyncio.create_task(queue_consumer())

            # Yield events from merged queue
            while not sdk_done.is_set() or not merged_queue.empty():
                try:
                    source, data = await asyncio.wait_for(merged_queue.get(), timeout=0.1)

                    if source == 'queued':
                        # Already an event, just yield it
                        yield data
                    else:  # source == 'sdk'
                        # Parse SDK message into events
                        events = self._parse_message(data)
                        for event in events:
                            # Enrich events with session context
                            if event.user_id is None:
                                event.user_id = self._user_id
                            if not event.metadata:
                                event.metadata = self.config.metadata.copy()

                            await self._emit_event(event)
                            yield event
                except TimeoutError:
                    continue

            # Wait for tasks to complete
            await sdk_task
            await queue_task

        except Exception as e:
            # Log detailed error information
            logger.error(f"Error in session {self._session_id[:12]} query: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.debug(f"Full traceback:\n{tb.format_exc()}")

            # Emit error event
            error_event = ErrorEvent(
                error=str(e),
                error_type=type(e).__name__,
                context={
                    "prompt": prompt,
                    "query_number": self._query_count
                },
                traceback=tb.format_exc(),
                session_id=self._session_id,
                user_id=self._user_id
            )
            await self._emit_event(error_event)
            yield error_event
            raise
        finally:
            # Cancel background tasks if still running
            if sdk_task and not sdk_task.done():
                sdk_task.cancel()
            if queue_task and not queue_task.done():
                queue_task.cancel()

            # Wait for cancellation to complete (only if tasks were created)
            tasks_to_await = [t for t in [sdk_task, queue_task] if t is not None]
            if tasks_to_await:
                await asyncio.gather(*tasks_to_await, return_exceptions=True)

            # Clean up queue
            self._event_queue = None

    async def close(self):
        """Close the session and cleanup resources.

        Emits SessionEndEvent with session statistics.

        Example:
            >>> await session.close()
        """
        if not self.is_connected:
            return

        # Calculate session metrics
        duration_ms = int((datetime.now() - self._start_time).total_seconds() * 1000)

        # Emit session end event
        end_event = SessionEndEvent(
            session_id=self._session_id,
            user_id=self._user_id,
            total_queries=self._query_count,
            total_duration_ms=duration_ms,
            metadata=self.config.metadata
        )
        await self._emit_event(end_event)

        # Disconnect SDK client
        if self.client:
            await self.client.disconnect()

        # Teardown trackers
        for tracker in self.trackers:
            await tracker.teardown()

        self.is_connected = False

    async def interrupt(self):
        """Interrupt the currently executing query.

        This stops Claude mid-execution and halts event streaming. Works like
        pressing ESC in Claude Code shell. Only works in streaming mode.

        The session remains connected and can continue with new queries.

        Example:
            >>> # Start a long-running query in background
            >>> query_task = asyncio.create_task(
            ...     session.query("Generate 1000 lines of code")
            ... )
            >>>
            >>> # Let it run for a bit
            >>> await asyncio.sleep(2)
            >>>
            >>> # Interrupt it
            >>> await session.interrupt()
            >>>
            >>> # Session is still alive for new queries
            >>> async for event in session.query("Now do something else"):
            ...     print(event)

        Raises:
            RuntimeError: If session is not connected
        """
        if not self.is_connected:
            raise RuntimeError("Session not connected. Cannot interrupt.")

        if not self.client:
            raise RuntimeError("SDK client not available. Cannot interrupt.")

        logger.info(f"Interrupting session {self._session_id}")
        await self.client.interrupt()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
