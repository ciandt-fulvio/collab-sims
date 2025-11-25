"""Integration tests for Documents API.

Tests the document management API endpoints:
- GET /api/documents/{doc_type}/{name} - Load document
- PUT /api/documents/{doc_type}/{name} - Save document
- POST /api/documents/{doc_type}/{name}/version - Save document version

References:
- FastAPI TestClient: https://fastapi.tiangolo.com/tutorial/testing/
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from collab_sims.api.main import app


class TestDocumentsAPI:
    """Test documents API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the API."""
        return TestClient(app)

    @pytest.fixture
    def temp_activity_results_dir(self):
        """Create temporary directory with test activity results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project directory
            project_dir = tmppath / "test-project"
            project_dir.mkdir(parents=True)

            # Create sample activity result file
            result_content = """---
status: completed
participants: "Alice, Bob"
session_id: "test-123"
---

# Test Activity Result

This is a test activity result for API testing.
"""
            (project_dir / "test-activity_2025-01-15.md").write_text(result_content)

            yield tmppath

    def test_get_activity_result_without_md_extension(
        self, client: TestClient, temp_activity_results_dir: Path
    ):
        """Test loading activity result by name without .md extension.

        This is the main regression test for the bug where the API was
        returning 404 because it didn't add .md extension to the filename.
        """
        # Patch the loader to use temp directory
        with patch(
            "collab_sims.api.routes.documents.activity_result_loader.base_path",
            temp_activity_results_dir,
        ):
            response = client.get(
                "/api/documents/activity_result/test-activity_2025-01-15",
                params={"project_name": "test-project"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-activity_2025-01-15"
        assert data["type"] == "activity_result"
        assert "Test Activity Result" in data["content"]
        assert data["frontmatter"]["status"] == "completed"

    def test_get_activity_result_requires_project_name(self, client: TestClient):
        """Test that project_name is required for activity_result type."""
        response = client.get("/api/documents/activity_result/test-activity_2025-01-15")

        assert response.status_code == 400
        assert "project_name query parameter required" in response.json()["detail"]

    def test_get_nonexistent_activity_result_returns_404(
        self, client: TestClient, temp_activity_results_dir: Path
    ):
        """Test that requesting nonexistent document returns 404."""
        with patch(
            "collab_sims.api.routes.documents.activity_result_loader.base_path",
            temp_activity_results_dir,
        ):
            response = client.get(
                "/api/documents/activity_result/nonexistent_2025-01-01",
                params={"project_name": "test-project"},
            )

        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]

    def test_get_invalid_doc_type_returns_400(self, client: TestClient):
        """Test that invalid document type returns 400."""
        response = client.get("/api/documents/invalid_type/some_name")

        assert response.status_code == 400
        assert "Invalid document type" in response.json()["detail"]


class TestDocumentsAPIPrefixRouting:
    """Test that documents API is correctly routed under /api prefix."""

    @pytest.fixture
    def client(self):
        """Create a test client for the API."""
        return TestClient(app)

    def test_documents_api_has_correct_prefix(self, client: TestClient):
        """Test that /api/documents route exists (not /documents)."""
        # This should return 400 (bad request) because project_name is missing
        # But it should NOT return 404 (not found) which would indicate wrong routing
        response = client.get("/api/documents/activity_result/test")

        # 400 means route exists but validation failed (expected)
        assert response.status_code == 400

    def test_old_path_without_api_prefix_returns_404(self, client: TestClient):
        """Test that the old path without /api prefix returns 404."""
        response = client.get("/documents/activity_result/test")

        # Should be 404 because this route doesn't exist anymore
        assert response.status_code == 404


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
