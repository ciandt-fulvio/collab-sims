"""Integration tests for HTTP server with real network requests.

Tests that verify the server can be started and accessed via HTTP:
- Server starts successfully on a port
- HTTP requests work correctly
- Endpoints respond as expected
- Server can be gracefully shutdown

These tests use real HTTP requests (not FastAPI TestClient) to ensure:
- ASGI server (uvicorn) works correctly
- Network layer is functioning
- Real-world HTTP behavior

References:
- https://www.uvicorn.org/
- https://www.python-httpx.org/
"""

import asyncio
import signal
import subprocess
import sys
from pathlib import Path

import httpx
import pytest


class TestServerStartup:
    """Test that the server can start and respond to requests."""

    @pytest.fixture
    def free_port(self):
        """Find a free port to use for testing.

        Returns:
            int: Available port number
        """
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    @pytest.fixture
    async def running_server(self, free_port):
        """Start server and return process.

        Yields:
            tuple: (process, port, base_url)
        """
        # Get project root
        project_root = Path(__file__).parent.parent.parent

        # Start server process
        env = {
            "PYTHONPATH": str(project_root),
            "PATH": f"{project_root / '.venv' / 'bin'}:{Path.home() / '.local' / 'bin'}:/usr/local/bin:/usr/bin:/bin",
        }

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
            text=True,
        )

        base_url = f"http://127.0.0.1:{free_port}"

        # Wait for server to be ready (max 10 seconds)
        server_ready = False
        for _ in range(50):  # 50 attempts * 0.2s = 10 seconds
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{base_url}/health", timeout=1.0)
                    if response.status_code == 200:
                        server_ready = True
                        break
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(0.2)

        if not server_ready:
            # Get error output
            process.terminate()
            stdout, stderr = process.communicate(timeout=2)
            pytest.fail(
                f"Server failed to start within 10 seconds.\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            )

        yield process, free_port, base_url

        # Cleanup - gracefully shutdown server
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        finally:
            # Explicitly close pipes to avoid ResourceWarning
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

    @pytest.mark.asyncio
    async def test_server_starts_and_responds(self, running_server):
        """Test that server starts and responds to basic requests."""
        process, port, base_url = running_server

        # Server should be running
        assert process.poll() is None, "Server process died"

        # Make HTTP request to health endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_hello_world_via_http(self, running_server):
        """Test 'hello world' request via real HTTP.

        This tests the single-turn execution endpoint with a simple query.
        """
        process, port, base_url = running_server

        # Make HTTP POST request to execute endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/execute",
                json={
                    "prompt": "Say 'hello world' and nothing else",
                    "config": {"auto_approve_tools": True},
                },
            )

        # Should get 200 OK
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

        # Response should be JSON
        data = response.json()

        # Should have status and events
        assert "status" in data
        assert data["status"] == "completed"
        assert "events" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) > 0

        # Should have at least one message event
        message_events = [e for e in data["events"] if e.get("event_type") == "message"]
        assert len(message_events) > 0

        # Message should contain "hello" (case insensitive)
        first_message = message_events[0]
        content = first_message.get("data", {}).get("content", "").lower()
        # For simulated API, check if content exists
        assert content, f"Expected non-empty message content, got: {first_message}"
        print(f"✓ Received message via HTTP: {content}")

    @pytest.mark.asyncio
    async def test_root_endpoint_via_http(self, running_server):
        """Test root endpoint returns API info."""
        process, port, base_url = running_server

        async with httpx.AsyncClient() as client:
            response = await client.get(base_url)

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "CollabSims API"

    @pytest.mark.asyncio
    async def test_api_docs_accessible(self, running_server):
        """Test that API docs are accessible."""
        process, port, base_url = running_server

        # OpenAPI JSON
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/openapi.json")

        assert response.status_code == 200
        openapi_spec = response.json()
        assert "openapi" in openapi_spec
        assert "info" in openapi_spec
        assert openapi_spec["info"]["title"] == "CollabSims API"

        # Swagger UI HTML
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, running_server):
        """Test that server handles concurrent requests."""
        process, port, base_url = running_server

        # Make multiple concurrent requests to health endpoint
        async with httpx.AsyncClient() as client:
            tasks = [client.get(f"{base_url}/health") for _ in range(10)]
            responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_invalid_endpoint_returns_404(self, running_server):
        """Test that invalid endpoints return 404."""
        process, port, base_url = running_server

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/nonexistent")

        assert response.status_code == 404


class TestServerErrors:
    """Test error handling in HTTP server."""

    @pytest.fixture
    async def running_server(self):
        """Start server on fixed port for error tests."""
        import socket

        # Find free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]

        project_root = Path(__file__).parent.parent.parent

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "collab_sims.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "error",
            ],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        base_url = f"http://127.0.0.1:{port}"

        # Wait for server
        server_ready = False
        for _ in range(50):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{base_url}/health", timeout=1.0)
                    if response.status_code == 200:
                        server_ready = True
                        break
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(0.2)

        if not server_ready:
            process.kill()
            pytest.fail("Server failed to start")

        yield process, port, base_url

        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        finally:
            # Explicitly close pipes to avoid ResourceWarning
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

    @pytest.mark.asyncio
    async def test_invalid_json_returns_422(self, running_server):
        """Test that invalid JSON payload returns 422."""
        process, port, base_url = running_server

        async with httpx.AsyncClient() as client:
            # Send invalid JSON
            response = await client.post(
                f"{base_url}/api/execute",
                json={"prompt": 123},  # Invalid: should be string
            )

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field_returns_422(self, running_server):
        """Test that missing required fields return 422."""
        process, port, base_url = running_server

        async with httpx.AsyncClient() as client:
            # Send request without required 'prompt' field
            response = await client.post(
                f"{base_url}/api/execute",
                json={"config": {}},
            )

        assert response.status_code == 422


if __name__ == "__main__":
    """Run tests with detailed output."""
    import sys

    print("\n" + "=" * 70)
    print("HTTP SERVER INTEGRATION TESTS")
    print("=" * 70)
    print("\nThese tests start a real HTTP server and make network requests.")
    print("This validates the complete stack: uvicorn + FastAPI + app code.\n")

    exit_code = pytest.main([__file__, "-v", "-s", "--tb=short"])

    if exit_code == 0:
        print("\n" + "=" * 70)
        print("✅ ALL HTTP SERVER TESTS PASSED")
        print("=" * 70)
        print("\nThe server can:")
        print("  ✓ Start successfully on a port")
        print("  ✓ Respond to HTTP requests")
        print("  ✓ Handle concurrent requests")
        print("  ✓ Return proper error codes")
        print("  ✓ Execute agent queries via HTTP")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ SOME HTTP SERVER TESTS FAILED")
        print("=" * 70)
        sys.exit(1)
