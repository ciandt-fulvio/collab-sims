"""Base class for shared session logic."""

from typing import TYPE_CHECKING

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from claude_agent_sdk.types import StreamEvent

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    pass

from .events import (
    AgentEvent,
    CompleteEvent,
    EventType,
    MessageEvent,
    PartialMessageEvent,
    PlanChanges,
    PlanEvent,
    ProgressEvent,
    SystemEvent,
    TaskInfo,
    ToolResultEvent,
    ToolUseEvent,
)


class _SessionBase:
    """Base class providing shared session logic for message parsing and event handling.

    This class should not be instantiated directly. It provides common functionality
    for session classes that handle agent execution.
    """

    def __init__(self, trackers: list | None = None):  # Remove type hint to avoid import
        """Initialize session base.

        Args:
            trackers: List of event trackers
        """
        self.trackers = trackers or []
        self._session_id: str | None = None
        self._previous_plan: list[dict] | None = None
        self._tool_use_names: dict[str, str] = {}  # tool_use_id -> tool_name mapping
        self._last_message_id: str | None = None  # Track last MESSAGE event to link tools

    def _parse_message(self, message) -> list[AgentEvent]:
        """Parse SDK message into domain events.

        Args:
            message: Message from Claude SDK

        Returns:
            List of AgentEvent objects
        """
        events = []

        # Extract session ID if available
        if isinstance(message, SystemMessage) and message.subtype == "init":
            self._session_id = message.data.get("session_id")
            events.append(
                SystemEvent(subtype=message.subtype, data=message.data, session_id=self._session_id)
            )

        # Parse AssistantMessage
        elif isinstance(message, AssistantMessage):
            # Collect all text and thinking content to combine into single message
            text_parts = []
            thinking_content = None

            for block in message.content:
                # TodoWrite tool = Plan event
                if isinstance(block, ToolUseBlock) and block.name == "TodoWrite":
                    plan_event = self._create_plan_event(block)
                    events.append(plan_event)

                    # Also create progress event
                    progress_event = ProgressEvent(
                        completed=plan_event.completed,
                        total=plan_event.total_tasks,
                        percentage=(plan_event.completed / plan_event.total_tasks * 100)
                        if plan_event.total_tasks > 0
                        else 0,
                        current_task=self._get_current_task(plan_event.todos),
                        session_id=self._session_id,
                    )
                    events.append(progress_event)

                # Other tool uses
                elif isinstance(block, ToolUseBlock):
                    # Store mapping for later ToolResultBlock matching
                    self._tool_use_names[block.id] = block.name
                    events.append(
                        ToolUseEvent(
                            tool_name=block.name,
                            tool_use_id=block.id,
                            input=block.input,
                            session_id=self._session_id,
                            originated_from_message_id=self._last_message_id,
                        )
                    )

                # NOTE: ToolResultBlock never appears in AssistantMessage
                # It only appears in UserMessage - see UserMessage handler below

                # Text content - collect for combining
                elif isinstance(block, TextBlock):
                    text_parts.append(block.text)

                # Thinking content
                elif isinstance(block, ThinkingBlock):
                    thinking_content = block.thinking

            # Create single MessageEvent with combined text
            if text_parts or thinking_content:
                msg_event = MessageEvent(
                    role="assistant",
                    content="".join(text_parts),
                    thinking=thinking_content,
                    model=message.model,
                    session_id=self._session_id,
                )
                # Track this MESSAGE event ID for linking subsequent tool events
                self._last_message_id = msg_event.event_id
                events.append(msg_event)

        # Parse UserMessage (contains ToolResultBlocks)
        elif isinstance(message, UserMessage):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    # Get tool name from stored mapping
                    tool_name = self._tool_use_names.get(block.tool_use_id, "")

                    # Skip TodoWrite - it's handled separately via Plan events
                    # Also skip if tool_name is empty (means TOOL_USE was filtered)
                    if (
                        tool_name == "TodoWrite"
                        or tool_name.endswith("__TodoWrite")
                        or not tool_name
                    ):
                        continue

                    events.append(
                        ToolResultEvent(
                            tool_use_id=block.tool_use_id,
                            tool_name=tool_name,
                            output=block.content,
                            is_error=block.is_error if hasattr(block, "is_error") else False,
                            session_id=self._session_id,
                            originated_from_message_id=self._last_message_id,
                        )
                    )

        # Parse ResultMessage
        elif isinstance(message, ResultMessage):
            complete_event = CompleteEvent(
                duration_ms=message.duration_ms,
                total_cost_usd=message.total_cost_usd,
                num_turns=message.num_turns,
                result=message.result,
                usage=message.usage or {},
                session_id=message.session_id,
            )
            events.append(complete_event)

        # Parse StreamEvent for partial messages and usage updates
        elif isinstance(message, StreamEvent):
            event_data = message.event
            event_type = event_data.get("type")

            if event_type == "content_block_delta":
                delta = event_data.get("delta", {})
                if delta.get("type") == "text_delta":
                    partial_event = PartialMessageEvent(
                        delta=delta.get("text", ""),
                        index=event_data.get("index", 0),
                        content_type="text",
                        session_id=self._session_id,
                    )
                    events.append(partial_event)

            # Note: message_start and message_delta events are not exposed by Claude Agent SDK
            # The SDK abstracts these low-level API events and only provides:
            # - SystemMessage, AssistantMessage, StreamEvent (content_block_delta), ResultMessage
            # Token usage is available in ResultMessage at the end of the response

        return events

    def _create_plan_event(self, block: ToolUseBlock) -> PlanEvent:
        """Create a PlanEvent from TodoWrite tool use.

        Args:
            block: ToolUseBlock with TodoWrite

        Returns:
            PlanEvent with task info and changes
        """
        todos_data = block.input.get("todos", [])

        # Convert to TaskInfo objects
        tasks = [
            TaskInfo(content=t["content"], status=t["status"], active_form=t.get("activeForm", ""))
            for t in todos_data
        ]

        # Calculate metrics
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        pending = sum(1 for t in tasks if t.status == "pending")

        # Detect changes
        changes = None
        if self._previous_plan:
            changes = self._detect_plan_changes(self._previous_plan, todos_data)

        # Update previous plan
        self._previous_plan = todos_data

        return PlanEvent(
            todos=tasks,
            total_tasks=total,
            completed=completed,
            in_progress=in_progress,
            pending=pending,
            changes=changes,
            tool_use_id=block.id,
            session_id=self._session_id,
        )

    def _detect_plan_changes(self, old_todos: list[dict], new_todos: list[dict]) -> PlanChanges:
        """Detect changes between plan snapshots.

        Args:
            old_todos: Previous todos
            new_todos: Current todos

        Returns:
            PlanChanges object with added/removed/changed tasks
        """
        old_contents = {t["content"]: t for t in old_todos}
        new_contents = {t["content"]: t for t in new_todos}

        # Find added/removed
        added = list(set(new_contents.keys()) - set(old_contents.keys()))
        removed = list(set(old_contents.keys()) - set(new_contents.keys()))

        # Find status changes
        status_changed = []
        for content in old_contents:
            if content in new_contents:
                old_status = old_contents[content]["status"]
                new_status = new_contents[content]["status"]
                if old_status != new_status:
                    status_changed.append({"task": content, "from": old_status, "to": new_status})

        return PlanChanges(added=added, removed=removed, status_changed=status_changed)

    def _get_current_task(self, tasks: list[TaskInfo]) -> str | None:
        """Get the current in-progress task.

        Args:
            tasks: List of tasks

        Returns:
            Active form of in-progress task, or None
        """
        for task in tasks:
            if task.status == "in_progress":
                return task.active_form or task.content
        return None

    async def _emit_event(self, event: AgentEvent) -> None:
        """Emit event to all trackers.

        Calls specific hooks based on event type, then the generic on_event() handler.
        Respects should_handle() filter for each tracker.

        Args:
            event: Event to emit
        """
        for tracker in self.trackers:
            # Check if tracker wants to handle this event
            if not tracker.should_handle(event):
                continue

            try:
                # Call specific hooks based on event type
                if event.type == EventType.START:
                    await tracker.on_start(event)
                elif event.type == EventType.COMPLETE:
                    await tracker.on_complete(event)
                elif event.type == EventType.SESSION_START:
                    await tracker.on_session_start(event)
                elif event.type == EventType.SESSION_END:
                    await tracker.on_session_end(event)
                elif event.type == EventType.QUERY:
                    await tracker.on_query(event)
                elif event.type == EventType.ERROR:
                    await tracker.on_error(event)

                # Always call generic handler
                await tracker.on_event(event)
            except Exception as e:
                # Don't let tracker errors stop execution
                print(f"Warning: Tracker {type(tracker).__name__} failed: {e}")
