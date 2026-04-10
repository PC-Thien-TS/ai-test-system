"""Run API endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_project_service, get_user_context
from orchestrator.models import RunStatus

router = APIRouter()


# Request/Response Models
class RunResponse(BaseModel):
    """Response model for a run."""
    run_id: str
    project_id: str
    status: str
    started_at: str
    output_path: str
    completed_at: Optional[str]
    gate_result: Optional[str]
    flaky: bool


class ProjectSummaryResponse(BaseModel):
    """Response model for project summary."""
    project_id: str
    project_name: str
    product_type: str
    latest_run_id: Optional[str]
    latest_status: Optional[str]
    gate_result: Optional[str]
    total_runs: int
    passed_runs: int
    failed_runs: int
    flaky_runs: int
    last_updated: Optional[str]


class TrendDataPoint(BaseModel):
    """Response model for a trend data point."""
    run_id: str
    timestamp: str
    status: str
    gate_result: Optional[str]
    flaky: bool
    duration: Optional[float]


@router.get("/{project_id}/runs", response_model=List[RunResponse])
async def list_project_runs(
    project_id: str,
    limit: int = 50,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    List runs for a project.
    
    Args:
        project_id: The project ID.
        limit: Maximum number of runs to return.
        
    Returns:
        List of runs.
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
    
    runs = service.get_project_runs(project_id, limit=limit)
    
    return [
        RunResponse(
            run_id=r.run_id,
            project_id=r.project_id,
            status=r.status.value,
            started_at=r.started_at.isoformat(),
            output_path=str(r.output_path),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            gate_result=r.gate_result.value if r.gate_result else None,
            flaky=r.flaky,
        )
        for r in runs
    ]


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(
    project_id: str,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get summary for a project.
    
    Args:
        project_id: The project ID.
        
    Returns:
        Project summary.
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
    
    summary = service.get_project_summary(project_id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary for project {project_id} not found"
        )
    
    return ProjectSummaryResponse(
        project_id=summary.project_id,
        project_name=summary.project_name,
        product_type=summary.product_type.value,
        latest_run_id=summary.latest_run_id,
        latest_status=summary.latest_status.value if summary.latest_status else None,
        gate_result=summary.gate_result.value if summary.gate_result else None,
        total_runs=summary.total_runs,
        passed_runs=summary.passed_runs,
        failed_runs=summary.failed_runs,
        flaky_runs=summary.flaky_runs,
        last_updated=summary.last_updated.isoformat() if summary.last_updated else None,
    )


@router.get("/{project_id}/trends", response_model=List[TrendDataPoint])
async def get_project_trends(
    project_id: str,
    limit: int = 50,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get trend data for a project.
    
    Args:
        project_id: The project ID.
        limit: Maximum number of data points to return.
        
    Returns:
        List of trend data points.
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
    
    trends = service.get_project_trends(project_id, limit=limit)
    
    return [
        TrendDataPoint(
            run_id=t["run_id"],
            timestamp=t["timestamp"],
            status=t["status"],
            gate_result=t.get("gate_result"),
            flaky=t["flaky"],
            duration=t.get("duration"),
        )
        for t in trends
    ]
