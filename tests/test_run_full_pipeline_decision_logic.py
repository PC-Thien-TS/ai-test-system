from __future__ import annotations

from scripts.run_full_pipeline import build_decision_payload, default_decision_policy


def _failure_analysis() -> dict:
    return {
        "summary": {
            "total_failed": 2,
            "total_groups": 1,
            "highest_severity": "low",
            "most_affected_area": "qa.tests",
            "critical_group_count": 0,
        },
        "groups": [
            {
                "group_id": "flaky-login-timeout",
                "signature": "flaky-login-timeout",
                "severity": "low",
                "count": 2,
                "module_family": "qa.tests",
                "category": "timeout",
                "message_pattern": "transient timeout",
                "examples": ["timeout on retry"],
            }
        ],
    }


def _pytest_report() -> dict:
    return {
        "summary": {
            "total": 20,
            "passed": 18,
            "failed": 2,
            "skipped": 0,
        }
    }


def test_first_occurrence_flaky_failure_prefers_rerun_not_suppress():
    payload = build_decision_payload(
        project="rankmate",
        failure_analysis=_failure_analysis(),
        pytest_report=_pytest_report(),
        memory_context={
            "available": True,
            "seen_count": 1,
            "flaky_signal": True,
            "flaky_score": 0.95,
            "rerun_success_count": 0,
            "rerun_failure_count": 0,
            "rerun_success_rate": 0.0,
        },
        policy_config=default_decision_policy(),
        memory_context_source="memory-db",
        policy_source="default_policy",
    )
    assert payload["decision"] == "RERUN_RECOMMENDED"
    assert payload["release_action"] == "RETRY_BEFORE_RELEASE"


def test_repeated_failure_with_high_rerun_success_rate_suppresses():
    payload = build_decision_payload(
        project="rankmate",
        failure_analysis=_failure_analysis(),
        pytest_report=_pytest_report(),
        memory_context={
            "available": True,
            "seen_count": 2,
            "flaky_signal": True,
            "flaky_score": 0.60,
            "rerun_success_count": 4,
            "rerun_failure_count": 1,
            "rerun_success_rate": 0.8,
        },
        policy_config=default_decision_policy(),
        memory_context_source="memory-db",
        policy_source="default_policy",
    )
    assert payload["decision"] == "SUPPRESS"
    assert payload["release_action"] == "SUPPRESS_AND_MONITOR"


def test_repeated_failure_with_low_rerun_success_rate_escalates():
    payload = build_decision_payload(
        project="rankmate",
        failure_analysis=_failure_analysis(),
        pytest_report=_pytest_report(),
        memory_context={
            "available": True,
            "seen_count": 3,
            "flaky_signal": True,
            "flaky_score": 0.85,
            "rerun_success_count": 1,
            "rerun_failure_count": 3,
            "rerun_success_rate": 0.25,
        },
        policy_config=default_decision_policy(),
        memory_context_source="memory-db",
        policy_source="default_policy",
    )
    assert payload["decision"] == "ESCALATE"
    assert payload["release_action"] == "HOLD_AND_REVIEW"


def test_repeated_failure_with_mixed_rerun_success_rate_prefers_rerun():
    payload = build_decision_payload(
        project="rankmate",
        failure_analysis=_failure_analysis(),
        pytest_report=_pytest_report(),
        memory_context={
            "available": True,
            "seen_count": 2,
            "flaky_signal": True,
            "flaky_score": 0.55,
            "rerun_success_count": 1,
            "rerun_failure_count": 1,
            "rerun_success_rate": 0.5,
        },
        policy_config=default_decision_policy(),
        memory_context_source="memory-db",
        policy_source="default_policy",
    )
    assert payload["decision"] == "RERUN_RECOMMENDED"
    assert payload["release_action"] == "RETRY_BEFORE_RELEASE"
