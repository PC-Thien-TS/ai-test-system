from __future__ import annotations

import pytest

from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_run():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Suite",
        test_cases=["TC-001", "TC-002"],
    )
    test_run = TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="2026.05.14.1",
        tester="alice",
    )
    TestResultService().update_test_result(test_run, "TC-001", "Fail", actual_result="Button was disabled.")
    return test_run


def test_attaches_screenshot_evidence_to_existing_test_result():
    service = EvidenceService()
    test_run = _build_run()

    evidence = service.attach_evidence(
        test_run,
        "TC-001",
        "screenshot",
        "artifacts/screenshots/checkout-fail.png",
        description="Checkout failure screenshot",
        content_type="image/png",
    )

    assert evidence.evidence_id == "EVD-001"
    assert evidence.evidence_type == "screenshot"
    assert evidence.run_id == test_run.run_id
    assert evidence.test_case_id == "TC-001"


def test_attaches_log_and_note_evidence_and_generates_stable_ids():
    service = EvidenceService()
    test_run = _build_run()

    log_evidence = service.attach_evidence(
        test_run,
        "TC-001",
        "log",
        "https://logs.example.local/run/1",
    )
    note_evidence = service.attach_evidence(
        test_run,
        "TC-001",
        "note",
        "manual-note://checkout",
        description="Tester noted intermittent spinner behavior.",
    )

    assert log_evidence.evidence_id == "EVD-001"
    assert note_evidence.evidence_id == "EVD-002"
    assert note_evidence.description == "Tester noted intermittent spinner behavior."


def test_preserves_run_id_and_test_case_id_and_adds_metadata_reference():
    service = EvidenceService()
    test_run = _build_run()

    evidence = service.attach_evidence(
        test_run,
        "TC-001",
        "api_response",
        "manual://api-response/checkout",
    )

    matching_result = next(result for result in test_run.results if result.test_case_id == "TC-001")
    assert evidence.run_id == test_run.run_id
    assert evidence.test_case_id == "TC-001"
    assert matching_result.metadata["evidence_ids"] == ["EVD-001"]
    assert matching_result.metadata["evidence"][0]["evidence_id"] == "EVD-001"


def test_raises_error_for_unknown_test_case_id():
    service = EvidenceService()
    test_run = _build_run()

    with pytest.raises(ValueError, match="does not exist"):
        service.attach_evidence(test_run, "TC-999", "note", "manual://missing")


def test_does_not_require_actual_file_path_to_exist():
    service = EvidenceService()
    test_run = _build_run()

    evidence = service.attach_evidence(
        test_run,
        "TC-001",
        "file",
        "C:/does/not/exist/screenshot.png",
    )

    assert evidence.path_or_url == "C:/does/not/exist/screenshot.png"
