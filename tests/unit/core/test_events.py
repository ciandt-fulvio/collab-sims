"""Unit tests for event dataclasses.

Tests event creation, serialization, and validation.

References:
- https://docs.python.org/3/library/dataclasses.html
"""

import json

import pytest

# Import directly from events module file to avoid circular imports via __init__.py
from collab_sims.core.events import (
    AgentEvent,
    CompleteEvent,
    ErrorEvent,
    EventType,
    MessageEvent,
    PlanEvent,
    QueryEvent,
    SessionEndEvent,
    SessionStartEvent,
    StartEvent,
    TaskInfo,
    ToolUseEvent,
)


class TestEventTypeEnum:
    """Test EventType enumeration."""

    def test_event_type_values(self):
        """Test that event types have expected values."""
        assert EventType.MESSAGE == "message"
        assert EventType.TOOL_USE == "tool_use"
        assert EventType.COMPLETE == "complete"
        assert EventType.ERROR == "error"

    def test_event_type_membership(self):
        """Test checking membership in EventType."""
        assert "message" in [e.value for e in EventType]
        assert "invalid_type" not in [e.value for e in EventType]


class TestAgentEvent:
    """Test base AgentEvent class."""

    def test_create_basic_event(self):
        """Test creating a basic event."""
        event = AgentEvent(type=EventType.MESSAGE)

        assert event.type == EventType.MESSAGE
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_event_has_unique_id(self):
        """Test that each event gets a unique ID."""
        event1 = AgentEvent(type=EventType.MESSAGE)
        event2 = AgentEvent(type=EventType.MESSAGE)

        assert event1.event_id != event2.event_id

    def test_event_with_session_id(self):
        """Test creating event with session_id."""
        event = AgentEvent(type=EventType.MESSAGE, session_id="test-session-123")

        assert event.session_id == "test-session-123"

    def test_event_with_metadata(self):
        """Test creating event with metadata."""
        metadata = {"key": "value", "number": 42}
        event = AgentEvent(type=EventType.MESSAGE, metadata=metadata)

        assert event.metadata == metadata

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = AgentEvent(type=EventType.MESSAGE, session_id="test-session")

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert event_dict["type"] == EventType.MESSAGE
        assert event_dict["session_id"] == "test-session"

    def test_event_to_json(self):
        """Test converting event to JSON string."""
        event = AgentEvent(type=EventType.MESSAGE, session_id="test-session")

        event_json = event.to_json()

        # Parse back to verify it's valid JSON
        parsed = json.loads(event_json)
        assert parsed["session_id"] == "test-session"


class TestSessionEvents:
    """Test session lifecycle events."""

    def test_session_start_event(self):
        """Test SessionStartEvent creation."""
        event = SessionStartEvent(
            session_id="session-123",
            user_id="user-456",
            tags=["dev", "test"],
            metadata={"role": "worker"},
        )

        assert event.type == EventType.SESSION_START
        assert event.session_id == "session-123"
        assert event.user_id == "user-456"
        assert event.tags == ["dev", "test"]
        assert event.metadata == {"role": "worker"}

    def test_session_end_event(self):
        """Test SessionEndEvent creation."""
        event = SessionEndEvent(session_id="session-123", total_queries=5, total_duration_ms=30000)

        assert event.type == EventType.SESSION_END
        assert event.total_queries == 5
        assert event.total_duration_ms == 30000

    def test_query_event(self):
        """Test QueryEvent creation."""
        event = QueryEvent(prompt="Create a file", query_number=1, session_id="session-123")

        assert event.type == EventType.QUERY
        assert event.prompt == "Create a file"
        assert event.query_number == 1


class TestExecutionEvents:
    """Test execution lifecycle events."""

    def test_start_event(self):
        """Test StartEvent creation."""
        event = StartEvent(prompt="Test prompt", options={"mode": "auto"})

        assert event.type == EventType.START
        assert event.prompt == "Test prompt"
        assert event.options == {"mode": "auto"}

    def test_complete_event(self):
        """Test CompleteEvent creation."""
        event = CompleteEvent(
            duration_ms=1500,
            total_cost_usd=0.002,
            num_turns=3,
            usage={"input_tokens": 100, "output_tokens": 50},
        )

        assert event.type == EventType.COMPLETE
        assert event.duration_ms == 1500
        assert event.total_cost_usd == 0.002
        assert event.num_turns == 3
        assert event.usage["input_tokens"] == 100


class TestMessageEvents:
    """Test message events."""

    def test_message_event(self):
        """Test MessageEvent creation."""
        event = MessageEvent(
            role="assistant", content="Hello, how can I help?", model="claude-3-5-sonnet-20250122"
        )

        assert event.type == EventType.MESSAGE
        assert event.role == "assistant"
        assert event.content == "Hello, how can I help?"
        assert event.model == "claude-3-5-sonnet-20250122"

    def test_message_event_with_thinking(self):
        """Test MessageEvent with thinking content."""
        event = MessageEvent(
            role="assistant",
            content="I'll create that file.",
            thinking="First, I need to determine the file path...",
        )

        assert event.thinking == "First, I need to determine the file path..."


class TestToolEvents:
    """Test tool-related events."""

    def test_tool_use_event(self):
        """Test ToolUseEvent creation."""
        event = ToolUseEvent(
            tool_name="Write",
            tool_use_id="tool_123",
            input={"file_path": "/test.txt", "content": "test"},
        )

        assert event.type == EventType.TOOL_USE
        assert event.tool_name == "Write"
        assert event.tool_use_id == "tool_123"
        assert event.input["file_path"] == "/test.txt"


class TestPlanEvents:
    """Test plan events."""

    def test_plan_event_basic(self):
        """Test PlanEvent creation."""
        tasks = [
            TaskInfo(content="Task 1", status="completed", active_form="Task 1 active"),
            TaskInfo(content="Task 2", status="in_progress", active_form="Task 2 active"),
        ]

        event = PlanEvent(todos=tasks, total_tasks=2, completed=1, in_progress=1, pending=0)

        assert event.type == EventType.PLAN
        assert len(event.todos) == 2
        assert event.total_tasks == 2
        assert event.completed == 1

    def test_task_info(self):
        """Test TaskInfo creation."""
        task = TaskInfo(content="Create file", status="in_progress", active_form="Creating file")

        assert task.content == "Create file"
        assert task.status == "in_progress"
        assert task.active_form == "Creating file"


class TestErrorEvents:
    """Test error events."""

    def test_error_event(self):
        """Test ErrorEvent creation."""
        event = ErrorEvent(
            error="File not found",
            error_type="FileNotFoundError",
            context={"file_path": "/missing.txt"},
        )

        assert event.type == EventType.ERROR
        assert event.error == "File not found"
        assert event.error_type == "FileNotFoundError"
        assert event.context["file_path"] == "/missing.txt"

    def test_error_event_with_traceback(self):
        """Test ErrorEvent with traceback."""
        event = ErrorEvent(
            error="Division by zero",
            error_type="ZeroDivisionError",
            traceback="Traceback (most recent call last):\n  ...",
        )

        assert "Traceback" in event.traceback


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
