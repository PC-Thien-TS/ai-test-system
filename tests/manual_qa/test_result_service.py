from __future__ import annotations

import pytest

from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_run():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Suite",
        test_cases=["TC-001", "TC-002", "TC-003"],
    )
    return TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="2026.05.14.1",
        tester="alice",
    )


def test_updates_pass_result():
    service = TestResultService()
    test_run = _build_run()

    updated = service.update_test_result(test_run, "TC-001", "Pass", notes="verified")

    result = updated.results[0]
    assert result.status == "Pass"
    assert result.notes == "verified"
    assert updated.status == "In Progress"


def test_updates_fail_result_with_actual_result():
    service = TestResultService()
    test_run = _build_run()

    updated = service.update_test_result(
        test_run,
        "TC-002",
        "Fail",
        actual_result="Validation error did not appear.",
    )

    result = next(item for item in updated.results if item.test_case_id == "TC-002")
    assert result.status == "Fail"
    assert result.actual_result == "Validation error did not appear."
    assert updated.status == "Failed"


def test_rejects_unsupported_status():
    service = TestResultService()
    test_run = _build_run()

    with pytest.raises(ValueError, match="Unsupported status"):
        service.update_test_result(test_run, "TC-001", "Unknown")


def test_raises_error_for_unknown_test_case_id():
    service = TestResultService()
    test_run = _build_run()

    with pytest.raises(ValueError, match="does not exist"):
        service.update_test_result(test_run, "TC-999", "Pass")


def test_updates_run_status_correctly():
    service = TestResultService()
    test_run = _build_run()

    service.update_test_result(test_run, "TC-001", "Pass")
    assert test_run.status == "In Progress"

    service.update_test_result(test_run, "TC-002", "Pass")
    assert test_run.status == "In Progress"

    service.update_test_result(test_run, "TC-003", "Pass")
    assert test_run.status == "Passed"
