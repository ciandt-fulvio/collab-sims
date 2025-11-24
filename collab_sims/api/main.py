"""
CollabSims API - FastAPI application (No CollabSims SDK required).

Unified API providing:
- Multi-turn session management (/sessions)
- Single-turn execution (/execute)
- Tool approval workflow (/approvals)

All functionality is simulated - perfect for frontend development without backend dependencies.
"""

import logging

from fastapi import FastAPI

from .middleware import setup_cors
from .routes import (
    approvals_router,
    execute_router,
    sessions_router,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress verbose logs from Claude Agent SDK internals
# These logs include internal errors that don't affect functionality
logging.getLogger('claude_agent_sdk._internal').setLevel(logging.WARNING)
logging.getLogger('claude_agent_sdk').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CollabSims API",
    description="Unified API for CollabSims: multi-turn sessions with tool approval workflow (Simulated - No SDK required)",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup CORS for local development
setup_cors(app)

# Register routes
app.include_router(execute_router)           # Single-turn execution
app.include_router(sessions_router)          # Multi-turn sessions
app.include_router(approvals_router)         # Approval workflow


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "CollabSims API",
        "version": "0.2.0",
        "status": "running",
        "note": "Simulated version - no CollabSims SDK required",
        "docs": "/docs",
        "endpoints": {
            "execute_buffered": "POST /api/execute - Single-turn execution (buffered)",
            "execute_stream": "POST /api/execute/stream - Single-turn execution (SSE streaming)",
            "sessions_create": "POST /api/sessions - Create session",
            "sessions_query": "POST /api/sessions/{id}/query/stream - Query session (SSE streaming)",
            "approvals_pending": "GET /api/sessions/{id}/approvals/pending - Get pending approvals",
            "approvals_respond": "POST /api/sessions/{id}/approvals/{tool_id}/respond - Approve/reject tool",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "collab-sims-api"}


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    import asyncio

    logger.info("🚀 CollabSims API starting...")

    # Initialize database
    from .services.session_manager import session_manager
    await session_manager.db_tracker.repository.initialize()
    logger.info("   Database initialized")

    # Start session restore in background (non-blocking)
    # This allows the server to accept requests immediately
    asyncio.create_task(session_manager.restore_sessions_from_database())
    logger.info("   Session restore started in background")

    logger.info("   Available routes:")
    logger.info("     - /api/sessions/* (multi-turn conversations)")
    logger.info("     - /api/execute/* (single-turn execution)")
    logger.info("     - /api/approvals/* (tool approval workflow)")
    logger.info("     - /health (health check)")
    logger.info("")
    logger.info("✅ API ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("🛑 CollabSims API shutting down...")

    # Shutdown session manager (cancels cleanup task, closes database)
    from .services.session_manager import session_manager
    await session_manager.shutdown()
    logger.info("   Shutdown complete")
