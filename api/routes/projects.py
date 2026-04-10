"""Project API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import get_project_service, get_user_context, require_maintainer
from orchestrator.models import ProductType

router = APIRouter()


# Request/Response Models
class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""
    name: str = Field(..., description="Project name")
    product_type: ProductType = Field(..., description="Product type being tested")
    manifest_path: str = Field(..., description="Path to project manifest")
    description: Optional[str] = Field(None, description="Optional project description")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional project tags")
    workspace_id: Optional[str] = Field(None, description="Optional workspace ID")


class ProjectResponse(BaseModel):
    """Response model for a project."""
    project_id: str
    name: str
    product_type: str
    manifest_path: str
    description: Optional[str]
    tags: List[str]
    workspace_id: Optional[str]
    owner_id: Optional[str]
    created_at: str
    updated_at: str
    active: bool


class RunTriggerResponse(BaseModel):
    """Response model for triggering a run."""
    run_id: str
    project_id: str
    status: str
    output_path: str
    started_at: str
    execution_path: str


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    workspace_id: Optional[str] = None,
    active_only: bool = True,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    List projects.
    
    Args:
        workspace_id: Optional workspace ID to filter by.
        active_only: If True, only return active projects.
        
    Returns:
        List of projects.
    """
    # Apply workspace filter from user context if not explicitly provided
    if workspace_id is None and user.workspace_id:
        workspace_id = user.workspace_id
    
    projects = service.list_projects(workspace_id=workspace_id, active_only=active_only)
    
    return [
        ProjectResponse(
            project_id=p.project_id,
            name=p.name,
            product_type=p.product_type.value,
            manifest_path=str(p.manifest_path),
            description=p.description,
            tags=p.tags,
            workspace_id=p.workspace_id,
            owner_id=p.owner_id,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            active=p.active,
        )
        for p in projects
    ]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    service = Depends(get_project_service),
    user = Depends(require_maintainer),
):
    """
    Create a new project.
    
    Args:
        request: Project creation request.
        
    Returns:
        Created project.
    """
    project = service.create_project(
        name=request.name,
        product_type=request.product_type,
        manifest_path=Path(request.manifest_path),
        description=request.description,
        tags=request.tags,
        workspace_id=request.workspace_id or user.workspace_id,
        owner_id=user.user_id,
    )
    
    return ProjectResponse(
        project_id=project.project_id,
        name=project.name,
        product_type=project.product_type.value,
        manifest_path=str(project.manifest_path),
        description=project.description,
        tags=project.tags,
        workspace_id=project.workspace_id,
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        active=project.active,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get a project by ID.
    
    Args:
        project_id: The project ID.
        
    Returns:
        Project details.
    """
    project = service.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Check workspace access
    if project.workspace_id and project.workspace_id != user.workspace_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    return ProjectResponse(
        project_id=project.project_id,
        name=project.name,
        product_type=project.product_type.value,
        manifest_path=str(project.manifest_path),
        description=project.description,
        tags=project.tags,
        workspace_id=project.workspace_id,
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        active=project.active,
    )


@router.post("/{project_id}/run", response_model=RunTriggerResponse)
async def trigger_run(
    project_id: str,
    execution_path: Optional[str] = None,
    service = Depends(get_project_service),
    user = Depends(require_maintainer),
):
    """
    Trigger a test run for a project.
    
    Args:
        project_id: The project ID.
        execution_path: Optional forced execution path (smoke, standard, deep, intelligent).
        
    Returns:
        Created run metadata.
    """
    project = service.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Check workspace access
    if project.workspace_id and project.workspace_id != user.workspace_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    # Convert execution_path string to enum if provided
    from orchestrator.models import ExecutionPath
    forced_path = ExecutionPath(execution_path) if execution_path else None
    
    run = service.trigger_run(project_id, forced_path=forced_path)
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create run"
        )
    
    return RunTriggerResponse(
        run_id=run.run_id,
        project_id=run.project_id,
        status=run.status.value,
        output_path=str(run.output_path),
        started_at=run.started_at.isoformat(),
        execution_path=run.execution_path.value,
    )
