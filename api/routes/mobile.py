"""Mobile run API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import api.deps as api_deps
from api.deps import require_maintainer
from mobile_appium import MobileRunService

router = APIRouter()


class MobileRunRequest(BaseModel):
    start_screen: str = Field("LoginScreen", description="Starting screen name for the bounded mobile exploration run")
    username: str = Field("", description="Username used for the exploration run")
    password: str = Field("", description="Password used for the exploration run")
    max_steps: Optional[int] = Field(None, ge=1, description="Optional maximum number of exploration steps")
    output_path: Optional[str] = Field(
        None,
        description="Optional artifact output path. Must resolve under artifacts/ inside the repository.",
    )


class MobileRunResponse(BaseModel):
    run_id: str
    passed: bool
    stop_reason: str
    visited_screens: list[str]
    executed_actions: list[str]
    coverage_score: float
    policy_shape: str
    started_at: str
    finished_at: str
    duration_ms: int
    error: str


def _resolve_safe_output_path(raw_output_path: str | None) -> Path | None:
    if raw_output_path is None or not str(raw_output_path).strip():
        return None

    repo_root = Path(api_deps.REPO_ROOT).resolve()
    artifacts_root = (repo_root / "artifacts").resolve()
    candidate = Path(str(raw_output_path).strip())
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()

    try:
        resolved.relative_to(artifacts_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="output_path must resolve under artifacts/ inside the repository",
        ) from exc

    return resolved


def get_mobile_run_service() -> MobileRunService:
    return MobileRunService()


@router.post("/runs/exploration", response_model=MobileRunResponse)
async def trigger_mobile_exploration_run(
    request: MobileRunRequest,
    service: MobileRunService = Depends(get_mobile_run_service),
    user=Depends(require_maintainer),
):
    """Trigger a bounded mobile exploration run using the internal mobile run service."""
    artifact = service.run_bounded_exploration(
        start_screen=request.start_screen,
        username=request.username,
        password=request.password,
        max_steps=request.max_steps,
        output_path=_resolve_safe_output_path(request.output_path),
    )
    return MobileRunResponse(**artifact.to_dict())

