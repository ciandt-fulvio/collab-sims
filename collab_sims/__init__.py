"""Collab-Sims - Collaborative AI Simulations Package

This package provides persistence and tracking utilities for AI agent sessions.
"""

__version__ = "0.1.0"

# Make commonly used classes available at package level
from .persistence import SessionRepository, SQLiteRepository
from .trackers import (
    BaseTracker,
    ConsoleTracker,
    JSONTracker,
    StreamTracker,
    DatabaseTracker,
)

__all__ = [
    "SessionRepository",
    "SQLiteRepository",
    "BaseTracker",
    "ConsoleTracker",
    "JSONTracker",
    "StreamTracker",
    "DatabaseTracker",
]
