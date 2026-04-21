from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orchestrator.dashboard_intelligence.application.service import DashboardIntelligenceService
from orchestrator.dashboard_intelligence.domain.models import DashboardQueryFilter
from orchestrator.dashboard_intelligence.infrastructure.local_readers import LocalDashboardArtifactReader
from orchestrator.dashboard_intelligence.infrastructure.query_repository import DashboardQueryRepository


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture()
def seeded_artifacts(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=30)

    _write_json(
        root / "failure_memory" / "mem1.json",
        {
            "memory_id": "mem-1",
            "signature_hash": "sig-1",
            "root_cause": "checkout timeout",
            "occurrence_count": 5,
            "confidence": 0.91,
            "severity": "high",
            "flaky": False,
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "module": "checkout",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "failure_memory" / "mem2.json",
        {
            "memory_id": "mem-2",
            "signature_hash": "sig-2",
            "root_cause": "search flaky response",
            "occurrence_count": 2,
            "confidence": 0.61,
            "severity": "medium",
            "flaky": True,
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "module": "search",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "failure_memory" / "old_mem.json",
        {
            "memory_id": "mem-old",
            "signature_hash": "sig-old",
            "root_cause": "legacy issue",
            "occurrence_count": 4,
            "confidence": 0.8,
            "severity": "high",
            "flaky": False,
            "adapter_id": "other",
            "project_id": "other",
            "module": "legacy",
            "timestamp": old.isoformat(),
        },
    )

    _write_json(
        root / "decision_results" / "d1.json",
        {
            "primary_decision": "BLOCK_RELEASE",
            "rationale": ["Release-critical payment path failure."],
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "severity": "critical",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "decision_results" / "d2.json",
        {
            "primary_decision": "ESCALATE",
            "rationale": ["Repeated backend issue."],
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "severity": "high",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "decision_results" / "d3.json",
        {
            "primary_decision": "RERUN_WITH_STRATEGY",
            "rationale": ["Rerun strategy historically effective."],
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "severity": "medium",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "decision_results" / "d4.json",
        {
            "primary_decision": "MANUAL_INVESTIGATION",
            "rationale": ["Ambiguous signal requires manual review."],
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "severity": "high",
            "timestamp": now.isoformat(),
        },
    )

    _write_json(
        root / "self_healing_actions" / "a1.json",
        {
            "action_id": "a1",
            "strategy": "retry_with_backoff",
            "executed": True,
            "success": True,
            "attempts_used": 1,
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
            "logs": ["ok"],
            "metadata": {},
        },
    )
    _write_json(
        root / "self_healing_actions" / "a2.json",
        {
            "action_id": "a2",
            "strategy": "retry_3x",
            "executed": True,
            "success": False,
            "attempts_used": 3,
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
            "logs": ["guardrail stop triggered"],
            "metadata": {"guardrail": "max attempts per failure reached"},
        },
    )
    _write_json(
        root / "self_healing_actions" / "a3.json",
        {
            "action_id": "a3",
            "strategy": "retry_3x",
            "executed": True,
            "success": False,
            "attempts_used": 2,
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
            "logs": ["failed"],
            "metadata": {},
        },
    )

    _write_json(
        root / "candidate_artifacts" / "bugs" / "bug1.json",
        {
            "candidate_id": "BUG-1",
            "artifact_type": "bug_candidate",
            "title": "bug one",
            "recurrence": 5,
            "severity": "high",
            "confidence": 0.9,
            "recommended_owner": "backend_owner",
            "generation_status": "created",
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "candidate_artifacts" / "bugs" / "bug2.json",
        {
            "candidate_id": "BUG-2",
            "artifact_type": "bug_candidate",
            "title": "bug two",
            "recurrence": 2,
            "severity": "medium",
            "confidence": 0.7,
            "recommended_owner": "qa_automation",
            "generation_status": "updated",
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "candidate_artifacts" / "incidents" / "inc1.json",
        {
            "candidate_id": "INC-1",
            "artifact_type": "incident_candidate",
            "title": "incident one",
            "recurrence": 4,
            "severity": "critical",
            "confidence": 0.95,
            "recommended_owner": "sre_oncall",
            "generation_status": "created",
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
        },
    )
    _write_json(
        root / "candidate_artifacts" / "suppressions" / "sup1.json",
        {
            "suppression_id": "SUP-1",
            "candidate_type": "bug_candidate",
            "rationale": ["duplicate candidate exists"],
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "timestamp": now.isoformat(),
            "metadata": {"duplicate_candidate_id": "BUG-1"},
        },
    )

    _write_json(
        root / "release" / "rel1.json",
        {
            "decision": "release_with_caution",
            "release_penalty": 11,
            "timestamp": now.isoformat(),
        },
    )

    _write_json(
        root / "ci_gate" / "ci1.json",
        {
            "ci_gate_status": "warning",
            "timestamp": now.isoformat(),
        },
    )
    return root


def _service(root: Path) -> DashboardIntelligenceService:
    reader = LocalDashboardArtifactReader(root)
    repo = DashboardQueryRepository(reader)
    return DashboardIntelligenceService(
        query_repository=repo,
        intelligence_enabled=True,
        trend_window_days=7,
        executive_top_risks_limit=5,
        leaderboard_limit=10,
    )


def test_release_readiness_summary_calculation(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    summary = svc.get_release_readiness_summary(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert summary.active_blockers == 1
    assert summary.active_incident_candidates == 1
    assert summary.escalation_count == 2
    assert summary.unresolved_actions == 2
    assert summary.release_penalty_total == 11
    assert summary.risk_level == "high"


def test_top_recurring_failure_aggregation(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    rows = svc.get_top_recurring_failures(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"), limit=2)
    assert rows
    assert rows[0].key == "mem-1"
    assert rows[0].count >= 5


def test_decision_distribution_summary(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    summary = svc.get_decision_summary(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert summary.block_release_count == 1
    assert summary.escalate_count == 1
    assert summary.rerun_count == 1
    assert summary.manual_review_count == 1


def test_self_healing_strategy_effectiveness_summary(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    summary = svc.get_self_healing_summary(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert summary.total_actions == 3
    assert summary.success_rate > 0
    by_strategy = {s.strategy: s for s in summary.strategy_effectiveness}
    assert "retry_3x" in by_strategy
    assert by_strategy["retry_3x"].failure_count >= 1


def test_candidate_summary_aggregation(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    summary = svc.get_candidate_summary(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert summary.total_bug_candidates == 2
    assert summary.total_incident_candidates == 1
    assert summary.duplicate_suppression_count == 1
    assert summary.owner_distribution.get("backend_owner", 0) >= 1


def test_governance_suppression_counting(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    summary = svc.get_governance_summary(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert summary.suppressed_candidate_count == 1
    assert summary.manual_review_count == 1
    assert summary.critical_path_guardrail_stops >= 1


def test_executive_snapshot_generation(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    snap = svc.get_executive_snapshot(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert snap.headline_status in {"at_risk", "watch", "healthy"}
    assert snap.top_risks
    assert snap.top_actions


def test_trend_series_generation(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    trend = svc.get_trend_series(
        DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"),
        metric="candidate_bug",
    )
    assert trend["metric"] == "candidate_bug"
    assert "points" in trend
    assert isinstance(trend["points"], list)


def test_filtering_by_adapter_project_date_range(seeded_artifacts: Path):
    svc = _service(seeded_artifacts)
    start = datetime.now(timezone.utc) - timedelta(days=7)
    end = datetime.now(timezone.utc)
    q = DashboardQueryFilter(adapter_id="other", project_id="other", start_date=start, end_date=end)
    rows = svc.get_top_recurring_failures(q)
    # old other record is outside date range, so should be empty
    assert rows == []


def test_graceful_behavior_with_missing_partial_local_artifacts(tmp_path: Path):
    root = tmp_path / "artifacts"
    svc = _service(root)
    q = DashboardQueryFilter(adapter_id="rankmate")
    rel = svc.get_release_readiness_summary(q)
    mem = svc.get_failure_memory_summary(q)
    dec = svc.get_decision_summary(q)
    sh = svc.get_self_healing_summary(q)
    cand = svc.get_candidate_summary(q)
    gov = svc.get_governance_summary(q)
    snap = svc.get_executive_snapshot(q)
    assert rel.active_blockers == 0
    assert mem.recurring_failure_count == 0
    assert dec.decision_counts == {}
    assert sh.total_actions == 0
    assert cand.total_bug_candidates == 0
    assert gov.suppressed_candidate_count == 0
    assert snap.release_readiness.active_blockers == 0


def test_release_readiness_uses_shared_release_decision_from_artifact_root(tmp_path: Path):
    root = tmp_path / "artifacts"
    _write_json(
        root / "release_decision.json",
        {
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "release_penalty_recommendation": 18,
            "release_signal": "block",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    svc = _service(root)
    summary = svc.get_release_readiness_summary(DashboardQueryFilter(adapter_id="rankmate", project_id="rankmate"))
    assert summary.release_penalty_total == 18


def test_api_endpoint_executive_summary(seeded_artifacts: Path, monkeypatch):
    fastapi = pytest.importorskip("fastapi")
    testclient_mod = pytest.importorskip("fastapi.testclient")
    from api.dashboard_app import create_app
    import api.routes.dashboard_intelligence as route_mod

    svc = _service(seeded_artifacts)
    monkeypatch.setattr(route_mod, "_service", lambda: svc)

    app = create_app()
    client = testclient_mod.TestClient(app)
    response = client.get("/dashboard/intelligence/executive-summary", params={"adapter_id": "rankmate", "project_id": "rankmate"})
    assert response.status_code == 200
    payload = response.json()
    assert "headline_status" in payload
    assert "release_readiness" in payload
