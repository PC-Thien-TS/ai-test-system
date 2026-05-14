from __future__ import annotations

import pytest

from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.models import ManualTestCase
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_run():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Suite",
        test_cases=["TC-001", "TC-002", "TC-003", "TC-004"],
    )
    return TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="2026.05.14.1",
        tester="alice",
    )


def _build_manual_test_case(test_case_id: str) -> ManualTestCase:
    return ManualTestCase(
        test_case_id=test_case_id,
        requirement_ids=["REQ-001"],
        module="Checkout",
        title="Checkout payment validation",
        steps=["Open checkout.", "Submit invalid payment details.", "Observe the response."],
        expected_result="The payment is rejected with a validation message.",
    )


def test_generates_bug_draft_from_fail_result():
    result_service = TestResultService()
    bug_service = BugDraftService()
    test_run = _build_run()
    result_service.update_test_result(
        test_run,
        "TC-001",
        "Fail",
        actual_result="The system accepted invalid card data.",
    )

    bug = bug_service.generate_bug_draft(
        test_run,
        "TC-001",
        test_case=_build_manual_test_case("TC-001"),
    )

    assert bug.bug_id == "BUG-001"
    assert bug.status == "Draft"
    assert bug.severity == "Major"
    assert bug.priority == "High"
    assert bug.actual_result == "The system accepted invalid card data."


def test_generates_bug_draft_from_blocked_result():
    result_service = TestResultService()
    bug_service = BugDraftService()
    test_run = _build_run()
    result_service.update_test_result(
        test_run,
        "TC-002",
        "Blocked",
        actual_result="The staging payment gateway was unavailable.",
    )

    bug = bug_service.generate_bug_draft(test_run, "TC-002")

    assert bug.bug_id == "BUG-001"
    assert bug.severity == "Major"
    assert bug.priority == "High"


def test_rejects_pass_result():
    result_service = TestResultService()
    bug_service = BugDraftService()
    test_run = _build_run()
    result_service.update_test_result(test_run, "TC-001", "Pass")

    with pytest.raises(ValueError, match="only allowed"):
        bug_service.generate_bug_draft(test_run, "TC-001")


def test_rejects_not_run_result():
    bug_service = BugDraftService()
    test_run = _build_run()

    with pytest.raises(ValueError, match="only allowed"):
        bug_service.generate_bug_draft(test_run, "TC-001")


def test_includes_expected_result_steps_and_evidence_ids_when_provided():
    result_service = TestResultService()
    evidence_service = EvidenceService()
    bug_service = BugDraftService()
    test_run = _build_run()
    result_service.update_test_result(
        test_run,
        "TC-003",
        "Fail",
        actual_result="Validation message was missing.",
    )
    evidence = evidence_service.attach_evidence(
        test_run,
        "TC-003",
        "screenshot",
        "artifacts/screenshots/validation-missing.png",
    )

    test_case = _build_manual_test_case("TC-003")
    bug = bug_service.generate_bug_draft(
        test_run,
        "TC-003",
        test_case=test_case,
        evidence=[evidence],
    )

    assert bug.steps_to_reproduce == test_case.steps
    assert bug.expected_result == test_case.expected_result
    assert bug.evidence_ids == ["EVD-001"]


def test_allows_severity_priority_override():
    result_service = TestResultService()
    bug_service = BugDraftService()
    test_run = _build_run()
    result_service.update_test_result(
        test_run,
        "TC-004",
        "Retest",
        actual_result="Fix needs confirmation after rerun.",
    )

    bug = bug_service.generate_bug_draft(
        test_run,
        "TC-004",
        severity="Critical",
        priority="Urgent",
    )

    assert bug.severity == "Critical"
    assert bug.priority == "Urgent"


def test_raises_error_for_unknown_test_case_id():
    bug_service = BugDraftService()
    test_run = _build_run()

    with pytest.raises(ValueError, match="does not exist"):
        bug_service.generate_bug_draft(test_run, "TC-999")
