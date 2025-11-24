#!/usr/bin/env python3.13
"""Basic validation script to test core functionality without circular imports.

This script validates:
1. SQLite persistence works
2. Events can be created
3. Basic functionality is operational

This avoids pytest and import issues for quick validation.
"""

import asyncio
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_sqlite_persistence():
    """Test SQLite repository basic operations."""
    print("Testing SQLite persistence...")

    # Import directly
    from collab_sims.persistence.sqlite_repository import SQLiteRepository

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Initialize
        repo = SQLiteRepository(db_path)
        await repo.initialize()

        # Create session
        session_id = "test-session-123"
        await repo.create_session(
            session_id=session_id,
            user_id="test-user",
            created_at=datetime.now(),
            project_name="test-project",
            metadata={"test": "data"}
        )

        # Get session
        session = await repo.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["metadata"]["test"] == "data"

        # Add event
        await repo.add_event(
            session_id=session_id,
            event_type="message",
            timestamp=datetime.now(),
            data={"content": "test message"}
        )

        # Get events
        events = await repo.get_events(session_id)
        assert len(events) == 1
        assert events[0]["data"]["content"] == "test message"

        # Cleanup
        await repo.close()

        print("✅ SQLite persistence tests passed!")
        return True

    except Exception as e:
        print(f"❌ SQLite persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Remove temp file
        Path(db_path).unlink(missing_ok=True)


async def test_events():
    """Test event creation."""
    print("\nTesting events...")

    try:
        from collab_sims.core.events import (
            EventType,
            MessageEvent,
            SessionStartEvent,
        )

        # Create message event
        event = MessageEvent(
            role="assistant",
            content="Test message",
            session_id="test"
        )

        assert event.type == EventType.MESSAGE
        assert event.content == "Test message"
        assert event.event_id is not None

        # Create session start event
        start_event = SessionStartEvent(
            session_id="test",
            user_id="user1"
        )

        assert start_event.type == EventType.SESSION_START
        assert start_event.session_id == "test"

        # Convert to dict
        event_dict = event.to_dict()
        assert "content" in event_dict
        assert event_dict["content"] == "Test message"

        print("✅ Event tests passed!")
        return True

    except Exception as e:
        print(f"❌ Event test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validations."""
    print("=" * 60)
    print("COLLAB-SIMS VALIDATION")
    print("=" * 60)

    results = []

    # Test persistence
    results.append(await test_sqlite_persistence())

    # Test events
    results.append(await test_events())

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✅ ALL VALIDATIONS PASSED")
        return 0
    else:
        print("\n❌ SOME VALIDATIONS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
