"""Main Agent API for executing prompts with event tracking."""

import traceback as tb
from typing import AsyncGenerator, List, Optional
from datetime import datetime

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
)

from .config import SessionConfig
from .events import (
    AgentEvent,
    EventType,
    StartEvent,
    ErrorEvent,
)
from collab_sims.trackers.base import BaseTracker
from ._session_base import _SessionBase


class CollabSims(_SessionBase):
    """Main API for executing agent prompts with event streaming and tracking."""

    def __init__(
        self,
        options: Optional[ClaudeAgentOptions] = None,
        trackers: Optional[List[BaseTracker]] = None,
        config: Optional[SessionConfig] = None,
        approval_manager=None
    ):
        """Initialize CollabSims.

        Args:
            options: Claude Agent options (default: bypassPermissions for auto-approval)
            trackers: List of event trackers (default: empty)
            config: Session configuration including partial message streaming
            approval_manager: Optional ApprovalManager for tool approval workflow
        """
        super().__init__(trackers=trackers)
        self.config = config or SessionConfig()
        self.approval_manager = approval_manager

        # Default to bypassPermissions for auto-approval unless options provided
        self.options = options or ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            include_partial_messages=self.config.include_partial_messages
        )
        self._start_time: Optional[datetime] = None

    def add_tracker(self, tracker: BaseTracker) -> None:
        """Add a tracker at runtime.

        Args:
            tracker: Tracker instance to add
        """
        self.trackers.append(tracker)

    async def create_session(
        self,
        config: Optional[SessionConfig] = None
    ):
        """Create and start a new session for multi-turn conversations.

        Args:
            config: Optional session configuration (user_id, tags, metadata)

        Returns:
            Connected CollabSimsSession ready for queries

        Example:
            >>> agent = CollabSims(trackers=[ConsoleTracker()])
            >>> session = await agent.create_session(
            ...     SessionConfig(user_id="user123", tags=["production"])
            ... )
            >>>
            >>> # Multiple queries in same session
            >>> async for event in session.query("First query"):
            ...     print(event)
            >>>
            >>> async for event in session.query("Follow-up query"):
            ...     print(event)  # Claude remembers first query!
            >>>
            >>> await session.close()
        """
        from .session import CollabSimsSession

        session = CollabSimsSession(
            options=self.options,
            config=config or SessionConfig(),
            trackers=self.trackers,
            approval_manager=self.approval_manager
        )
        await session._connect()
        return session

    async def execute(self, prompt: str) -> AsyncGenerator[AgentEvent, None]:
        """Execute a prompt and stream events.

        Args:
            prompt: The instruction/prompt for the agent

        Yields:
            AgentEvent objects (PlanEvent, MessageEvent, etc.)

        Example:
            >>> api = CollabSims(trackers=[ConsoleTracker()])
            >>> async for event in api.execute("Create a web scraper"):
            ...     if event.type == EventType.PLAN:
            ...         print(f"Tasks: {len(event.todos)}")
        """
        self._start_time = datetime.now()

        try:
            # Setup trackers
            for tracker in self.trackers:
                await tracker.setup()

            # Emit start event
            start_event = StartEvent(
                prompt=prompt,
                options={"permission_mode": self.options.permission_mode}
            )
            await self._emit_event(start_event)
            yield start_event

            # Execute agent
            async with ClaudeSDKClient(options=self.options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    # Parse message into events
                    events = self._parse_message(message)

                    # Emit and yield each event
                    for event in events:
                        await self._emit_event(event)
                        yield event

        except Exception as e:
            # Emit error event
            error_event = ErrorEvent(
                error=str(e),
                error_type=type(e).__name__,
                context={"prompt": prompt},
                traceback=tb.format_exc(),
                session_id=self._session_id
            )
            await self._emit_event(error_event)
            yield error_event
            raise

        finally:
            # Teardown trackers
            for tracker in self.trackers:
                await tracker.teardown()
