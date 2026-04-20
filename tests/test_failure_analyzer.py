from __future__ import annotations

import json
from pathlib import Path

from orchestrator.failure_analysis.application.analyzer import FailureAnalyzer
from orchestrator.failure_analysis.integration.pytest_bridge import (
    analyze_pytest_report_file,
    build_notification_group_lines,
)


def _pytest_report_fixture() -> dict:
    return {
        "summary": {"total": 8, "passed": 3, "failed": 5, "skipped": 0, "error": 0},
        "tests": [
            {
                "nodeid": "tests/rankmate_wave1/test_admin_consistency_api.py::test_admin_cons_002_semantic_status_continuity",
                "outcome": "failed",
                "call": {"crash": {"message": "status phase mismatch for terminal seed order"}},
            },
            {
                "nodeid": "tests/rankmate_wave1/test_admin_consistency_api.py::test_admin_cons_005_terminal_action_safety",
                "outcome": "failed",
                "call": {"crash": {"message": "status phase mismatch for terminal seed order"}},
            },
            {
                "nodeid": "tests/rankmate_wave1/test_search_store_api.py::test_store_api_004_invalid_store_lookup",
                "outcome": "failed",
                "call": {"crash": {"message": "Unexpected status 500, expected [400, 404]"}},
            },
            {
                "nodeid": "tests/rankmate_wave1/test_store_contract_api.py::test_store_contract_has_integer_status",
                "outcome": "failed",
                "call": {"crash": {"message": "Missing integer status in payload"}},
            },
            {
                "nodeid": "tests/rankmate_wave1/test_merchant_transition_api.py::test_mer_api_021_stale_complete_rejected",
                "outcome": "failed",
                "call": {"crash": {"message": "Unexpected status 200, expected [400]"}},
            },
        ],
    }


def test_grouping_repeated_failures():
    analyzer = FailureAnalyzer()
    report = analyzer.analyze_pytest_report(_pytest_report_fixture())
    assert report.summary.total_failed == 5
    assert report.summary.total_groups < report.summary.total_failed
    grouped = {g.category: g.count for g in report.groups}
    assert grouped["cross_surface_consistency"] == 2


def test_category_inference_and_owner_suggestion():
    analyzer = FailureAnalyzer()
    report = analyzer.analyze_pytest_report(_pytest_report_fixture())
    by_category = {g.category: g for g in report.groups}

    assert by_category["api_contract_mismatch"].owner == "backend_api_owner"
    assert by_category["server_error"].owner == "backend_service_owner"
    assert by_category["state_transition_guard_missing"].owner == "merchant_flow_owner"


def test_severity_inference_and_highest_summary():
    analyzer = FailureAnalyzer()
    report = analyzer.analyze_pytest_report(_pytest_report_fixture())
    by_category = {g.category: g for g in report.groups}

    assert by_category["server_error"].severity == "critical"
    assert by_category["cross_surface_consistency"].severity == "critical"
    assert report.summary.highest_severity == "critical"
    assert report.summary.critical_group_count >= 2


def test_artifact_generation_and_history(tmp_path: Path):
    pytest_report_path = tmp_path / "pytest_report.json"
    analysis_output_path = tmp_path / "failure_analysis_report.json"
    history_path = tmp_path / "history.json"
    pytest_report_path.write_text(json.dumps(_pytest_report_fixture(), indent=2), encoding="utf-8")

    analysis = analyze_pytest_report_file(
        pytest_report_path=pytest_report_path,
        output_path=analysis_output_path,
        write_history=True,
        history_path=history_path,
    )
    assert analysis_output_path.exists()
    assert history_path.exists()
    loaded = json.loads(analysis_output_path.read_text(encoding="utf-8"))
    assert loaded["summary"]["total_failed"] == 5
    assert len(loaded["groups"]) >= 3


def test_notification_formatting_compatibility():
    analyzer = FailureAnalyzer()
    analysis = analyzer.to_dict(analyzer.analyze_pytest_report(_pytest_report_fixture()))
    lines = build_notification_group_lines(analysis, top_n=3)
    assert lines
    assert any("cross_surface_consistency" in ln for ln in lines)
    assert any("owner=" in ln for ln in lines)
    assert any("sample=" in ln for ln in lines)


def test_unknown_pattern_defaults():
    report = {
        "summary": {"total": 1, "passed": 0, "failed": 1, "skipped": 0, "error": 0},
        "tests": [
            {
                "nodeid": "tests/rankmate_wave1/test_unknown.py::test_unknown",
                "outcome": "failed",
                "call": {"crash": {"message": "completely new failure signature abc123"}},
            }
        ],
    }
    analyzer = FailureAnalyzer()
    output = analyzer.analyze_pytest_report(report)
    assert output.groups[0].category == "unknown_failure_pattern"
    assert output.groups[0].owner == "qa_lead"
    assert output.groups[0].severity == "medium"

