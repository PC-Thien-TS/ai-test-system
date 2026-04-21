"""Platform API endpoints."""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_project_service, get_user_context
from orchestrator.models import GateResult


class PlatformSummaryResponse(BaseModel):
    """Response model for platform summary."""
    total_projects: int
    active_projects: int
    total_runs: int
    failing_projects: int
    flaky_projects: int
    gate_overview: Dict[str, int]
    plugin_usage: Dict[str, int]
    generated_at: str


class ProjectStatusResponse(BaseModel):
    """Response model for project status."""
    project_id: str
    project_name: str
    product_type: str
    latest_run_id: Optional[str]
    latest_status: Optional[str]
    gate_result: Optional[str]
    last_updated: Optional[str]


router = APIRouter()


@router.get("/summary", response_model=PlatformSummaryResponse)
async def get_platform_summary(
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get platform-wide summary.
    
    Returns:
        Platform summary with aggregate statistics.
    """
    summary = service.get_platform_summary()
    
    return PlatformSummaryResponse(
        total_projects=summary.total_projects,
        active_projects=summary.active_projects,
        total_runs=summary.total_runs,
        failing_projects=summary.failing_projects,
        flaky_projects=summary.flaky_projects,
        gate_overview={k.value: v for k, v in summary.gate_overview.items()},
        plugin_usage=summary.plugin_usage,
        generated_at=summary.generated_at.isoformat(),
    )


@router.get("/projects/latest", response_model=List[ProjectStatusResponse])
async def get_latest_project_status(
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get latest status for all projects.
    
    Returns:
        List of project status entries.
    """
    status_list = service.get_latest_project_status()
    
    # Filter by workspace if user has one
    if user.workspace_id:
        projects = service.list_projects(workspace_id=user.workspace_id)
        project_ids = {p.project_id for p in projects}
        status_list = [s for s in status_list if s["project_id"] in project_ids]
    
    return [
        ProjectStatusResponse(
            project_id=s["project_id"],
            project_name=s["project_name"],
            product_type=s["product_type"],
            latest_run_id=s["latest_run_id"],
            latest_status=s["latest_status"],
            gate_result=s["gate_result"],
            last_updated=s["last_updated"],
        )
        for s in status_list
    ]
