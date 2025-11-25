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

            # Create main project file (should be skipped by activity result loader)
            project_content = """---
name: "test-project"
type: "design-sprint"
---
# Test Project
"""
            (project_dir / "test-project.md").write_text(project_content)

            # Create sample activity result file using versioned naming
            result_content = """---
participants: "Alice, Bob"
session_id: "test-123"
version: 1
---

# Test Activity Result

This is a test activity result.
"""
            (project_dir / "test-activity_v1.md").write_text(result_content)
            (project_dir / "another-activity_v1.md").write_text(result_content)

            yield tmppath

    def test_load_result_without_md_extension(self, temp_results_dir: Path):
        """Test loading activity result by name without .md extension.

        This tests the bug fix where the loader should accept names without
        .md extension and add it internally (consistent with other loaders).
        """
        loader = ActivityResultLoader(base_path=temp_results_dir)

        # Load without .md extension (the bug case)
        result = loader.get_activity_result("test-project", "test-activity_v1")

        assert result is not None
        assert "Alice, Bob" in result.frontmatter.get("participants", "")

    def test_load_result_with_md_extension(self, temp_results_dir: Path):
        """Test loading activity result by name with .md extension.

        This ensures backwards compatibility for any code that might still
        pass the full filename with extension.
        """
        loader = ActivityResultLoader(base_path=temp_results_dir)

        # Load with .md extension
        result = loader.get_activity_result("test-project", "test-activity_v1.md")

        assert result is not None

    def test_load_nonexistent_result_returns_none(self, temp_results_dir: Path):
        """Test that loading a nonexistent result returns None."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        result = loader.get_activity_result("test-project", "nonexistent_v1")

        assert result is None

    def test_load_from_nonexistent_project_returns_none(self, temp_results_dir: Path):
        """Test that loading from a nonexistent project returns None."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        result = loader.get_activity_result("nonexistent-project", "test-activity_v1")

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

            # Create main project file (should be skipped)
            project_content = """---
name: "multi-project"
---
# Multi Project
"""
            (project_dir / "multi-project.md").write_text(project_content)

            # Create multiple activity results using versioned naming
            content1 = """---
participants: "Team A"
version: 1
---
# Activity 1
"""
            content2 = """---
participants: "Team B"
version: 1
---
# Activity 2
"""
            content3 = """---
participants: "Team A"
version: 2
---
# Activity 1 v2
"""
            (project_dir / "activity-one_v1.md").write_text(content1)
            (project_dir / "activity-two_v1.md").write_text(content2)
            (project_dir / "activity-one_v2.md").write_text(content3)

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
        """Test that results are sorted by version, most recent first."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        results = loader.list_activity_results("multi-project")

        versions = [r["version"] for r in results]
        assert versions == sorted(versions, reverse=True)

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


class TestListActivityResultsWithVersioning:
    """Tests for list_activity_results with versioned files (_vNN pattern)."""

    @pytest.fixture
    def temp_versioned_dir(self) -> Path:
        """Create a temporary directory with versioned activity files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            project_dir = tmppath / "versioned-project"
            project_dir.mkdir(parents=True)

            # Create main project file (should be skipped)
            project_content = """---
name: "versioned-project"
---
# Versioned Project
"""
            (project_dir / "versioned-project.md").write_text(project_content)

            # Create versioned activity results (the correct pattern)
            content1 = """---
participants: "Team A"
version: 1
---
# How Might We v1
"""
            content2 = """---
participants: "Team A"
version: 2
---
# How Might We v2
"""
            content3 = """---
participants: "Team B"
version: 1
---
# Design Criteria v1
"""
            (project_dir / "how-might-we_v1.md").write_text(content1)
            (project_dir / "how-might-we_v2.md").write_text(content2)
            (project_dir / "design-criteria_v1.md").write_text(content3)

            # Create old-style file with timestamp (should be ignored or handled differently)
            old_content = """---
---
# Old Style
"""
            (project_dir / "old-activity_2025-01-15.md").write_text(old_content)

            yield tmppath

    def test_list_versioned_files(self, temp_versioned_dir: Path):
        """Test that versioned files (_vNN) are correctly listed."""
        loader = ActivityResultLoader(base_path=temp_versioned_dir)

        results = loader.list_activity_results("versioned-project")

        # Should find 3 versioned files (old timestamp format should be skipped)
        versioned_results = [r for r in results if "_v" in r["filename"]]
        assert len(versioned_results) == 3

    def test_versioned_files_have_correct_metadata(self, temp_versioned_dir: Path):
        """Test that versioned files have correct activity_script extracted."""
        loader = ActivityResultLoader(base_path=temp_versioned_dir)

        results = loader.list_activity_results("versioned-project")

        # Find the how-might-we results
        hmw_results = [r for r in results if r["activity_script"] == "how-might-we"]
        assert len(hmw_results) == 2

        # Verify they have different versions
        filenames = [r["filename"] for r in hmw_results]
        assert "how-might-we_v1.md" in filenames
        assert "how-might-we_v2.md" in filenames

    def test_versioned_files_sorted_by_version(self, temp_versioned_dir: Path):
        """Test that versioned files are sorted correctly (most recent version first)."""
        loader = ActivityResultLoader(base_path=temp_versioned_dir)

        results = loader.list_activity_results("versioned-project")

        # Find how-might-we results
        hmw_results = [r for r in results if r["activity_script"] == "how-might-we"]

        # Should be sorted with v2 before v1 (descending version order)
        assert hmw_results[0]["filename"] == "how-might-we_v2.md"
        assert hmw_results[1]["filename"] == "how-might-we_v1.md"

    def test_grouping_with_versioned_files(self, temp_versioned_dir: Path):
        """Test that grouping works correctly with versioned files."""
        loader = ActivityResultLoader(base_path=temp_versioned_dir)

        results = loader.list_activity_results("versioned-project")
        grouped = loader.group_by_activity(results)

        # Should have 2 groups: how-might-we and design-criteria
        assert len(grouped) == 2

        # Find how-might-we group
        hmw_group = next((g for g in grouped if g["activity_script"] == "how-might-we"), None)
        assert hmw_group is not None
        assert len(hmw_group["executions"]) == 2

    def test_date_field_mapped_to_created_at(self, temp_versioned_dir: Path):
        """Test that 'date' field in frontmatter is mapped to 'created_at'."""
        loader = ActivityResultLoader(base_path=temp_versioned_dir)

        # Create a file with 'date' field
        project_dir = temp_versioned_dir / "test-date-project"
        project_dir.mkdir(parents=True)

        content_with_date = """---
date: 2025-11-25
version: 1
---
# Test with date field
"""
        (project_dir / "test-activity_v1.md").write_text(content_with_date)

        results = loader.list_activity_results("test-date-project")

        assert len(results) == 1
        assert results[0]["created_at"] == "2025-11-25"

    def test_created_at_field_fallback(self, temp_versioned_dir: Path):
        """Test that 'created_at' field is used if 'date' is not present."""
        loader = ActivityResultLoader(base_path=temp_versioned_dir)

        # Create a file with 'created_at' field
        project_dir = temp_versioned_dir / "test-created-at-project"
        project_dir.mkdir(parents=True)

        content_with_created_at = """---
created_at: 2025-11-26
version: 1
---
# Test with created_at field
"""
        (project_dir / "test-activity_v1.md").write_text(content_with_created_at)

        results = loader.list_activity_results("test-created-at-project")

        assert len(results) == 1
        assert results[0]["created_at"] == "2025-11-26"


