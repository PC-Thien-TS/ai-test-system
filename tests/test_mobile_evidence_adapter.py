from __future__ import annotations

import uuid
from pathlib import Path

from mobile_appium import MobileRunArtifact, MobileRunService, MobileTestSettings
from orchestrator.mobile_adapter import MobileOrchestratorAdapter
from orchestrator.mobile_evidence_adapter import (
    MOBILE_EXPLORATION_EVIDENCE_TYPE,
    MobileEvidenceAdapter,
    collect_mobile_exploration_evidence,
)


def _workspace_artifact_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_evidence_runs" / f"{test_name}_{run_id}.json"


def test_mobile_evidence_adapter_collects_passed_artifact_evidence():
    output_path = _workspace_artifact_path("passed_artifact")
    service = MobileRunService(MobileTestSettings())
    artifact = service.run_bounded_exploration(
        start_screen="LoginScreen",
        username="demo",
        password="demo123",
        max_steps=8,
        output_path=output_path,
    )

    evidence = MobileEvidenceAdapter().collect(artifact, artifact_path=output_path).to_dict()

    try:
        assert evidence["evidence_type"] == MOBILE_EXPLORATION_EVIDENCE_TYPE
        assert evidence["run_id"] == artifact.run_id
        assert evidence["status"] == "passed"
        assert evidence["stop_reason"] == "coverage_threshold_reached"
        assert evidence["visited_screen_count"] == 3
        assert evidence["executed_action_count"] == 3
        assert evidence["coverage_score"] == artifact.coverage_score
        assert evidence["policy_shape"] == "nested"
        assert evidence["artifact_path"] == str(output_path)
        assert evidence["error"] == ""
        assert evidence["failure_signal"] == ""
        assert 0.0 <= evidence["richness_score"] <= 1.0
        assert evidence["richness_score"] > 0.75
    finally:
        output_path.unlink(missing_ok=True)


def test_mobile_evidence_adapter_collects_failed_artifact_evidence():
    artifact = MobileRunArtifact(
        run_id="mobile-run-failed",
        passed=False,
        stop_reason="execution_error",
        visited_screens=[],
        executed_actions=[],
        coverage_score=0.0,
        policy_shape="nested",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        duration_ms=1000,
        error="RuntimeError: runner exploded",
    )

    evidence = MobileEvidenceAdapter().collect(artifact).to_dict()

    assert evidence == {
        "evidence_type": MOBILE_EXPLORATION_EVIDENCE_TYPE,
        "richness_score": evidence["richness_score"],
        "run_id": "mobile-run-failed",
        "status": "failed",
        "stop_reason": "execution_error",
        "visited_screen_count": 0,
        "executed_action_count": 0,
        "coverage_score": 0.0,
        "policy_shape": "nested",
        "artifact_path": "",
        "error": "RuntimeError: runner exploded",
        "failure_signal": "RuntimeError: runner exploded",
    }
    assert 0.0 <= evidence["richness_score"] <= 1.0
    assert evidence["richness_score"] >= 0.4


def test_mobile_evidence_adapter_richness_score_increases_with_more_signal():
    adapter = MobileEvidenceAdapter()

    sparse = adapter.collect(
        {
            "run_id": "run-sparse",
            "passed": True,
            "stop_reason": "",
            "visited_screens": [],
            "executed_actions": [],
            "coverage_score": 0.0,
            "policy_shape": "",
            "error": "",
        }
    )
    rich = adapter.collect(
        {
            "run_id": "run-rich",
            "passed": True,
            "stop_reason": "coverage_threshold_reached",
            "visited_screens": ["AUTH_LOGIN", "CONTENT_LIST", "CONTENT_DETAIL"],
            "executed_actions": ["submit_login", "open_first_item", "go_back"],
            "coverage_score": 1.0,
            "policy_shape": "nested",
            "artifact_path": "artifacts/mobile_run.json",
            "error": "",
        }
    )

    assert sparse.richness_score < rich.richness_score
    assert rich.richness_score > 0.85


def test_mobile_evidence_adapter_handles_missing_fields_safely():
    evidence = collect_mobile_exploration_evidence(
        {
            "artifact": {
                "run_id": "run-empty",
                "passed": None,
                "visited_screens": None,
                "executed_actions": None,
                "coverage_score": None,
                "policy_shape": None,
                "error": None,
            },
            "summary": {},
        }
    )

    assert evidence == {
        "evidence_type": MOBILE_EXPLORATION_EVIDENCE_TYPE,
        "richness_score": evidence["richness_score"],
        "run_id": "run-empty",
        "status": "unknown",
        "stop_reason": "",
        "visited_screen_count": 0,
        "executed_action_count": 0,
        "coverage_score": 0.0,
        "policy_shape": "",
        "artifact_path": "",
        "error": "",
        "failure_signal": "",
    }
    assert 0.0 <= evidence["richness_score"] <= 0.2


def test_mobile_evidence_adapter_accepts_mobile_orchestrator_result_shape():
    service = MobileRunService(MobileTestSettings())
    orchestrator_result = MobileOrchestratorAdapter(service=service).execute_exploration_run(
        start_screen="LoginScreen",
        username="demo",
        password="demo123",
        max_steps=8,
    )

    evidence = MobileEvidenceAdapter().collect(orchestrator_result).to_dict()

    assert evidence["evidence_type"] == MOBILE_EXPLORATION_EVIDENCE_TYPE
    assert evidence["run_id"] == orchestrator_result["run_id"]
    assert evidence["status"] == "passed"
    assert evidence["stop_reason"] == orchestrator_result["summary"]["stop_reason"]
    assert evidence["visited_screen_count"] == orchestrator_result["summary"]["visited_screen_count"]
    assert evidence["executed_action_count"] == orchestrator_result["summary"]["executed_action_count"]
    assert evidence["coverage_score"] == orchestrator_result["summary"]["coverage_score"]
    assert evidence["policy_shape"] == orchestrator_result["summary"]["policy_shape"]
