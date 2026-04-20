from __future__ import annotations

import json
from pathlib import Path

from orchestrator.failure_analysis.application.analyzer import FailureAnalyzer
from orchestrator.failure_analysis.integration.pytest_bridge import (
    analyze_pytest_report_file,
    build_notification_group_lines,
)


def _sample_pytest_report() -> dict:
    return {
        "summary": {"total": 6, "passed": 2, "failed": 4, "skipped": 0},
        "tests": [
            {
                "nodeid": "tests/rankmate_wave1/test_admin_consistency_api.py::test_admin_cons_002_semantic_status_continuity",
                "outcome": "failed",
                "call": {
                    "outcome": "failed",
                    "crash": {"message": "status phase mismatch for seed final status"},
                },
            },
            {
                "nodeid": "tests/rankmate_wave1/test_admin_consistency_api.py::test_admin_cons_005_terminal_state_visibility",
                "outcome": "failed",
                "call": {
                    "outcome": "failed",
                    "crash": {"message": "status phase mismatch for seed final status"},
                },
            },
            {
                "nodeid": "tests/rankmate_wave1/test_search_store_api.py::test_store_api_004_invalid_store_returns_controlled_error",
                "outcome": "failed",
                "call": {"outcome": "failed", "crash": {"message": "Unexpected status 500 for invalid store id"}},
            },
            {
                "nodeid": "tests/rankmate_wave1/test_order_lifecycle_flow_api.py::test_ord_life_005_cancel_branch",
                "outcome": "failed",
                "call": {"outcome": "failed", "crash": {"message": "Missing integer status in payload"}},
            },
        ],
    }


def test_grouping_repeated_failures_and_category_inference():
    analyzer = FailureAnalyzer()
    report = analyzer.analyze_pytest_report(_sample_pytest_report())

    assert report.summary.total_failed == 4
    assert report.summary.total_groups == 3
    assert report.summary.highest_severity == "critical"

    top = report.groups[0]
    assert top.category == "cross_surface_consistency"
    assert top.count == 2
    assert top.owner == "order_state_owner"
    assert top.severity == "critical"


def test_known_pattern_infers_expected_owner_and_severity():
    analyzer = FailureAnalyzer()
    payload = {
        "summary": {"failed": 1},
        "tests": [
            {
                "nodeid": "tests/rankmate_wave1/test_search_store_api.py::test_store_500",
                "outcome": "failed",
                "call": {"outcome": "failed", "crash": {"message": "Unexpected status 500 in store API"}},
            }
        ],
    }
    report = analyzer.analyze_pytest_report(payload)
    assert report.groups[0].category == "server_error"
    assert report.groups[0].owner == "backend_service_owner"
    assert report.groups[0].severity == "critical"


def test_unknown_pattern_defaults_to_medium_and_qa_owner():
    analyzer = FailureAnalyzer()
    payload = {
        "summary": {"failed": 1},
        "tests": [
            {
                "nodeid": "tests/random/test_unknown.py::test_unknown",
                "outcome": "failed",
                "call": {"outcome": "failed", "crash": {"message": "Unexpected unicode edge case occurred"}},
            }
        ],
    }
    report = analyzer.analyze_pytest_report(payload)
    assert report.groups[0].category == "unknown_failure_pattern"
    assert report.groups[0].owner == "qa_lead"
    assert report.groups[0].severity == "medium"


def test_artifact_generation_and_history(tmp_path: Path):
    pytest_report = tmp_path / "pytest_report.json"
    out_path = tmp_path / "failure_analysis_report.json"
    history_path = tmp_path / "history.json"
    pytest_report.write_text(json.dumps(_sample_pytest_report()), encoding="utf-8")

    report = analyze_pytest_report_file(
        pytest_report_path=pytest_report,
        output_path=out_path,
        history_path=history_path,
        write_history=True,
    )
    assert report is not None
    assert out_path.exists()
    assert history_path.exists()

    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["summary"]["total_failed"] == 4
    assert loaded["summary"]["critical_group_count"] >= 1


def test_notification_group_lines_are_compact_and_actionable():
    analyzer = FailureAnalyzer()
    report = analyzer.analyze_pytest_report(_sample_pytest_report())
    lines = build_notification_group_lines(report.to_dict(), max_groups=3)
    assert len(lines) == 3
    assert "severity=CRITICAL" in lines[0]
    assert "owner=order_state_owner" in lines[0]
    assert "sample=tests/rankmate_wave1/test_admin_consistency_api.py::test_admin_cons_002_semantic_status_continuity" in lines[0]

