"""FastAPI application for Universal Testing Platform v2.1."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, mobile, platform, plugins, projects, runs, storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the app."""
    # Startup
    print("Starting Universal Testing Platform API v2.1...")
    yield
    # Shutdown
    print("Shutting down Universal Testing Platform API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Universal Testing Platform API",
        description="Platform API for managing testing projects, runs, and quality gates",
        version="3.0.0",
        lifespan=lifespan,
    )
    
    # Add CORS middleware for dashboard integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(projects.router, prefix="/projects", tags=["projects"])
    # Keep legacy /projects run routes while exposing canonical /runs endpoints.
    app.include_router(runs.router, prefix="/projects", tags=["runs"])
    app.include_router(runs.router, prefix="/runs", tags=["runs"])
    app.include_router(storage.router, prefix="/storage", tags=["storage"])
    app.include_router(platform.router, prefix="/platform", tags=["platform"])
    app.include_router(plugins.router, prefix="/plugins", tags=["plugins"])
    app.include_router(mobile.router, prefix="/mobile", tags=["mobile"])
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
