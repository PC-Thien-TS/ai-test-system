from __future__ import annotations

from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.failure_memory_service import FailureMemoryService
from orchestrator.manual_qa.models import ManualTestCase
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.suite_service import TestSuiteService


def _build_bug_draft():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Suite",
        test_cases=["TC-001"],
    )
    test_run = TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="2026.05.14.1",
        tester="alice",
    )
    test_case = ManualTestCase(
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Checkout",
        title="Checkout validation failure",
        steps=["Open checkout.", "Submit invalid payload."],
        expected_result="A validation message is shown.",
        metadata={"module": "Checkout"},
    )
    TestResultService().update_test_result(
        test_run,
        "TC-001",
        "Fail",
        actual_result="No validation message was shown and request succeeded.",
    )
    return BugDraftService().generate_bug_draft(
        test_run,
        "TC-001",
        test_case=test_case,
        metadata={"module": "Checkout", "run_id": test_run.run_id, "tags": ["checkout", "validation"]},
    )


def test_creates_failure_signature_from_manual_fields():
    service = FailureMemoryService()

    signature = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation message missing",
        expected_result="A validation message is shown.",
        actual_result="The request succeeded without validation.",
        environment="staging",
        build="build-001",
        severity="Major",
        priority="High",
        source_bug_id="BUG-001",
        tags=["checkout"],
        metadata={"run_id": "RUN-001"},
    )

    assert signature.signature_id == "FSIG-001"
    assert signature.test_case_id == "TC-001"
    assert signature.fingerprint.startswith("FP-")


def test_creates_failure_signature_from_bug_draft():
    service = FailureMemoryService()
    bug_draft = _build_bug_draft()

    signature = service.create_failure_signature_from_bug_draft(bug_draft)

    assert signature.source_bug_id == bug_draft.bug_id
    assert signature.test_case_id == bug_draft.test_case_id
    assert signature.expected_result == bug_draft.expected_result
    assert signature.actual_result == bug_draft.actual_result


def test_generated_fingerprint_is_stable_for_same_input():
    service = FailureMemoryService()

    first = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation missing",
        expected_result="Message shown.",
        actual_result="Message missing.",
        environment="staging",
        build="build-001",
    )
    second = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation missing",
        expected_result="Message shown.",
        actual_result="Message missing.",
        environment="staging",
        build="build-001",
    )

    assert first.fingerprint == second.fingerprint
    assert first.signature_id == "FSIG-001"
    assert second.signature_id == "FSIG-002"


def test_remember_failure_creates_new_record_and_same_fingerprint_increments_occurrence_count():
    service = FailureMemoryService()

    first = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation missing",
        expected_result="Message shown.",
        actual_result="Message missing.",
        source_bug_id="BUG-001",
        metadata={"run_id": "RUN-001"},
    )
    first_record = service.remember_failure(first)
    second = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation missing",
        expected_result="Message shown.",
        actual_result="Message missing.",
        source_bug_id="BUG-001",
        metadata={"run_id": "RUN-001"},
    )
    updated_record = service.remember_failure(second)

    assert first_record.record_id == "FMEM-001"
    assert updated_record.record_id == "FMEM-001"
    assert updated_record.occurrence_count == 2
    assert updated_record.related_bug_ids == ["BUG-001"]


def test_find_exact_failure_returns_matching_record_and_none_for_unknown():
    service = FailureMemoryService()
    signature = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation missing",
        expected_result="Message shown.",
        actual_result="Message missing.",
    )
    record = service.remember_failure(signature)

    assert service.find_exact_failure(signature.fingerprint) is record
    assert service.find_exact_failure("FP-UNKNOWN") is None


def test_find_similar_failures_returns_same_module_title_overlap_matches_ranked_first():
    service = FailureMemoryService()
    strong = service.remember_failure(
        service.create_failure_signature(
            module="Checkout",
            test_case_id="TC-001",
            title="Checkout validation failure",
            symptom="Validation message missing on invalid card",
            expected_result="Validation is shown.",
            actual_result="Validation missing and payment passed.",
            severity="Major",
            priority="High",
            source_bug_id="BUG-001",
            metadata={"run_id": "RUN-001"},
        )
    )
    weak = service.remember_failure(
        service.create_failure_signature(
            module="Checkout",
            test_case_id="TC-009",
            title="Checkout button style issue",
            symptom="Button layout shifted",
            expected_result="Button alignment is correct.",
            actual_result="Button misaligned after resize.",
            severity="Minor",
            priority="Low",
            source_bug_id="BUG-002",
            metadata={"run_id": "RUN-002"},
        )
    )
    _other_module = service.remember_failure(
        service.create_failure_signature(
            module="Auth",
            test_case_id="TC-020",
            title="Login validation failure",
            symptom="Validation missing on empty password",
            expected_result="Validation is shown.",
            actual_result="Validation missing and login request sent.",
            severity="Major",
            priority="High",
            source_bug_id="BUG-003",
            metadata={"run_id": "RUN-003"},
        )
    )

    query = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Missing validation message for invalid card",
        expected_result="Validation is shown.",
        actual_result="Payment passed without validation.",
        severity="Major",
        priority="High",
    )
    matches = service.find_similar_failures(query)

    assert matches[0].record_id == strong.record_id
    assert matches[0].metadata["similarity_score"] >= matches[1].metadata["similarity_score"]
    assert any(match.record_id == weak.record_id for match in matches)


def test_no_vector_db_or_external_ai_is_required():
    service = FailureMemoryService()
    signature = service.create_failure_signature(title="Simple failure", actual_result="Observed failure")
    record = service.remember_failure(signature)
    matches = service.find_similar_failures(signature)

    assert record.record_id == "FMEM-001"
    assert isinstance(matches, list)
