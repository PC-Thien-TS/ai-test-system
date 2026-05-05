from __future__ import annotations

from mobile_appium import MobileRunArtifact, MobileRunService, MobileTestSettings
from orchestrator.mobile_evidence_adapter import MobileEvidenceAdapter
from orchestrator.mobile_failure_classifier import (
    MOBILE_COVERAGE_NOT_REACHED,
    MOBILE_DRIVER_ERROR,
    MOBILE_NAVIGATION_FAILURE,
    MOBILE_POLICY_UNSUPPORTED_ACTION,
    SUCCESS,
    UNKNOWN,
    MobileFailureClassifier,
    classify_mobile_failure,
)


def test_mobile_failure_classifier_returns_success_for_passed_evidence():
    service = MobileRunService(MobileTestSettings())
    evidence = MobileEvidenceAdapter().collect(
        service.run_bounded_exploration(
            start_screen="LoginScreen",
            username="demo",
            password="demo123",
            max_steps=8,
        )
    )

    result = MobileFailureClassifier().classify(evidence).to_dict()

    assert result["failure_type"] == SUCCESS
    assert result["severity"] == "low"
    assert result["confidence"] >= 0.95
    assert result["likely_owner"] == "qa_platform"


def test_mobile_failure_classifier_classifies_driver_error():
    result = classify_mobile_failure(
        {
            "run_id": "run-driver",
            "passed": False,
            "stop_reason": "execution_error",
            "visited_screens": [],
            "executed_actions": [],
            "coverage_score": 0.0,
            "policy_shape": "nested",
            "error": "WebDriverException: Driver does not support opening detail screen.",
        }
    )

    assert result["failure_type"] == MOBILE_DRIVER_ERROR
    assert result["severity"] == "high"
    assert result["confidence"] >= 0.85
    assert result["likely_owner"] == "qa_infra"


def test_mobile_failure_classifier_classifies_policy_unsupported_action_from_orchestrator_result():
    orchestrator_result = {
        "plugin": "mobile_exploration",
        "status": "failed",
        "run_id": "run-policy",
        "summary": {
            "stop_reason": "no_valid_action",
            "coverage_score": 0.4,
            "policy_shape": "nested",
            "visited_screen_count": 2,
            "executed_action_count": 1,
        },
        "artifact": {
            "run_id": "run-policy",
            "passed": False,
            "stop_reason": "no_valid_action",
            "visited_screens": ["AUTH_LOGIN", "CONTENT_LIST"],
            "executed_actions": ["submit_login"],
            "coverage_score": 0.4,
            "policy_shape": "nested",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "duration_ms": 1000,
            "error": "AssertionError: Unsupported navigation action: unsupported_recovery",
        },
    }

    result = MobileFailureClassifier().classify(orchestrator_result).to_dict()

    assert result["failure_type"] == MOBILE_POLICY_UNSUPPORTED_ACTION
    assert result["severity"] == "medium"
    assert result["confidence"] >= 0.85
    assert result["likely_owner"] == "qa_policy"


def test_mobile_failure_classifier_classifies_coverage_not_reached():
    artifact = MobileRunArtifact(
        run_id="run-coverage",
        passed=False,
        stop_reason="max_steps_reached",
        visited_screens=["AUTH_LOGIN", "CONTENT_LIST"],
        executed_actions=["submit_login"],
        coverage_score=0.5,
        policy_shape="flat",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:02Z",
        duration_ms=2000,
        error="",
    )

    result = MobileFailureClassifier().classify(artifact).to_dict()

    assert result["failure_type"] == MOBILE_COVERAGE_NOT_REACHED
    assert result["severity"] == "medium"
    assert result["confidence"] >= 0.8
    assert result["likely_owner"] == "qa_automation"


def test_mobile_failure_classifier_classifies_navigation_failure():
    result = classify_mobile_failure(
        {
            "evidence_type": "mobile_exploration",
            "richness_score": 0.84,
            "run_id": "run-navigation",
            "status": "failed",
            "stop_reason": "cycle_detected",
            "visited_screen_count": 2,
            "executed_action_count": 3,
            "coverage_score": 0.5,
            "policy_shape": "nested",
            "artifact_path": "",
            "error": "AssertionError: Detail screen is not loaded.",
            "failure_signal": "AssertionError: Detail screen is not loaded.",
        }
    )

    assert result["failure_type"] == MOBILE_NAVIGATION_FAILURE
    assert result["severity"] == "high"
    assert result["confidence"] >= 0.85
    assert result["likely_owner"] == "mobile_app"


def test_mobile_failure_classifier_falls_back_to_unknown_for_sparse_payload():
    result = MobileFailureClassifier().classify(
        {
            "artifact": {
                "run_id": "run-unknown",
                "passed": False,
                "visited_screens": None,
                "executed_actions": None,
                "coverage_score": None,
                "policy_shape": None,
                "error": "",
            },
            "summary": {},
        }
    ).to_dict()

    assert result["failure_type"] == UNKNOWN
    assert result["severity"] == "medium"
    assert result["confidence"] <= 0.4
    assert result["likely_owner"] == "qa_platform"
