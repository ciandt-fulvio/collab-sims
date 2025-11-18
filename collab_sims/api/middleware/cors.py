"""CORS configuration for local development and production"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI, allow_origins: list[str] = None):
    """
    Configure CORS middleware for the application.

    Args:
        app: FastAPI application instance
        allow_origins: List of allowed origins. Defaults to localhost for development.
    """
    if allow_origins is None:
        # Default: Allow local development
        allow_origins = [
            "http://localhost:5173",  # Vite default
            "http://localhost:3000",  # Common React dev server
            "http://localhost:3005",  # Sims web frontend
            "http://localhost:8080",  # Python HTTP server
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3005",
            "http://127.0.0.1:8080",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )
