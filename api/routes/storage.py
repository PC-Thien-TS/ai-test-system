from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import (
    get_storage_artifact_service,
    get_storage_memory_service,
    get_storage_run_service,
    get_user_context,
    require_maintainer,
)
from orchestrator.storage.application.services import ArtifactService, MemoryService, RunService
from orchestrator.storage.domain.models import FailureSignature


router = APIRouter()


class CreateRunRequest(BaseModel):
    adapter_id: str
    project_id: str
    status: str = "pending"
    metadata: dict = Field(default_factory=dict)


class UpdateRunStatusRequest(BaseModel):
    status: str
    summary: Optional[dict] = None
    metadata: dict = Field(default_factory=dict)


class AttachReleaseRequest(BaseModel):
    release_decision_ref: str


class StoreTextArtifactRequest(BaseModel):
    adapter_id: str
    artifact_name: str
    content: str
    content_type: str = "text/plain; charset=utf-8"
    metadata: dict = Field(default_factory=dict)


class RememberFailureRequest(BaseModel):
    adapter_id: str
    project_id: Optional[str] = None
    root_cause: str
    severity: str
    confidence: float
    flaky: bool = False
    recommended_actions: list[str] = Field(default_factory=list)
    action_note: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    semantic_text: Optional[str] = None
    signature: dict


class ExactLookupRequest(BaseModel):
    adapter_id: str
    signature: dict


class SimilarLookupRequest(BaseModel):
    adapter_id: str
    query_text: str
    top_k: int = 5
    min_score: float = 0.1


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    service: RunService = Depends(get_storage_run_service),
    _user=Depends(require_maintainer),
):
    run = service.create_run(
        adapter_id=payload.adapter_id,
        project_id=payload.project_id,
        status=payload.status,
        metadata=payload.metadata,
    )
    return run.to_dict()


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    adapter_id: Optional[str] = None,
    service: RunService = Depends(get_storage_run_service),
    _user=Depends(get_user_context),
):
    run = service.get_run(run_id, adapter_id=adapter_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.get("/runs")
async def list_runs(
    adapter_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    service: RunService = Depends(get_storage_run_service),
    _user=Depends(get_user_context),
):
    rows = service.list_runs(adapter_id=adapter_id, project_id=project_id, status=status_filter, limit=limit)
    return {"items": [row.to_dict() for row in rows], "count": len(rows)}


@router.patch("/runs/{run_id}/status")
async def update_run_status(
    run_id: str,
    payload: UpdateRunStatusRequest,
    service: RunService = Depends(get_storage_run_service),
    _user=Depends(require_maintainer),
):
    run = service.mark_run_status(
        run_id=run_id,
        status=payload.status,
        summary=payload.summary,
        metadata=payload.metadata,
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.post("/runs/{run_id}/release-decision")
async def attach_release_decision(
    run_id: str,
    payload: AttachReleaseRequest,
    service: RunService = Depends(get_storage_run_service),
    _user=Depends(require_maintainer),
):
    run = service.attach_release_decision(run_id=run_id, release_decision_ref=payload.release_decision_ref)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.post("/runs/{run_id}/artifacts/text", status_code=status.HTTP_201_CREATED)
async def store_text_artifact(
    run_id: str,
    payload: StoreTextArtifactRequest,
    service: ArtifactService = Depends(get_storage_artifact_service),
    _user=Depends(require_maintainer),
):
    record = service.store_text(
        run_id=run_id,
        adapter_id=payload.adapter_id,
        artifact_name=payload.artifact_name,
        text=payload.content,
        content_type=payload.content_type,
        metadata=payload.metadata,
    )
    return record.to_dict()


@router.get("/runs/{run_id}/artifacts")
async def list_artifacts(
    run_id: str,
    adapter_id: Optional[str] = None,
    service: ArtifactService = Depends(get_storage_artifact_service),
    _user=Depends(get_user_context),
):
    items = service.list_run_artifacts(run_id=run_id, adapter_id=adapter_id)
    return {"items": [row.to_dict() for row in items], "count": len(items)}


@router.post("/memory/remember")
async def remember_failure(
    payload: RememberFailureRequest,
    service: MemoryService = Depends(get_storage_memory_service),
    _user=Depends(require_maintainer),
):
    signature = FailureSignature.from_dict(payload.signature)
    record = service.remember_failure(
        adapter_id=payload.adapter_id,
        project_id=payload.project_id,
        signature=signature,
        root_cause=payload.root_cause,
        severity=payload.severity,
        confidence=payload.confidence,
        flaky=payload.flaky,
        recommended_actions=payload.recommended_actions,
        action_note=payload.action_note,
        metadata=payload.metadata,
        semantic_text=payload.semantic_text,
    )
    return record.to_dict()


@router.post("/memory/exact-lookup")
async def exact_lookup(
    payload: ExactLookupRequest,
    service: MemoryService = Depends(get_storage_memory_service),
    _user=Depends(get_user_context),
):
    signature = FailureSignature.from_dict(payload.signature)
    record = service.exact_lookup(adapter_id=payload.adapter_id, signature=signature)
    if record is None:
        return {"found": False, "item": None}
    return {"found": True, "item": record.to_dict()}


@router.post("/memory/similar-lookup")
async def similar_lookup(
    payload: SimilarLookupRequest,
    service: MemoryService = Depends(get_storage_memory_service),
    _user=Depends(get_user_context),
):
    matches = service.similar_lookup(
        adapter_id=payload.adapter_id,
        query_text=payload.query_text,
        top_k=payload.top_k,
        min_score=payload.min_score,
    )
    return {"items": [match.to_dict() for match in matches], "count": len(matches)}
