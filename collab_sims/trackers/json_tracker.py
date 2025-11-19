"""JSON file tracker for event logging."""

import json
from pathlib import Path

from ..core.events import AgentEvent
from .base import BaseTracker


class JSONTracker(BaseTracker):
    """Tracker that saves events to a JSON file."""

    def __init__(self, output_file: str = "agent_session.json", indent: int = 2):
        """Initialize JSON tracker.

        Args:
            output_file: Path to output JSON file
            indent: JSON indentation (default 2 for readability)
        """
        self.output_file = Path(output_file)
        self.indent = indent
        self.events: list[dict] = []

    async def on_event(self, event: AgentEvent) -> None:
        """Store event in memory."""
        self.events.append(event.to_dict())

    async def teardown(self) -> None:
        """Write all events to file on teardown."""
        with open(self.output_file, "w") as f:
            json.dump({
                "events": self.events,
                "total_events": len(self.events)
            }, f, indent=self.indent)

        print(f"💾 Saved {len(self.events)} events to: {self.output_file}")
