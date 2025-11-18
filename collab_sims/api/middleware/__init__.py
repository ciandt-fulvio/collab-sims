"""Middleware for FastAPI app"""

from .cors import setup_cors

__all__ = ["setup_cors"]
