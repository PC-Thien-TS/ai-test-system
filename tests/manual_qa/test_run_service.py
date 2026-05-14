from __future__ import annotations

from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_suite():
    suite_service = TestSuiteService()
    return suite_service.create_test_suite(
        project_id="checkout-web",
        name="Checkout Regression",
        test_cases=["TC-001", "TC-002", "TC-003"],
        owner="qa-team",
    )


def test_creates_run_from_suite():
    service = TestRunService()
    suite = _build_suite()

    test_run = service.create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="2026.05.14.1",
        tester="alice",
    )

    assert test_run.run_id == "RUN-001"
    assert test_run.suite_id == suite.suite_id
    assert test_run.project_id == "checkout-web"


def test_initializes_one_result_per_test_case_with_not_run_status():
    service = TestRunService()
    suite = _build_suite()

    test_run = service.create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="2026.05.14.1",
        tester="alice",
    )

    assert len(test_run.results) == 3
    assert [result.test_case_id for result in test_run.results] == ["TC-001", "TC-002", "TC-003"]
    assert all(result.status == "Not Run" for result in test_run.results)


def test_run_has_environment_build_tester_metadata():
    service = TestRunService()
    suite = _build_suite()

    test_run = service.create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="uat",
        build="build-123",
        tester="bob",
        metadata={"release": "candidate"},
    )

    assert test_run.environment == "uat"
    assert test_run.build == "build-123"
    assert test_run.tester == "bob"
    assert test_run.metadata["release"] == "candidate"
    assert test_run.status == "Not Started"


def test_generates_stable_run_ids():
    service = TestRunService()
    suite = _build_suite()

    first = service.create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="b1",
        tester="alice",
    )
    second = service.create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="b2",
        tester="bob",
    )

    assert first.run_id == "RUN-001"
    assert second.run_id == "RUN-002"
