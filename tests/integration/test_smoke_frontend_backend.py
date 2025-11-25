"""
Smoke tests for frontend-backend integration.

Tests critical paths discovered during exploratory testing to prevent regression.
These are fast, simple integration tests that validate the most common failure points.

Run with:
    pytest tests/integration/test_smoke_frontend_backend.py -v
    pytest tests/integration/test_smoke_frontend_backend.py -v -m smoke
"""

import pytest
from fastapi.testclient import TestClient

from collab_sims.api.main import app

pytestmark = [pytest.mark.integration, pytest.mark.smoke]


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestLibraryAPIEndpoints:
    """Test that library API endpoints are accessible and return correct data.

    Bug #2: Library API routes returned 404 due to missing /api prefix.
    """

    def test_list_projects_endpoint_accessible(self, client):
        """Verify /api/library/projects returns 200 (not 404)."""
        response = client.get("/api/library/projects")

        assert response.status_code == 200, (
            f"Library projects endpoint should return 200, got {response.status_code}. "
            "Check that router prefix includes '/api'"
        )
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_list_agents_endpoint_accessible(self, client):
        """Verify /api/library/agents returns 200 (not 404)."""
        response = client.get("/api/library/agents")

        assert response.status_code == 200, (
            f"Library agents endpoint should return 200, got {response.status_code}"
        )
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_list_activity_scripts_endpoint_accessible(self, client):
        """Verify /api/library/activity-scripts returns 200 (not 404).

        Bug #4: Frontend used underscore (activity_scripts) but backend uses hyphen.
        """
        # Test with hyphen (correct)
        response = client.get("/api/library/activity-scripts")

        assert response.status_code == 200, (
            f"Activity scripts endpoint should return 200, got {response.status_code}. "
            "Frontend must use 'activity-scripts' (hyphen, not underscore)"
        )
        data = response.json()
        assert "activity_scripts" in data
        assert isinstance(data["activity_scripts"], list)


class TestSessionCreationAndMetadata:
    """Test that session creation returns all required fields.

    Bug #3: Session response was missing project_name, agent_name, session_name
    causing Pydantic validation errors (500).

    Note: These tests require full server initialization (startup event).
    They are skipped in unit test mode.
    """

    @pytest.mark.skip(reason="Requires full server with startup event and Claude SDK")
    def test_create_session_returns_required_fields(self, client):
        """Verify session creation returns project_name, agent_name, session_name."""
        # Create a session with project and agent
        response = client.post(
            "/api/sessions",
            json={
                "project_name": "design-sprint-q1",
                "agent_name": "facilitator",
                "config": {
                    "include_partial_messages": True,
                    "approval_config": {
                        "mode": "auto",
                        "tool_policies": {},
                        "auto_approved_tools": [],
                    },
                },
            },
        )

        # Should return 200, not 500 (internal server error)
        assert response.status_code == 200, (
            f"Session creation should succeed, got {response.status_code}: {response.text}"
        )

        data = response.json()

        # All required fields must be present (bug #3)
        assert "session_id" in data, "Response must include session_id"
        assert "project_name" in data, "Response must include project_name (bug #3)"
        assert "agent_name" in data, "Response must include agent_name (bug #3)"
        assert "session_name" in data, "Response must include session_name (bug #3)"
        assert "created_at" in data, "Response must include created_at"
        assert "status" in data, "Response must include status"

        # Verify values match request
        assert data["project_name"] == "design-sprint-q1"
        assert data["agent_name"] == "facilitator"

        # session_type should NOT be present (removed in migration)
        assert "session_type" not in data, (
            "session_type is deprecated and should not be in response"
        )

    @pytest.mark.skip(reason="Requires full server with startup event and Claude SDK")
    def test_list_sessions_includes_project_fields(self, client):
        """Verify session list includes project/agent fields."""
        # Create a session first
        create_response = client.post(
            "/api/sessions",
            json={
                "project_name": "research-ux",
                "agent_name": "researcher",
                "config": {"include_partial_messages": True},
            },
        )
        assert create_response.status_code == 200

        # List sessions
        list_response = client.get("/api/sessions")
        assert list_response.status_code == 200

        data = list_response.json()
        assert "sessions" in data
        assert len(data["sessions"]) > 0

        # Check that each session has required fields
        for session in data["sessions"]:
            assert "project_name" in session, "List must include project_name"
            assert "agent_name" in session, "List must include agent_name"


class TestEndpointNamingConsistency:
    """Test that frontend and backend use consistent endpoint URLs.

    Bug #4: Frontend used 'activity_scripts' but backend uses 'activity-scripts'.
    """

    def test_activity_scripts_uses_hyphen_not_underscore(self, client):
        """Verify activity-scripts endpoint uses hyphen (backend convention)."""
        # Correct URL (hyphen)
        correct_response = client.get("/api/library/activity-scripts")
        assert correct_response.status_code == 200

        # Incorrect URL (underscore) should fail
        wrong_response = client.get("/api/library/activity_scripts")
        assert wrong_response.status_code == 404, (
            "Frontend must use 'activity-scripts' with hyphen, not underscore"
        )


class TestCriticalWorkflow:
    """End-to-end smoke test for the most common user workflow.

    Note: This test requires full server initialization.
    Run with: pytest tests/integration/test_smoke_frontend_backend.py::TestCriticalWorkflow -v --no-skip
    """

    @pytest.mark.skip(reason="Requires full server with startup event and Claude SDK")
    def test_complete_session_creation_workflow(self, client):
        """Test: List projects → Select project → Create session → Verify session.

        This is the critical path users take when starting a new session.
        """
        # Step 1: List projects (library tab)
        projects_response = client.get("/api/library/projects")
        assert projects_response.status_code == 200
        projects = projects_response.json()["projects"]
        assert len(projects) > 0, "Should have at least one project"

        # Step 2: List agents (agent selector)
        agents_response = client.get("/api/library/agents")
        assert agents_response.status_code == 200
        agents = agents_response.json()["agents"]
        assert len(agents) > 0, "Should have at least one agent"

        # Step 3: Create session with first project and agent
        project_name = projects[0]["name"]
        agent_name = agents[0]["name"]

        create_response = client.post(
            "/api/sessions",
            json={
                "project_name": project_name,
                "agent_name": agent_name,
                "config": {"include_partial_messages": True},
            },
        )
        assert create_response.status_code == 200, (
            f"Session creation failed: {create_response.text}"
        )

        session_data = create_response.json()
        session_id = session_data["session_id"]

        # Step 4: Load session details (what chat page does)
        session_response = client.get(f"/api/sessions/{session_id}")
        assert session_response.status_code == 200

        loaded_session = session_response.json()
        assert loaded_session["project_name"] == project_name
        assert loaded_session["agent_name"] == agent_name

        # Step 5: Load library resources (for Library tab)
        lib_projects = client.get("/api/library/projects")
        lib_agents = client.get("/api/library/agents")
        lib_scripts = client.get("/api/library/activity-scripts")

        # All library endpoints must work (bug #2, #4)
        for resp in [lib_projects, lib_agents, lib_scripts]:
            assert resp.status_code == 200, f"Library endpoint failed: {resp.url}"
