"""Pytest configuration and shared fixtures.

This module provides shared fixtures used across all tests.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path.

    Returns:
        str: Path to temporary database file

    Example:
        >>> def test_something(temp_db_path):
        ...     repo = SQLiteRepository(temp_db_path)
        ...     # Test with temporary database
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_work_dir():
    """Create a temporary working directory.

    Returns:
        Path: Path to temporary directory

    Example:
        >>> def test_something(temp_work_dir):
        ...     file_path = temp_work_dir / "test.txt"
        ...     file_path.write_text("test")
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
