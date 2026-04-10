"""Dependency injection for FastAPI routes."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.project_service import ProjectService


@dataclass
class UserContext:
    """User context for multi-tenant support."""
    user_id: str
    workspace_id: Optional[str] = None
    role: str = "viewer"  # viewer, maintainer, admin


def get_project_service() -> ProjectService:
    """Dependency injection for project service."""
    return ProjectService(REPO_ROOT)


def get_user_context(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    x_user_role: Optional[str] = Header("viewer", alias="X-User-Role"),
) -> UserContext:
    """
    Get user context from headers.
    
    In a real system, this would validate JWT tokens.
    For now, we use simple header-based simulation for testing.
    """
    if not x_user_id:
        # Default to a test user for development
        x_user_id = "test-user"
    
    return UserContext(
        user_id=x_user_id,
        workspace_id=x_workspace_id,
        role=x_user_role or "viewer",
    )


def require_admin(user: UserContext = Depends(get_user_context)) -> UserContext:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user


def require_maintainer(user: UserContext = Depends(get_user_context)) -> UserContext:
    """Require maintainer or admin role."""
    if user.role not in ("admin", "maintainer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maintainer or admin role required"
        )
    return user
