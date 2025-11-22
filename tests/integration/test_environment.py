"""Integration tests for environment setup and dependencies.

Tests that verify the development environment is correctly configured:
- Python version requirements
- Critical dependencies are installed
- Module imports work correctly
- API can be initialized

These tests help catch issues like:
- Wrong Python version
- Missing dependencies (e.g., attrs, jsonschema)
- Import errors
- Broken package installations

References:
- https://docs.python.org/3/library/sys.html
- https://docs.pytest.org/
"""

import importlib
import sys
from pathlib import Path

import pytest


class TestPythonVersion:
    """Test Python version requirements."""

    def test_python_version_is_3_13_or_higher(self):
        """Verify Python version meets minimum requirement.

        The project requires Python 3.13+ as specified in pyproject.toml.
        Running with older versions can cause compatibility issues.
        """
        version_info = sys.version_info
        actual_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        assert version_info.major == 3, f"Python 3.x required, got {actual_version}"
        assert (
            version_info.minor >= 13
        ), f"Python 3.13+ required, got {actual_version}"

    def test_python_executable_path(self):
        """Verify Python executable is from expected location.

        This helps detect if the wrong Python interpreter is being used.
        """
        executable = Path(sys.executable)
        assert executable.exists(), f"Python executable not found: {executable}"

        # Should either be in .venv or a system Python 3.13+
        is_venv = ".venv" in str(executable)
        is_system_313_plus = sys.version_info >= (3, 13)

        assert (
            is_venv or is_system_313_plus
        ), f"Expected venv or Python 3.13+, got {executable}"


class TestCriticalDependencies:
    """Test that all critical dependencies are installed."""

    @pytest.mark.parametrize(
        "package_name,min_version",
        [
            ("attrs", "22.2.0"),  # Required by jsonschema
            ("jsonschema", "4.20.0"),  # Required by mcp
            ("fastapi", "0.115.0"),  # Web framework
            ("uvicorn", "0.30.0"),  # ASGI server
            ("pydantic", "2.9.0"),  # Data validation
            ("aiosqlite", "0.20.0"),  # Async SQLite
            ("loguru", "0.7.0"),  # Logging
            ("claude_agent_sdk", "0.1.6"),  # Claude Agent SDK
        ],
    )
    def test_dependency_is_installed(self, package_name, min_version):
        """Test that a critical dependency is installed.

        Args:
            package_name: Name of the package to check
            min_version: Minimum required version (for documentation)
        """
        try:
            module = importlib.import_module(package_name.replace("-", "_"))
            assert module is not None, f"Failed to import {package_name}"

            # Try to get version if available
            version = getattr(module, "__version__", None)
            if version:
                print(f"✓ {package_name} version {version} (min: {min_version})")
            else:
                print(f"✓ {package_name} installed (version unknown)")

        except ImportError as e:
            pytest.fail(
                f"Critical dependency '{package_name}' not installed: {e}\n"
                f"Run: pip install -e . to install all dependencies"
            )

    def test_attrs_module_accessible(self):
        """Specific test for attrs module that caused the original error.

        This was the missing dependency that caused ModuleNotFoundError.
        """
        try:
            from attrs import define

            # Test that we can use basic attrs functionality
            @define
            class TestClass:
                value: str

            obj = TestClass(value="test")
            assert obj.value == "test"

        except ImportError as e:
            pytest.fail(
                f"attrs module not accessible: {e}\n"
                "This is a transitive dependency of jsonschema.\n"
                "Run: pip install attrs"
            )


