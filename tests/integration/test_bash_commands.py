"""Integration tests for bash command execution via Claude Agent SDK.

Tests that verify the agent can execute real bash commands and
return correct results.

These tests require:
- Internet connection

References:
- https://github.com/anthropics/claude-agent-sdk
"""


import pytest

from collab_sims.core.agent import CollabSims
from collab_sims.core.config import SessionConfig
from collab_sims.core.events import EventType


class TestBashCommandExecution:
    """Test real bash command execution through agent."""

    @pytest.mark.asyncio
    async def test_pwd_shows_current_directory(self, temp_work_dir):
        """Test that pwd command returns the working directory.

        This is a simple test that verifies:
        1. Claude Agent SDK can execute bash commands
        2. The working directory is set correctly
        3. Tool results are captured
        """
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query(
            "Execute the bash command 'pwd' to show the current working directory"
        ):
            events.append(event)

        # Verify we got a complete response
        assert any(e.type == EventType.COMPLETE for e in events)

        # Get all tool results
        tool_results = [e for e in events if e.type == EventType.TOOL_RESULT]

        # Collect output from tool results
        outputs = []
        for result in tool_results:
            if hasattr(result, 'output'):
                outputs.append(str(result.output))

        # Verify the working directory appears somewhere in the output
        all_output = "\n".join(outputs)
        assert str(temp_work_dir) in all_output or temp_work_dir.name in all_output

        await session.close()

    @pytest.mark.asyncio
    async def test_ls_lists_files(self, temp_work_dir):
        """Test that ls command lists files in directory.

        Creates specific files and verifies agent can list them.
        """
        # Create test files with known names
        test_files = ["alpha.txt", "beta.txt", "gamma.txt"]
        for filename in test_files:
            (temp_work_dir / filename).write_text(f"content of {filename}")

        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query(
            "Use bash to list all files in the current directory with 'ls'"
        ):
            events.append(event)

        # Get all content from messages and tool results
        all_content = []
        for event in events:
            if hasattr(event, 'content') and event.content:
                all_content.append(event.content)
            if hasattr(event, 'output') and event.output:
                all_content.append(str(event.output))

        combined_content = " ".join(all_content)

        # Verify at least some of our test files appear
        found_files = sum(1 for f in test_files if f in combined_content)
        assert found_files >= 2, f"Should find at least 2 test files, found {found_files}"

        await session.close()

    @pytest.mark.asyncio
    async def test_echo_command(self, temp_work_dir):
        """Test that echo command works correctly.

        This tests a simple command with predictable output.
        """
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        test_message = "HelloFromCollabSims123"

        events = []
        async for event in session.query(
            f"Use bash to run 'echo {test_message}'"
        ):
            events.append(event)

        # Get tool results
        tool_results = [e for e in events if e.type == EventType.TOOL_RESULT]

        # Collect outputs
        outputs = []
        for result in tool_results:
            if hasattr(result, 'output'):
                outputs.append(str(result.output))

        # The test message should appear in output
        all_output = " ".join(outputs)
        assert test_message in all_output

        await session.close()

    @pytest.mark.asyncio
    async def test_create_file_with_bash(self, temp_work_dir):
        """Test creating a file using bash commands.

        Verifies that bash commands can modify the filesystem.
        """
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        filename = "test_created_file.txt"
        file_content = "Created by bash command"

        events = []
        async for event in session.query(
            f"Use bash to create a file named '{filename}' with content '{file_content}' "
            f"using echo and redirection"
        ):
            events.append(event)

        # Verify the file was created
        created_file = temp_work_dir / filename
        assert created_file.exists(), f"File {filename} should have been created"

        # Verify content
        actual_content = created_file.read_text()
        assert file_content in actual_content

        await session.close()

    @pytest.mark.asyncio
    async def test_multiple_bash_commands_in_sequence(self, temp_work_dir):
        """Test executing multiple bash commands in one query.

        Verifies that agent can handle complex multi-step bash operations.
        """
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query(
            "Use bash to: 1) create a directory named 'testdir', "
            "2) create a file 'testdir/hello.txt' with content 'world', "
            "3) list the contents of testdir"
        ):
            events.append(event)

        # Verify directory was created
        test_dir = temp_work_dir / "testdir"
        assert test_dir.exists(), "Directory should have been created"

        # Verify file was created
        test_file = test_dir / "hello.txt"
        assert test_file.exists(), "File should have been created"

        # Verify content
        content = test_file.read_text()
        assert "world" in content

        await session.close()


class TestBashCommandToolEvents:
    """Test that bash commands generate proper tool events."""

    @pytest.mark.asyncio
    async def test_bash_generates_tool_use_event(self, temp_work_dir):
        """Test that bash command generates ToolUseEvent."""
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query("Use bash to run 'pwd'"):
            events.append(event)

        # Find tool_use events
        tool_uses = [e for e in events if e.type == EventType.TOOL_USE]

        # Should have at least one tool use
        assert len(tool_uses) > 0, "Should generate at least one tool_use event"

        # At least one should be Bash
        bash_uses = [e for e in tool_uses if hasattr(e, 'tool_name') and e.tool_name == "Bash"]
        assert len(bash_uses) > 0, "Should have at least one Bash tool use"

        # Bash tool should have input with command
        bash_event = bash_uses[0]
        assert hasattr(bash_event, 'input'), "Tool use should have input"
        assert 'command' in bash_event.input, "Bash tool should have command in input"

        await session.close()

    @pytest.mark.asyncio
    async def test_bash_generates_tool_result_event(self, temp_work_dir):
        """Test that bash command generates ToolResultEvent."""
        agent = CollabSims()
        session = await agent.create_session(
            SessionConfig(project_name="test-project", working_dir=str(temp_work_dir))
        )

        events = []
        async for event in session.query("Use bash to run 'echo test'"):
            events.append(event)

        # Find tool_result events
        tool_results = [e for e in events if e.type == EventType.TOOL_RESULT]

        # Should have at least one tool result
        assert len(tool_results) > 0, "Should generate at least one tool_result event"

        # Tool result should have output
        result_event = tool_results[0]
        assert hasattr(result_event, 'output'), "Tool result should have output"
        assert result_event.output is not None, "Tool result output should not be None"

        await session.close()


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
