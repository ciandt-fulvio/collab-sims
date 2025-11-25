"""Unit tests for ActivityResultLoader.

Tests the activity result loader functionality, including:
- Loading activity results with and without .md extension
- Error handling for missing files
- Listing and grouping results

References:
- https://docs.python.org/3/library/pathlib.html
"""

import tempfile
from pathlib import Path

import pytest

from collab_sims.core.loaders import ActivityResultLoader


class TestGetActivityResult:
    """Tests for get_activity_result method."""

    @pytest.fixture
    def temp_results_dir(self) -> Path:
        """Create a temporary directory with test activity result files.

        Returns:
            Path: Temporary directory path
        """
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

This is a test activity result.
"""
            (project_dir / "test-activity_2025-01-15.md").write_text(result_content)
            (project_dir / "another-activity_2025-01-20.md").write_text(result_content)

            yield tmppath

    def test_load_result_without_md_extension(self, temp_results_dir: Path):
        """Test loading activity result by name without .md extension.

        This tests the bug fix where the loader should accept names without
        .md extension and add it internally (consistent with other loaders).
        """
        loader = ActivityResultLoader(base_path=temp_results_dir)

        # Load without .md extension (the bug case)
        result = loader.get_activity_result("test-project", "test-activity_2025-01-15")

        assert result is not None
        assert result.frontmatter.get("status") == "completed"
        assert "Alice, Bob" in result.frontmatter.get("participants", "")

    def test_load_result_with_md_extension(self, temp_results_dir: Path):
        """Test loading activity result by name with .md extension.

        This ensures backwards compatibility for any code that might still
        pass the full filename with extension.
        """
        loader = ActivityResultLoader(base_path=temp_results_dir)

        # Load with .md extension
        result = loader.get_activity_result("test-project", "test-activity_2025-01-15.md")

        assert result is not None
        assert result.frontmatter.get("status") == "completed"

    def test_load_nonexistent_result_returns_none(self, temp_results_dir: Path):
        """Test that loading a nonexistent result returns None."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        result = loader.get_activity_result("test-project", "nonexistent_2025-01-01")

        assert result is None

    def test_load_from_nonexistent_project_returns_none(self, temp_results_dir: Path):
        """Test that loading from a nonexistent project returns None."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        result = loader.get_activity_result("nonexistent-project", "test-activity_2025-01-15")

        assert result is None


class TestListActivityResults:
    """Tests for list_activity_results method."""

    @pytest.fixture
    def temp_results_dir(self) -> Path:
        """Create a temporary directory with multiple test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            project_dir = tmppath / "multi-project"
            project_dir.mkdir(parents=True)

            # Create multiple activity results
            content1 = """---
status: completed
participants: "Team A"
---
# Activity 1
"""
            content2 = """---
status: in_progress
participants: "Team B"
---
# Activity 2
"""
            (project_dir / "activity-one_2025-01-15.md").write_text(content1)
            (project_dir / "activity-two_2025-01-20.md").write_text(content2)
            (project_dir / "activity-one_2025-01-10.md").write_text(content1)

            # Create an invalid file (won't match naming pattern)
            (project_dir / "invalid-file.md").write_text("# Invalid")

            yield tmppath

    def test_list_results_returns_all_valid_files(self, temp_results_dir: Path):
        """Test that list_activity_results returns all valid files."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        results = loader.list_activity_results("multi-project")

        # Should have 3 valid results (invalid-file.md skipped)
        assert len(results) == 3

    def test_list_results_sorted_by_date_descending(self, temp_results_dir: Path):
        """Test that results are sorted by date, most recent first."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        results = loader.list_activity_results("multi-project")

        dates = [r["created_at"] for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_list_results_for_nonexistent_project(self, temp_results_dir: Path):
        """Test that nonexistent project returns empty list."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        results = loader.list_activity_results("nonexistent-project")

        assert results == []


class TestGroupByActivity:
    """Tests for group_by_activity method."""

    @pytest.fixture
    def sample_results(self) -> list[dict]:
        """Create sample results for grouping tests."""
        return [
            {"activity_script": "design-review", "created_at": "2025-01-20"},
            {"activity_script": "brainstorm", "created_at": "2025-01-15"},
            {"activity_script": "design-review", "created_at": "2025-01-10"},
            {"activity_script": "brainstorm", "created_at": "2025-01-05"},
        ]

    def test_groups_results_by_activity_name(self, sample_results):
        """Test that results are grouped by activity script name."""
        loader = ActivityResultLoader()

        groups = loader.group_by_activity(sample_results)

        # Should have 2 groups
        assert len(groups) == 2

        # Find each group
        brainstorm_group = next((g for g in groups if g["activity_script"] == "brainstorm"), None)
        design_group = next((g for g in groups if g["activity_script"] == "design-review"), None)

        assert brainstorm_group is not None
        assert design_group is not None
        assert len(brainstorm_group["executions"]) == 2
        assert len(design_group["executions"]) == 2

    def test_groups_sorted_alphabetically(self, sample_results):
        """Test that groups are sorted alphabetically by activity name."""
        loader = ActivityResultLoader()

        groups = loader.group_by_activity(sample_results)

        activity_names = [g["activity_script"] for g in groups]
        assert activity_names == sorted(activity_names)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
