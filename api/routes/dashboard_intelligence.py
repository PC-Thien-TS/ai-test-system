from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Query

from orchestrator.dashboard_intelligence.domain.models import DashboardQueryFilter
from orchestrator.dashboard_intelligence.integration.api_bridge import to_response
from orchestrator.dashboard_intelligence.integration.provider import build_dashboard_intelligence_service


router = APIRouter(prefix="/dashboard/intelligence", tags=["dashboard-intelligence"])


@lru_cache(maxsize=1)
def _service():
    return build_dashboard_intelligence_service()


def _query_filter(
    adapter_id: Optional[str] = None,
    project_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    severity: Optional[str] = None,
    candidate_type: Optional[str] = None,
    owner: Optional[str] = None,
    decision_type: Optional[str] = None,
) -> DashboardQueryFilter:
    return DashboardQueryFilter(
        adapter_id=adapter_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        severity=severity,
        candidate_type=candidate_type,
        owner=owner,
        decision_type=decision_type,
    )


@router.get("/executive-summary")
def executive_summary(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    q = _query_filter(adapter_id=adapter_id, project_id=project_id, start_date=start_date, end_date=end_date)
    return to_response(_service().get_executive_snapshot(q))


@router.get("/release-readiness")
def release_readiness(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    q = _query_filter(adapter_id=adapter_id, project_id=project_id, start_date=start_date, end_date=end_date)
    return to_response(_service().get_release_readiness_summary(q))


@router.get("/failure-memory")
def failure_memory(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    severity: Optional[str] = Query(default=None),
):
    q = _query_filter(
        adapter_id=adapter_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        severity=severity,
    )
    return to_response(_service().get_failure_memory_summary(q))


@router.get("/decisions")
def decisions(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    decision_type: Optional[str] = Query(default=None),
):
    q = _query_filter(
        adapter_id=adapter_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        decision_type=decision_type,
    )
    return to_response(_service().get_decision_summary(q))


@router.get("/self-healing")
def self_healing(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    q = _query_filter(adapter_id=adapter_id, project_id=project_id, start_date=start_date, end_date=end_date)
    return to_response(_service().get_self_healing_summary(q))


@router.get("/candidates")
def candidates(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    candidate_type: Optional[str] = Query(default=None),
    owner: Optional[str] = Query(default=None),
):
    q = _query_filter(
        adapter_id=adapter_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        severity=severity,
        candidate_type=candidate_type,
        owner=owner,
    )
    return to_response(_service().get_candidate_summary(q))


@router.get("/governance")
def governance(
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    q = _query_filter(adapter_id=adapter_id, project_id=project_id, start_date=start_date, end_date=end_date)
    return to_response(_service().get_governance_summary(q))


@router.get("/trends")
def trends(
    metric: str = Query(..., description="Metric key, e.g. decision_block_release, candidate_bug, suppression"),
    window_days: Optional[int] = Query(default=None),
    adapter_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
):
    q = _query_filter(adapter_id=adapter_id, project_id=project_id, severity=severity)
    return to_response(_service().get_trend_series(q, metric=metric, window_days=window_days))