class TestSaveActivityResult:
    """Tests for save_activity_result method."""

    @pytest.fixture
    def temp_results_dir(self) -> Path:
        """Create a temporary directory for testing saves.

        Returns:
            Path: Temporary directory path
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_save_adds_md_extension_if_missing(self, temp_results_dir):
        """Test that .md extension is added if not present."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        content = """---
---

# Test Result
"""
        # Save without .md extension
        success = loader.save_activity_result("test-project", "test-result", content)

        assert success is True
        # Verify file was created with .md extension
        result_file = temp_results_dir / "test-project" / "test-result.md"
        assert result_file.exists()
        assert result_file.read_text() == content

    def test_save_keeps_md_extension_if_present(self, temp_results_dir):
        """Test that existing .md extension is preserved."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        content = """---
---

# Test Result
"""
        # Save with .md extension
        success = loader.save_activity_result("test-project", "test-result.md", content)

        assert success is True
        # Verify file was created (not test-result.md.md)
        result_file = temp_results_dir / "test-project" / "test-result.md"
        assert result_file.exists()
        assert result_file.read_text() == content

        # Make sure no double extension was created
        double_ext_file = temp_results_dir / "test-project" / "test-result.md.md"
        assert not double_ext_file.exists()

    def test_save_creates_project_directory_if_missing(self, temp_results_dir):
        """Test that project directory is created if it doesn't exist."""
        loader = ActivityResultLoader(base_path=temp_results_dir)

        content = "# Test"
        success = loader.save_activity_result("new-project", "result", content)

        assert success is True
        project_dir = temp_results_dir / "new-project"
        assert project_dir.exists()
        assert project_dir.is_dir()


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
