from __future__ import annotations

from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.failure_memory_service import FailureMemoryService
from orchestrator.manual_qa.models import ManualTestCase, TestResult


def _smoke_case() -> ManualTestCase:
    return ManualTestCase(
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Authentication",
        title="Smoke login flow",
        steps=["Open login page.", "Enter valid credentials.", "Submit login."],
        expected_result="User is redirected to the dashboard.",
        priority="High",
        test_type="Smoke",
    )


def _subjective_case() -> ManualTestCase:
    return ManualTestCase(
        test_case_id="TC-002",
        requirement_ids=["REQ-002"],
        module="Checkout",
        title="Visual only checkout page review looks good",
        steps=["Open checkout page.", "Review layout manually."],
        expected_result="Looks good based on manual judgment and UX feeling.",
        priority="Medium",
        test_type="Usability",
    )


def _medium_case() -> ManualTestCase:
    return ManualTestCase(
        test_case_id="TC-003",
        requirement_ids=["REQ-003"],
        module="Profile",
        title="Update profile address",
        steps=["Open profile page.", "Update address.", "Save changes."],
        expected_result="Address is updated successfully.",
        priority="Medium",
        test_type="Positive",
    )


def test_scores_clear_smoke_regression_case_as_should_automate():
    service = AutomationCandidateService()

    candidate = service.score_automation_candidate(_smoke_case())

    assert candidate.candidate_id == "AUTO-001"
    assert candidate.recommendation == "Should Automate"
    assert candidate.score >= 70
    assert candidate.test_case_id == "TC-001"


def test_scores_vague_subjective_visual_case_as_do_not_automate():
    service = AutomationCandidateService()

    candidate = service.score_automation_candidate(_subjective_case())

    assert candidate.recommendation == "Do Not Automate"
    assert candidate.suggested_automation_type == "manual_only"
    assert any("subjective" in blocker.lower() or "judgment" in blocker.lower() for blocker in candidate.blockers)


def test_scores_medium_priority_functional_case_as_consider_later():
    service = AutomationCandidateService()

    candidate = service.score_automation_candidate(_medium_case())

    assert candidate.recommendation == "Consider Later"
    assert 40 <= candidate.score <= 69


def test_repeated_failure_record_increases_score():
    scoring_service = AutomationCandidateService()
    memory_service = FailureMemoryService()
    test_case = _medium_case()
    base_candidate = scoring_service.score_automation_candidate(test_case)

    signature = memory_service.create_failure_signature(
        module=test_case.module,
        test_case_id=test_case.test_case_id,
        title=test_case.title,
        expected_result=test_case.expected_result,
        actual_result="Address update intermittently fails.",
    )
    memory_service.remember_failure(signature)
    repeated_record = memory_service.remember_failure(signature)

    boosted_candidate = scoring_service.score_automation_candidate(
        test_case,
        failure_records=[repeated_record],
    )

    assert boosted_candidate.score > base_candidate.score
    assert repeated_record.record_id in boosted_candidate.related_failure_record_ids


def test_missing_expected_result_creates_blocker():
    service = AutomationCandidateService()
    test_case = ManualTestCase(
        test_case_id="TC-004",
        requirement_ids=["REQ-004"],
        module="Search",
        title="Search result verification",
        steps=["Open search.", "Enter query."],
        expected_result="",
        priority="High",
        test_type="Regression",
    )

    candidate = service.score_automation_candidate(test_case)

    assert candidate.recommendation == "Do Not Automate"
    assert any("missing steps or expected result" in blocker.lower() or "expected result" in blocker.lower() for blocker in candidate.blockers)


def test_captcha_manual_approval_external_payment_creates_critical_blocker():
    service = AutomationCandidateService()
    test_case = ManualTestCase(
        test_case_id="TC-005",
        requirement_ids=["REQ-005"],
        module="Checkout",
        title="External payment without mock requires manual approval and captcha",
        steps=["Open checkout.", "Complete external payment without mock."],
        expected_result="Payment is accepted.",
        priority="High",
        test_type="Regression",
    )

    candidate = service.score_automation_candidate(test_case)

    assert candidate.recommendation == "Do Not Automate"
    assert any("captcha" in blocker.lower() for blocker in candidate.blockers)
    assert any("manual approval" in blocker.lower() for blocker in candidate.blockers)


def test_preserves_requirement_ids_and_generates_stable_candidate_ids():
    service = AutomationCandidateService()

    first = service.score_automation_candidate(_smoke_case())
    second = service.score_automation_candidate(_medium_case())

    assert first.requirement_ids == ["REQ-001"]
    assert second.requirement_ids == ["REQ-003"]
    assert first.candidate_id == "AUTO-001"
    assert second.candidate_id == "AUTO-002"


def test_suggests_api_automation_for_api_like_cases():
    service = AutomationCandidateService()
    test_case = ManualTestCase(
        test_case_id="TC-006",
        requirement_ids=["REQ-006"],
        module="Order API",
        title="API endpoint returns 200 response",
        steps=["Send request to endpoint.", "Inspect response body."],
        expected_result="Response status code is 200 and payload is valid.",
        priority="High",
        test_type="Regression",
    )

    candidate = service.score_automation_candidate(test_case)

    assert candidate.suggested_automation_type == "api"


def test_suggests_mobile_automation_for_mobile_like_cases():
    service = AutomationCandidateService()
    test_case = ManualTestCase(
        test_case_id="TC-007",
        requirement_ids=["REQ-007"],
        module="Mobile App",
        title="Android app login flow",
        steps=["Open Android app.", "Login with valid credentials."],
        expected_result="User lands on home screen.",
        priority="High",
        test_type="Regression",
    )

    candidate = service.score_automation_candidate(test_case)

    assert candidate.suggested_automation_type == "mobile"


def test_suggests_manual_only_for_subjective_manual_judgment_cases():
    service = AutomationCandidateService()

    candidate = service.score_automation_candidate(_subjective_case())

    assert candidate.suggested_automation_type == "manual_only"


def test_score_automation_candidates_returns_candidates_in_same_input_order():
    service = AutomationCandidateService()
    cases = [_medium_case(), _smoke_case(), _subjective_case()]
    results = [
        TestResult(result_id="RESULT-001", run_id="RUN-001", test_case_id="TC-003", status="Pass"),
        TestResult(result_id="RESULT-002", run_id="RUN-001", test_case_id="TC-001", status="Pass"),
        TestResult(result_id="RESULT-003", run_id="RUN-001", test_case_id="TC-002", status="Skipped"),
    ]

    candidates = service.score_automation_candidates(cases, test_results=results)

    assert [candidate.test_case_id for candidate in candidates] == ["TC-003", "TC-001", "TC-002"]
