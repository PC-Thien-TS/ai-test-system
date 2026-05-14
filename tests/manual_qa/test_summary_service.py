from __future__ import annotations

from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_run():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Suite",
        test_cases=["TC-001", "TC-002", "TC-003", "TC-004", "TC-005"],
    )
    return TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="build-001",
        tester="qa-user",
    )


def test_summarizes_all_not_run():
    service = RunSummaryService()
    test_run = _build_run()

    summary = service.summarize_test_run(test_run)

    assert summary.total == 5
    assert summary.not_run == 5
    assert summary.passed == 0
    assert summary.status == "Not Started"


def test_summarizes_mixed_pass_fail_blocked_skipped():
    result_service = TestResultService()
    summary_service = RunSummaryService()
    test_run = _build_run()

    result_service.update_test_result(test_run, "TC-001", "Pass")
    result_service.update_test_result(test_run, "TC-002", "Fail")
    result_service.update_test_result(test_run, "TC-003", "Blocked")
    result_service.update_test_result(test_run, "TC-004", "Skipped")

    summary = summary_service.summarize_test_run(test_run)

    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.blocked == 1
    assert summary.skipped == 1
    assert summary.not_run == 1
    assert summary.status == "Failed"


def test_computes_pass_rate_correctly():
    result_service = TestResultService()
    summary_service = RunSummaryService()
    test_run = _build_run()

    result_service.update_test_result(test_run, "TC-001", "Pass")
    result_service.update_test_result(test_run, "TC-002", "Pass")
    result_service.update_test_result(test_run, "TC-003", "Skipped")

    summary = summary_service.summarize_test_run(test_run)

    assert summary.pass_rate == 40.0


def test_summary_status_matches_run_status():
    result_service = TestResultService()
    summary_service = RunSummaryService()
    test_run = _build_run()

    for test_case_id in ["TC-001", "TC-002", "TC-003", "TC-004", "TC-005"]:
        result_service.update_test_result(test_run, test_case_id, "Pass")

    summary = summary_service.summarize_test_run(test_run)

    assert test_run.status == "Passed"
    assert summary.status == "Passed"