class TestCoreModuleImports:
    """Test that all core modules can be imported."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "collab_sims",
            "collab_sims.core.agent",
            "collab_sims.core.events",
            "collab_sims.core.session",
            "collab_sims.api.main",
            "collab_sims.persistence.sqlite_repository",
            "collab_sims.trackers.base",
        ],
    )
    def test_module_imports_successfully(self, module_path):
        """Test that a core module can be imported without errors.

        Args:
            module_path: Dotted path to the module
        """
        try:
            module = importlib.import_module(module_path)
            assert module is not None, f"Module {module_path} is None"
            print(f"✓ {module_path} imported successfully")

        except ImportError as e:
            pytest.fail(
                f"Failed to import {module_path}: {e}\n"
                "This indicates a dependency or import issue."
            )
        except Exception as e:
            pytest.fail(
                f"Unexpected error importing {module_path}: {e}\n"
                f"Error type: {type(e).__name__}"
            )

    def test_collabsims_agent_class_accessible(self):
        """Test that the main CollabSims agent class can be instantiated."""
        try:
            from collab_sims.core.agent import CollabSims

            agent = CollabSims()
            assert agent is not None
            assert hasattr(agent, "execute")
            assert hasattr(agent, "create_session")

        except Exception as e:
            pytest.fail(f"Failed to instantiate CollabSims: {e}")


class TestAPIInitialization:
    """Test that the FastAPI application can be initialized."""

    def test_fastapi_app_imports(self):
        """Test that the FastAPI app can be imported."""
        try:
            from collab_sims.api.main import app

            assert app is not None
            assert hasattr(app, "routes")

        except ImportError as e:
            pytest.fail(
                f"Failed to import FastAPI app: {e}\n"
                "Check for missing dependencies or import errors."
            )

    def test_api_routes_registered(self):
        """Test that API routes are registered."""
        from collab_sims.api.main import app

        # Get all registered routes
        routes = [route.path for route in app.routes]

        # Should have at least these critical routes
        expected_routes = [
            "/",
            "/health",
            "/sessions",
            "/execute",
        ]

        for route in expected_routes:
            matching_routes = [r for r in routes if route in r]
            assert (
                len(matching_routes) > 0
            ), f"Expected route '{route}' not found in {routes}"

    def test_api_can_create_test_client(self):
        """Test that a test client can be created for the API."""
        try:
            from fastapi.testclient import TestClient

            from collab_sims.api.main import app

            client = TestClient(app)
            assert client is not None

            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200

        except Exception as e:
            pytest.fail(f"Failed to create test client: {e}")


class TestEnvironmentConfiguration:
    """Test environment configuration and setup."""

    def test_can_detect_venv(self):
        """Test that we can detect if running in a virtual environment."""
        # Check common venv indicators
        has_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        # Print diagnostic info
        print(f"\nPython executable: {sys.executable}")
        print(f"Base prefix: {sys.base_prefix}")
        print(f"Prefix: {sys.prefix}")
        print(f"In virtual env: {has_venv}")

        # This is informational - not a hard requirement
        if not has_venv:
            print(
                "⚠️  Not running in a virtual environment. "
                "Consider using: python3.13 -m venv .venv"
            )

    def test_site_packages_accessible(self):
        """Test that site-packages directory is accessible."""
        import site

        site_packages = site.getsitepackages()
        assert len(site_packages) > 0, "No site-packages found"

        for path in site_packages:
            path_obj = Path(path)
            if path_obj.exists():
                print(f"✓ Site packages: {path}")
                break
        else:
            pytest.fail("No accessible site-packages directory found")


class TestPackageIntegration:
    """Test integration between packages."""

    def test_claude_sdk_uses_mcp(self):
        """Test that Claude SDK can access MCP types.

        This was part of the import chain that caused the original error.
        """
        try:
            from mcp.types import Tool

            # Should be able to create a simple tool definition
            assert Tool is not None

        except ImportError as e:
            pytest.fail(
                f"Failed to import MCP types: {e}\n"
                "Claude Agent SDK requires MCP package."
            )

    def test_jsonschema_validation_works(self):
        """Test that jsonschema validation works (uses attrs internally)."""
        try:
            from jsonschema import validate

            # Simple schema validation
            schema = {"type": "object", "properties": {"name": {"type": "string"}}}

            data = {"name": "test"}

            # Should not raise
            validate(instance=data, schema=schema)

        except Exception as e:
            pytest.fail(f"jsonschema validation failed: {e}")


if __name__ == "__main__":
    """Run tests with verbose output."""
    import sys

    # Track validation failures
    all_validation_failures = []
    total_tests = 0

    print("\n" + "=" * 70)
    print("ENVIRONMENT VALIDATION TESTS")
    print("=" * 70)

    # Run pytest with verbose output
    exit_code = pytest.main([__file__, "-v", "-s", "--tb=short"])

    # Report results
    if exit_code == 0:
        print("\n" + "=" * 70)
        print("✅ VALIDATION PASSED - Environment is correctly configured")
        print("=" * 70)
        print("\nYou can now run:")
        print("  ./run_api.sh    # Start the API server")
        print("  pytest          # Run all tests")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ VALIDATION FAILED - Environment has issues")
        print("=" * 70)
        print("\nCommon fixes:")
        print("  1. Ensure Python 3.13+ is installed")
        print("  2. Create venv: python3.13 -m venv .venv")
        print("  3. Activate venv: source .venv/bin/activate")
        print("  4. Install deps: pip install -e .")
        sys.exit(1)
