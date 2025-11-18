"""Console tracker for debugging."""

from typing import Optional
from .base import BaseTracker
from ..core.events import (
    AgentEvent,
    EventType,
    PlanEvent,
    MessageEvent,
    ToolUseEvent,
    ProgressEvent,
    ErrorEvent,
    StartEvent,
    CompleteEvent,
)


class ConsoleTracker(BaseTracker):
    """Tracker that outputs events to console for debugging."""

    def __init__(self, verbose: bool = True, pretty: bool = True):
        """Initialize console tracker.

        Args:
            verbose: If True, show all events. If False, show only important ones.
            pretty: If True, use colored/formatted output.
        """
        self.verbose = verbose
        self.pretty = pretty

    async def on_start(self, event: StartEvent) -> None:
        """Handle start event."""
        if self.pretty:
            print("🚀 " + "=" * 68)
            print(f"   AGENT EXECUTION STARTED")
            print("   " + "=" * 68)
            print(f"   Prompt: {event.prompt[:80]}{'...' if len(event.prompt) > 80 else ''}")
            print("=" * 70)
        else:
            print(f"[START] {event.prompt}")

    async def on_complete(self, event: CompleteEvent) -> None:
        """Handle complete event."""
        if self.pretty:
            print("\n" + "=" * 70)
            print("✅ EXECUTION COMPLETE")
            print("=" * 70)
            print(f"   Duration: {event.duration_ms}ms")
            print(f"   Turns: {event.num_turns}")
            if event.total_cost_usd:
                print(f"   Cost: ${event.total_cost_usd:.4f}")
            if event.result:
                print(f"   Result: {event.result}")
            print("=" * 70)
        else:
            print(f"[COMPLETE] {event.duration_ms}ms, {event.num_turns} turns")

    async def on_event(self, event: AgentEvent) -> None:
        """Handle any event."""
        if event.type == EventType.PLAN:
            await self._handle_plan(event)
        elif event.type == EventType.MESSAGE:
            await self._handle_message(event)
        elif event.type == EventType.TOOL_USE:
            await self._handle_tool_use(event)
        elif event.type == EventType.PROGRESS:
            await self._handle_progress(event)
        elif event.type == EventType.ERROR:
            await self._handle_error(event)
        elif self.verbose:
            # For other events, print if verbose
            print(f"[{event.type.value.upper()}] {event.to_dict()}")

    async def _handle_plan(self, event: PlanEvent) -> None:
        """Handle plan event."""
        if self.pretty:
            print(f"\n📋 PLAN UPDATE")
            print("=" * 70)

            for i, task in enumerate(event.todos, 1):
                status_icon = {
                    "completed": "✅",
                    "in_progress": "🔧",
                    "pending": "⏳"
                }.get(task.status, "❓")

                display = task.active_form if task.status == "in_progress" else task.content
                print(f"{i}. {status_icon} {display}")

            if event.changes:
                if event.changes.added:
                    print(f"\n  ➕ Added: {', '.join(event.changes.added)}")
                if event.changes.removed:
                    print(f"  ➖ Removed: {', '.join(event.changes.removed)}")

            print("=" * 70)
        else:
            print(f"[PLAN] {event.completed}/{event.total_tasks} tasks")

    async def _handle_message(self, event: MessageEvent) -> None:
        """Handle message event."""
        if event.role == "assistant" and event.content:
            if self.pretty:
                print(f"\n💬 {event.content}")
            else:
                print(f"[MESSAGE] {event.content}")

    async def _handle_tool_use(self, event: ToolUseEvent) -> None:
        """Handle tool use event."""
        if self.verbose:
            if self.pretty:
                print(f"\n🔧 Tool: {event.tool_name}")
                if event.input:
                    # Show first few items of input
                    input_preview = str(event.input)[:100]
                    print(f"   Input: {input_preview}{'...' if len(str(event.input)) > 100 else ''}")
            else:
                print(f"[TOOL] {event.tool_name}")

    async def _handle_progress(self, event: ProgressEvent) -> None:
        """Handle progress event."""
        if self.pretty:
            bar_length = 40
            filled = int(bar_length * event.percentage / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\n📊 Progress: [{bar}] {event.percentage:.1f}% ({event.completed}/{event.total})")
            if event.current_task:
                print(f"   Current: {event.current_task}")
        else:
            print(f"[PROGRESS] {event.percentage:.1f}%")

    async def _handle_error(self, event: ErrorEvent) -> None:
        """Handle error event."""
        if self.pretty:
            print(f"\n❌ ERROR: {event.error}")
            if event.error_type:
                print(f"   Type: {event.error_type}")
            if event.traceback and self.verbose:
                print(f"   Traceback: {event.traceback}")
        else:
            print(f"[ERROR] {event.error}")

    async def on_error(self, event: ErrorEvent) -> None:
        """Handle error event (called separately)."""
        await self._handle_error(event)
