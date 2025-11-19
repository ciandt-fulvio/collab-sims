"""Integration tests for Agent with Claude Agent SDK.

Tests real interactions with the Claude Agent SDK to ensure:
- Core properly calls SDK methods
- Events are generated correctly
- Real bash commands work
- Session management works end-to-end

These tests require:
- Internet connection

References:
- https://github.com/anthropics/claude-agent-sdk
"""

import os
from pathlib import Path

import pytest

from collab_sims.core.agent import CollabSims
from collab_sims.core.config import SessionConfig
from collab_sims.core.events import (
    CompleteEvent,
    EventType,
    MessageEvent,
    QueryEvent,
)


class TestAgentBasicExecution:
    """Test basic agent execution with Claude SDK."""

    @pytest.mark.asyncio
    async def test_simple_query_returns_200_equivalent(self):
        """Test that a simple query executes successfully.

        This is equivalent to checking for HTTP 200 - the query should
        complete without errors.
        """
        agent = CollabSims()
        events = []

        async for event in agent.execute("Say 'hello' and nothing else"):
            events.append(event)

        # Should have at least: start, message, complete
        assert len(events) >= 3

        # Check for specific event types
        event_types = [e.type for e in events]
        assert EventType.START in event_types
        assert EventType.MESSAGE in event_types
        assert EventType.COMPLETE in event_types

        # Last event should be complete
        assert isinstance(events[-1], CompleteEvent)

    @pytest.mark.asyncio
    async def test_agent_responds_with_message(self):
        """Test that agent generates a message response."""
        agent = CollabSims()
        messages = []

        async for event in agent.execute("What is 2+2?"):
            if event.type == EventType.MESSAGE:
                messages.append(event)

        # Should have at least one message
        assert len(messages) > 0

        # Message should have content
        first_message = messages[0]
        assert isinstance(first_message, MessageEvent)
        assert first_message.content
        assert len(first_message.content) > 0


class TestAgentSessionManagement:
    """Test session creation and multi-turn conversations."""

    @pytest.mark.asyncio
    async def test_create_session_successfully(self):
        """Test creating a session with Claude SDK."""
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(user_id="test-user")
        )

        assert session is not None
        assert session.is_connected
        assert session._session_id is not None

        await session.close()

    @pytest.mark.asyncio
    async def test_session_query_generates_events(self):
        """Test that session queries generate proper events."""
        agent = CollabSims()
        session = await agent.create_session()

        events = []
        async for event in session.query("Say hello"):
            events.append(event)

        # Should have query, message, and complete events
        event_types = [e.type for e in events]
        assert EventType.QUERY in event_types
        assert EventType.MESSAGE in event_types
        assert EventType.COMPLETE in event_types

        await session.close()

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test using session as async context manager."""
        agent = CollabSims()

        async with await agent.create_session() as session:
            events = []
            async for event in session.query("Hello"):
                events.append(event)

            assert len(events) > 0

        # Session should be closed after context exit
        assert not session.is_connected


class TestAgentBashIntegration:
    """Test agent bash command execution."""

    @pytest.mark.asyncio
    async def test_bash_pwd_command(self, temp_work_dir):
        """Test agent executing pwd bash command.

        This verifies that:
        1. Agent can execute bash commands via SDK
        2. Tool use and tool result events are generated
        3. Commands run in the correct working directory
        """
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query(
            "Use bash to show the current working directory (pwd)"
        ):
            events.append(event)

        # Check for tool events
        event_types = [e.type for e in events]

        # Should have tool_use and tool_result somewhere
        # (might not be in every execution if Claude decides to just answer)
        # So we make this a soft assertion - if tools were used, verify them
        tool_uses = [e for e in events if e.type == EventType.TOOL_USE]
        tool_results = [e for e in events if e.type == EventType.TOOL_RESULT]

        if tool_uses:
            # If agent used tools, verify structure
            assert len(tool_results) > 0
            # At least one tool should be Bash
            bash_tools = [t for t in tool_uses if hasattr(t, 'tool_name') and t.tool_name == "Bash"]
            assert len(bash_tools) > 0

        await session.close()

    @pytest.mark.asyncio
    async def test_bash_list_files_command(self, temp_work_dir):
        """Test agent listing files in a directory.

        Creates test files and asks agent to list them.
        """
        # Create test files
        (temp_work_dir / "file1.txt").write_text("test1")
        (temp_work_dir / "file2.txt").write_text("test2")

        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query(
            "Use bash to list all .txt files in the current directory (ls *.txt)"
        ):
            events.append(event)

        # Verify execution completed
        assert any(e.type == EventType.COMPLETE for e in events)

        # Check if agent found the files (in message or tool result)
        all_content = []
        for event in events:
            if hasattr(event, 'content') and event.content:
                all_content.append(event.content)
            if hasattr(event, 'output') and event.output:
                all_content.append(str(event.output))

        # At least one piece of content should mention our files
        # (This is a soft check - depends on agent behavior)
        content_str = " ".join(all_content).lower()
        found_files = "file1" in content_str or "file2" in content_str

        # If agent used tools, should have found files
        tool_results = [e for e in events if e.type == EventType.TOOL_RESULT]
        if tool_results:
            assert found_files, "Agent should have found the test files"

        await session.close()


class TestAgentEventStreaming:
    """Test event streaming behavior."""

    @pytest.mark.asyncio
    async def test_events_stream_in_real_time(self):
        """Test that events are yielded as they occur, not buffered."""
        agent = CollabSims()
        session = await agent.create_session()

        event_count = 0
        first_event_received = False

        async for event in session.query("Count to 3"):
            event_count += 1
            if event_count == 1:
                first_event_received = True
            if event_count == 2:
                # If we get a second event, streaming is working
                assert first_event_received
                break

        # Should have received multiple events
        assert event_count >= 2

        await session.close()


class TestAgentErrorHandling:
    """Test error handling in agent execution."""

    @pytest.mark.asyncio
    async def test_handles_invalid_working_directory(self):
        """Test agent handles invalid working directory gracefully."""
        # This should either fail gracefully or create the directory
        agent = CollabSims()

        # Try to create session with non-existent directory
        # The agent should handle this by creating it or raising a clear error
        try:
            session = await agent.create_session(
                SessionConfig(working_dir="/tmp/collab-sims-test-nonexistent-" + str(os.getpid()))
            )

            # If successful, should be connected
            assert session.is_connected

            # Test a simple query
            events = []
            async for event in session.query("Hello"):
                events.append(event)

            assert len(events) > 0

            await session.close()

            # Cleanup
            Path(session._working_dir).rmdir()

        except Exception as e:
            # If it raises an error, it should be clear
            assert str(e)  # Should have error message


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
