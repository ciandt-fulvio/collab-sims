#!/usr/bin/env python3
"""
Script to populate session_name for existing sessions.
Extracts session name from the first query event, respecting word boundaries.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path to import collab_sims
sys.path.insert(0, str(Path(__file__).parent.parent))

from collab_sims.core.utils import truncate_session_name


async def populate_session_names():
    """Populate session_name for sessions that don't have one."""

    db_path = Path(__file__).parent.parent / "data" / "api_sessions.db"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get sessions without session_name
    cursor.execute("""
        SELECT session_id
        FROM session
        WHERE session_name IS NULL OR session_name = ''
    """)

    sessions_without_name = cursor.fetchall()

    if not sessions_without_name:
        print("✅ All sessions already have names")
        conn.close()
        return

    print(f"📝 Found {len(sessions_without_name)} session(s) without names")

    updated_count = 0

    for (session_id,) in sessions_without_name:
        # Get first query event for this session
        cursor.execute(
            """
            SELECT data
            FROM event
            WHERE session_id = ? AND event_type = 'query'
            ORDER BY timestamp ASC
            LIMIT 1
        """,
            (session_id,),
        )

        result = cursor.fetchone()

        if result:
            event_data = json.loads(result[0])
            prompt = event_data.get("prompt", "")

            if prompt:
                # Extract session name respecting word boundaries
                session_name = truncate_session_name(prompt)

                # Update session
                cursor.execute(
                    """
                    UPDATE session
                    SET session_name = ?
                    WHERE session_id = ?
                """,
                    (session_name, session_id),
                )

                print(f'   ✓ Updated {session_id[:8]}... → "{session_name}"')
                updated_count += 1
            else:
                print(f"   ⚠ No prompt found for {session_id[:8]}...")
        else:
            print(f"   ⚠ No query events found for {session_id[:8]}...")

    conn.commit()
    conn.close()

    print(f"\n✅ Updated {updated_count} session name(s)")


if __name__ == "__main__":
    asyncio.run(populate_session_names())
