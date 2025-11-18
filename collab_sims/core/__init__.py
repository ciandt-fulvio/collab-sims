"""Core functionality for agent event handling and execution.

This module provides event types, classes for tracking agent execution,
sessions, tools, messages, and other events throughout the agent lifecycle,
as well as the main API for executing agents with real Claude SDK integration.
"""

from .events import (
    # Base classes
    AgentEvent,
    EventType,
    # Session events
    SessionStartEvent,
    SessionEndEvent,
    QueryEvent,
    # Execution events
    StartEvent,
    CompleteEvent,
    # Agent events
    PlanEvent,
    MessageEvent,
    PartialMessageEvent,
    ToolUseEvent,
    ToolResultEvent,
    ProgressEvent,
    SystemEvent,
    ErrorEvent,
    # Approval events
    ApprovalRequestEvent,
    ApprovalResponseEvent,
    # Metrics events
    MetricsEvent,
    # Supporting classes
    TaskInfo,
    PlanChanges,
)

# Agent execution classes
from .agent import CollabSims
from .session import CollabSimsSession

# Configuration
from .config import (
    SessionConfig,
    get_collab_sims_config_dir,
    get_default_working_dir,
)

# Prompts
from .prompts import (
    get_session_prompt,
    load_template,
    list_available_prompts,
)

# Approval handling
from .approval_callback import ApprovalCallback

__all__ = [
    # Base classes
    "AgentEvent",
    "EventType",
    # Session events
    "SessionStartEvent",
    "SessionEndEvent",
    "QueryEvent",
    # Execution events
    "StartEvent",
    "CompleteEvent",
    # Agent events
    "PlanEvent",
    "MessageEvent",
    "PartialMessageEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "ProgressEvent",
    "SystemEvent",
    "ErrorEvent",
    # Approval events
    "ApprovalRequestEvent",
    "ApprovalResponseEvent",
    # Metrics events
    "MetricsEvent",
    # Supporting classes
    "TaskInfo",
    "PlanChanges",
    # Agent execution
    "CollabSims",
    "CollabSimsSession",
    # Configuration
    "SessionConfig",
    "get_collab_sims_config_dir",
    "get_default_working_dir",
    # Prompts
    "get_session_prompt",
    "load_template",
    "list_available_prompts",
    # Approval
    "ApprovalCallback",
]
