"""Pytest configuration and shared fixtures.

This module provides shared fixtures used across all tests.
Optimized for fast test execution with appropriate scopes.

References:
- https://docs.pytest.org/en/stable/fixture.html
"""

import tempfile
from pathlib import Path

import pytest

# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def temp_db_path():
    """Create a temporary database file path (function-scoped for isolation).

    Returns:
        str: Path to temporary database file

    Example:
        >>> def test_something(temp_db_path):
        ...     repo = SQLiteRepository(temp_db_path)
        ...     # Test with temporary database
    """
    # Create temp file and explicitly close it before yielding path
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = f.name
    f.close()  # Explicitly close to avoid ResourceWarning

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def temp_work_dir():
    """Create a temporary working directory (function-scoped for isolation).

    Returns:
        Path: Path to temporary directory

    Example:
        >>> def test_something(temp_work_dir):
        ...     file_path = temp_work_dir / "test.txt"
        ...     file_path.write_text("test")
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# Performance Optimization Settings
# ============================================================================


def pytest_configure(config):
    """Configure pytest for optimal performance.

    This hook runs before test collection starts.
    """
    # Set asyncio fixture loop scope to function for faster tests
    config.option.asyncio_default_fixture_loop_scope = "function"


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location.

    - tests/unit/* → @pytest.mark.unit
    - tests/integration/* → @pytest.mark.integration
    - Tests with 'slow' in name → @pytest.mark.slow
    """
    for item in items:
        # Get the test file path relative to tests directory
        test_path = Path(item.fspath).relative_to(Path(item.config.rootdir) / "tests")

        # Auto-mark based on directory
        if test_path.parts[0] == "unit":
            item.add_marker(pytest.mark.unit)
        elif test_path.parts[0] == "integration":
            item.add_marker(pytest.mark.integration)
            # Integration tests are typically slower
            item.add_marker(pytest.mark.timeout(60))

        # Auto-mark slow tests
        if "slow" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
