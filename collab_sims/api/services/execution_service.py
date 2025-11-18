"""Service for single-turn execution"""

import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime

# Import only from collab_sims (no CollabSims dependencies)
from ...trackers import StreamTracker


class ExecutionService:
    """
    Handles single-turn agent execution (simulated).
    Provides API for executing single prompts without maintaining session state.
    """

    @staticmethod
    async def execute(
        prompt: str, config: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Dict[str, Any]], str, Optional[str]]:
        """
        Execute a single-turn prompt and return all events (buffered).

        Args:
            prompt: User prompt to send to agent
            config: Optional session configuration

        Returns:
            Tuple of (events, status, error_message)
        """
        try:
            # Simulate agent response
            events = await ExecutionService._simulate_execution(prompt)
            return events, "completed", None

        except Exception as e:
            # Return error
            return [], "error", str(e)

    @staticmethod
    async def execute_stream(
        prompt: str, config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute with real-time event streaming (for SSE).

        Args:
            prompt: User prompt
            config: Optional session configuration

        Yields:
            Events as they occur in real-time
        """
        try:
            # Stream simulated events
            async for event in ExecutionService._simulate_execution_stream(prompt):
                yield event

        except Exception as e:
            # Yield error event
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @staticmethod
    async def _simulate_execution(prompt: str) -> List[Dict[str, Any]]:
        """Simulate a single-turn execution (buffered)"""
        events = []

        # Event: Query started
        query_event = {
            "type": "query",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "query_number": 1,
        }
        events.append(query_event)

        # Event: Complete message
        message_text = f"Resposta para: '{prompt}'. Esta é uma execução única simulada."
        message_event = {
            "type": "message",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": message_text,
        }
        events.append(message_event)

        # Event: Complete
        complete_event = {
            "type": "complete",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "input_tokens": 30,
                "output_tokens": 20,
                "total_cost_usd": 0.0005,
            },
            "duration_ms": 300,
            "num_turns": 1,
        }
        events.append(complete_event)

        return events

    @staticmethod
    async def _simulate_execution_stream(prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Simulate streaming execution with partial messages"""
        import asyncio

        # Event: Query started
        query_event = {
            "type": "query",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "query_number": 1,
        }
        yield query_event
        await asyncio.sleep(0.1)

        # Event: Partial messages (word by word)
        message_text = f"Resposta para: '{prompt}'. Esta é uma execução única simulada."
        words = message_text.split()
        for i, word in enumerate(words):
            partial = {
                "type": "partial_message",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "delta": word + " ",
                "index": i,
            }
            yield partial
            await asyncio.sleep(0.05)

        # Event: Complete message
        message_event = {
            "type": "message",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": message_text,
        }
        yield message_event
        await asyncio.sleep(0.1)

        # Event: Complete
        complete_event = {
            "type": "complete",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "input_tokens": 30,
                "output_tokens": 20,
                "total_cost_usd": 0.0005,
            },
            "duration_ms": 300,
            "num_turns": 1,
        }
        yield complete_event
