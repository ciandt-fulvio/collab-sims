"""Test for closed session retrieval bug.

Bug: When clicking on a closed session with query_count=0,
     the API returns "Session not found" even though it exists in the database.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

import httpx
import pytest


class TestClosedSessionRetrieval:
    """Test retrieving closed sessions from the database."""

    @pytest.fixture
    def free_port(self):
        """Find a free port for testing."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    @pytest.fixture
    async def running_server(self, free_port):
        """Start the API server for testing."""
        project_root = Path(__file__).parent.parent.parent

        # Set environment variables for test database
        import os

        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        env["COLLAB_SIMS_DB_PATH"] = "./data/api_sessions.db"

        # Start server
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "collab_sims.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(free_port),
                "--log-level",
                "warning",
            ],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        await asyncio.sleep(2)

        base_url = f"http://127.0.0.1:{free_port}"
        yield base_url, process

        # Cleanup
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    @pytest.mark.asyncio
    async def test_retrieve_closed_session_with_zero_queries(self, running_server):
        """Test that we can retrieve a closed session even with query_count=0.

        This tests the bug where closed sessions cannot be retrieved.
        """
        base_url, _process = running_server

        async with httpx.AsyncClient() as client:
            # Get an existing closed session from the database
            # The database already has test sessions from previous runs
            import sqlite3

            conn = sqlite3.connect("./data/api_sessions.db")
            cursor = conn.execute(
                "SELECT session_id FROM session WHERE status = 'closed' LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                # Skip test if no closed sessions exist
                pytest.skip("No closed sessions in database for testing")

            session_id = row[0]

            # Try to retrieve the closed session via API
            response = await client.get(f"{base_url}/api/sessions/{session_id}")

            # This should succeed, not return 404
            assert response.status_code == 200, (
                f"Failed to retrieve closed session {session_id}. "
                f"Status: {response.status_code}, Response: {response.text}"
            )

            # Verify the response contains the session data
            data = response.json()
            assert data["session_id"] == session_id
            assert data["status"] == "closed"
            print(f"✅ Successfully retrieved closed session: {session_id}")

    @pytest.mark.asyncio
    async def test_create_and_close_session_then_retrieve(self, running_server):
        """Test creating a session, closing it, and then retrieving it."""
        base_url, _process = running_server

        async with httpx.AsyncClient(timeout=10) as client:
            # Create a new session
            create_response = await client.post(
                f"{base_url}/api/sessions",
                json={"project_name": "test-project", "agent_name": "test-agent"},
            )

            assert create_response.status_code == 201
            session_id = create_response.json()["session_id"]
            print(f"Created session: {session_id}")

            # Close the session without executing any queries
            close_response = await client.delete(f"{base_url}/api/sessions/{session_id}")

            assert close_response.status_code == 204
            print(f"Closed session: {session_id}")

            # Wait a moment for database to persist
            await asyncio.sleep(0.5)

            # Try to retrieve the closed session
            get_response = await client.get(f"{base_url}/api/sessions/{session_id}")

            # This should succeed, not return 404
            assert get_response.status_code == 200, (
                f"Failed to retrieve closed session {session_id} immediately after closing. "
                f"Status: {get_response.status_code}, Response: {get_response.text}"
            )

            data = get_response.json()
            assert data["session_id"] == session_id
            assert data["status"] == "closed"
            assert data["query_count"] == 0
            print(f"✅ Successfully retrieved closed session with 0 queries: {session_id}")
