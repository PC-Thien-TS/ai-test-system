"""Run API endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import get_project_service, get_user_context, require_maintainer
from api.websocket_manager import manager
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


class RunUpdate(BaseModel):
    """Real-time run update."""
    run_id: str
    status: str
    confidence_score: float
    fallback_ratio: float
    real_execution_ratio: float
    timestamp: str


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get a specific run by ID.
    
    Args:
        run_id: The run ID.
        
    Returns:
        The run details.
    """
    run = service.get_run(run_id)
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    project = service.get_project(run.project_id)
    
    # Check workspace access
    if project and project.workspace_id and project.workspace_id != user.workspace_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this run"
        )
    
    return {
        "run_id": run.run_id,
        "project_id": run.project_id,
        "status": run.status.value,
        "started_at": run.started_at.isoformat(),
        "output_path": str(run.output_path),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "gate_result": run.gate_result.value if run.gate_result else None,
        "flaky": run.flaky,
        "metadata": run.metadata,
        "execution_path": run.execution_path.value,
        "parent_run_id": run.parent_run_id,
        "confidence_score": run.confidence_score,
        "fallback_ratio": run.fallback_ratio,
        "real_execution_ratio": run.real_execution_ratio,
    }


@router.post("/{run_id}/escalate")
async def trigger_escalation_rerun(
    run_id: str,
    reason: str,
    service = Depends(get_project_service),
    user = Depends(require_maintainer),
):
    """
    Trigger an escalation rerun for a completed run.
    
    Args:
        run_id: The parent run ID to escalate from.
        reason: Reason for escalation.
        
    Returns:
        The new escalated run details.
    """
    parent_run = service.get_run(run_id)
    
    if not parent_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    project = service.get_project(parent_run.project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {parent_run.project_id} not found"
        )
    
    # Check workspace access
    if project.workspace_id and project.workspace_id != user.workspace_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    # Determine next escalation path
    from orchestrator.models import ExecutionPath
    current_path = parent_run.execution_path
    
    if current_path == ExecutionPath.SMOKE:
        new_path = ExecutionPath.STANDARD
    elif current_path == ExecutionPath.STANDARD:
        new_path = ExecutionPath.DEEP
    elif current_path == ExecutionPath.DEEP:
        new_path = ExecutionPath.INTELLIGENT
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot escalate from INTELLIGENT path"
        )
    
    # Trigger escalation rerun
    new_run = service.trigger_escalation_run(
        parent_run_id=run_id,
        new_path=new_path,
        reason=reason,
    )
    
    if not new_run:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create escalation rerun"
        )
    
    return {
        "run_id": new_run.run_id,
        "project_id": new_run.project_id,
        "status": new_run.status.value,
        "execution_path": new_run.execution_path.value,
        "parent_run_id": new_run.parent_run_id,
        "started_at": new_run.started_at.isoformat(),
    }


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


@router.get("/{run_id}/updates")
async def run_updates_stream(
    run_id: str,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Stream real-time updates for a run using Server-Sent Events (SSE).

    Args:
        run_id: The run ID to stream updates for.

    Returns:
        Streaming response with SSE events.
    """
    run = service.get_run(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    project = service.get_project(run.project_id)

    # Check workspace access
    if project and project.workspace_id and project.workspace_id != user.workspace_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this run"
        )

    async def event_generator():
        """Generate SSE events for run updates."""
        try:
            # Send initial state
            yield f"data: {json.dumps(RunUpdate(
                run_id=run.run_id,
                status=run.status.value,
                confidence_score=run.confidence_score,
                fallback_ratio=run.fallback_ratio,
                real_execution_ratio=run.real_execution_ratio,
                timestamp=run.started_at.isoformat(),
            ).model_dump())}\n\n"

            # Poll for updates (in production, use WebSocket or message queue)
            for i in range(10):  # Limit to 10 updates for demo
                await asyncio.sleep(2)

                # Refresh run state
                updated_run = service.get_run(run_id)
                if updated_run:
                    yield f"data: {json.dumps(RunUpdate(
                        run_id=updated_run.run_id,
                        status=updated_run.status.value,
                        confidence_score=updated_run.confidence_score,
                        fallback_ratio=updated_run.fallback_ratio,
                        real_execution_ratio=updated_run.real_execution_ratio,
                        timestamp=datetime.utcnow().isoformat(),
                    ).model_dump())}\n\n"

                    # Stop if run is completed
                    if updated_run.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                        break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/{run_id}/ws")
async def websocket_run_updates(
    websocket: WebSocket,
    run_id: str,
):
    """
    WebSocket endpoint for real-time run intelligence updates.

    Args:
        websocket: The WebSocket connection.
        run_id: The run ID to subscribe to updates for.
    """
    await websocket.accept()
    client_id = f"client_{id(websocket)}"
    
    try:
        await manager.connect(websocket, client_id)
        await manager.subscribe_to_run(websocket, run_id)
        
        # Send initial state
        from orchestrator.project_service import ProjectService
        from pathlib import Path
        service = ProjectService(Path("data/projects"))
        
        run = service.get_run(run_id)
        if run:
            await manager.send_run_update(
                run_id=run_id,
                status=run.status.value,
                confidence_score=run.confidence_score,
                fallback_ratio=run.fallback_ratio,
                execution_path=run.execution_path.value,
                escalation_state={
                    "parent_run_id": run.parent_run_id,
                    "depth": run.metadata.get("escalation_depth", 0) if run.metadata else 0,
                },
            )
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive ping/pong or control messages
                data = await websocket.receive_text()
                
                # Echo back for keep-alive
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"WebSocket error for run {run_id}: {e}")
    finally:
        manager.disconnect(websocket, client_id)
        await manager.unsubscribe_from_run(websocket, run_id)
