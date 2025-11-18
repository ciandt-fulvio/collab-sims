"""Custom tracker for streaming events to API clients"""

import asyncio
from typing import List, Dict, Any
from .base import BaseTracker
from ..core.events import AgentEvent


class StreamTracker(BaseTracker):
    """
    Tracker that collects events for API responses.

    Can be used for:
    - Single-turn execution (collect all events, return when done)
    - Multi-turn sessions (collect events per query)
    - Server-Sent Events streaming (real-time event push)
    """

    def __init__(self):
        super().__init__()
        self.events: List[Dict[str, Any]] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._is_streaming = False

    async def on_event(self, event: AgentEvent):
        """Called for every event - store in list and queue for SSE"""
        event_dict = event.to_dict()
        self.events.append(event_dict)

        if self._is_streaming:
            await self._event_queue.put(event_dict)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all collected events"""
        return self.events

    def clear_events(self):
        """Clear event history (useful for multi-turn sessions)"""
        self.events = []

    async def stream_events(self):
        """
        Async generator for SSE streaming.
        Yields events as they arrive in real-time.
        """
        self._is_streaming = True
        try:
            while True:
                event = await self._event_queue.get()
                yield event

                # Check if this is a completion event
                if event.get('event_type') in ['complete', 'error', 'session_end']:
                    break
        finally:
            self._is_streaming = False
