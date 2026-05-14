from __future__ import annotations

import pytest

from orchestrator.manual_qa.models import ManualTestCase
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_test_cases() -> list[ManualTestCase]:
    return [
        ManualTestCase(
            test_case_id="TC-001",
            requirement_ids=["REQ-001"],
            module="Checkout",
            title="Checkout happy path",
        ),
        ManualTestCase(
            test_case_id="TC-002",
            requirement_ids=["REQ-002"],
            module="Checkout",
            title="Checkout validation path",
        ),
    ]


def test_creates_suite_from_manual_test_case_objects():
    service = TestSuiteService()

    suite = service.create_test_suite(
        project_id="checkout-web",
        name="Checkout Regression",
        test_cases=_build_test_cases(),
    )

    assert suite.suite_id == "SUITE-001"
    assert suite.test_case_ids == ["TC-001", "TC-002"]


def test_creates_suite_from_test_case_ids_and_preserves_order():
    service = TestSuiteService()

    suite = service.create_test_suite(
        project_id="checkout-web",
        name="Checkout Smoke",
        test_cases=["TC-010", "TC-002", "TC-003"],
    )

    assert suite.test_case_ids == ["TC-010", "TC-002", "TC-003"]


def test_rejects_empty_test_case_list():
    service = TestSuiteService()

    with pytest.raises(ValueError, match="must not be empty"):
        service.create_test_suite(
            project_id="checkout-web",
            name="Empty Suite",
            test_cases=[],
        )


def test_generates_stable_suite_ids():
    service = TestSuiteService()

    first = service.create_test_suite(
        project_id="checkout-web",
        name="Suite A",
        test_cases=["TC-001"],
    )
    second = service.create_test_suite(
        project_id="checkout-web",
        name="Suite B",
        test_cases=["TC-002"],
    )

    assert first.suite_id == "SUITE-001"
    assert second.suite_id == "SUITE-002"
