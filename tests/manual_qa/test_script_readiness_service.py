from __future__ import annotations

from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.models import ManualTestCase
from orchestrator.manual_qa.script_readiness_service import ScriptReadinessService


def test_clear_api_test_case_with_endpoint_status_code_is_ready_or_high_score():
    service = ScriptReadinessService()
    test_case = ManualTestCase(
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Order API",
        title="Create order endpoint returns status code 201",
        steps=[
            "Send POST request to /api/orders with valid payload.",
            "Verify response status code is 201.",
        ],
        expected_result="Response status code is 201 and order is created.",
        priority="High",
        metadata={"test_data": "valid order payload"},
    )

    readiness = service.analyze_script_readiness(test_case)

    assert readiness.target_type == "api"
    assert readiness.readiness_score >= 75
    assert readiness.readiness_status in {"Ready", "Needs More Data"}


def test_vague_subjective_visual_case_is_not_suitable():
    service = ScriptReadinessService()
    test_case = ManualTestCase(
        test_case_id="TC-002",
        requirement_ids=["REQ-002"],
        module="Checkout UI",
        title="Checkout page visual review looks good",
        steps=["Open checkout page and review manually."],
        expected_result="Looks good and gives the right UX feeling.",
        priority="Medium",
    )

    readiness = service.analyze_script_readiness(test_case)

    assert readiness.target_type == "manual_only"
    assert readiness.readiness_status == "Not Suitable"
    assert any(gap.gap_type == "manual_judgment_required" for gap in readiness.gaps)


def test_web_ui_case_without_selector_hint_creates_missing_selector_gap():
    service = ScriptReadinessService()
    test_case = ManualTestCase(
        test_case_id="TC-003",
        requirement_ids=["REQ-003"],
        module="Login UI",
        title="Login page submit flow",
        steps=["Open login page.", "Click login and verify successful navigation."],
        expected_result="User lands on the dashboard.",
    )

    readiness = service.analyze_script_readiness(test_case)

    assert readiness.target_type == "web_ui"
    assert any(gap.gap_type == "missing_selector_hint" for gap in readiness.gaps)


def test_api_case_without_endpoint_hint_creates_missing_endpoint_gap():
    service = ScriptReadinessService()
    test_case = ManualTestCase(
        test_case_id="TC-004",
        requirement_ids=["REQ-004"],
        module="API",
        title="Token API behavior",
        steps=["Send authenticated request.", "Verify API response."],
        expected_result="API returns valid data.",
    )

    readiness = service.analyze_script_readiness(test_case)

    assert readiness.target_type == "api"
    assert any(gap.gap_type == "missing_endpoint_hint" for gap in readiness.gaps)


def test_missing_expected_result_creates_high_severity_gap():
    service = ScriptReadinessService()
    test_case = ManualTestCase(
        test_case_id="TC-005",
        requirement_ids=["REQ-005"],
        module="Search",
        title="Search query flow",
        steps=["Open search page.", "Submit query for shoes."],
        expected_result="",
    )

    readiness = service.analyze_script_readiness(test_case)

    gap = next(gap for gap in readiness.gaps if gap.gap_type == "missing_expected_result")
    assert gap.severity == "High"


def test_automation_candidate_should_automate_increases_score():
    readiness_service = ScriptReadinessService()
    candidate_service = AutomationCandidateService()
    test_case = ManualTestCase(
        test_case_id="TC-006",
        requirement_ids=["REQ-006"],
        module="Search API",
        title="Regression API search results",
        steps=["Send GET request to /api/search?q=boots.", "Verify status code is 200."],
        expected_result="Response status code is 200 and matching results are returned.",
        priority="High",
        test_type="Regression",
        metadata={"test_data": "query=boots"},
    )

    without_candidate = readiness_service.analyze_script_readiness(test_case)
    candidate = candidate_service.score_automation_candidate(test_case)
    with_candidate = readiness_service.analyze_script_readiness(test_case, automation_candidate=candidate)

    assert candidate.recommendation == "Should Automate"
    assert with_candidate.readiness_score >= without_candidate.readiness_score


def test_batch_analysis_preserves_input_order():
    service = ScriptReadinessService()
    test_cases = [
        ManualTestCase(test_case_id="TC-010", requirement_ids=["REQ-010"], module="API", title="A", steps=["GET /api/a"], expected_result="200"),
        ManualTestCase(test_case_id="TC-011", requirement_ids=["REQ-011"], module="UI", title="B", steps=["Open page"], expected_result="Dashboard appears"),
    ]

    results = service.analyze_script_readiness_batch(test_cases)

    assert [item.test_case_id for item in results] == ["TC-010", "TC-011"]


def test_target_type_classification_works_for_api_web_ui_mobile_manual_only():
    service = ScriptReadinessService()
    api = service.analyze_script_readiness(
        ManualTestCase("TC-020", ["REQ-020"], "API", "Endpoint flow", steps=["GET /api/orders"], expected_result="200")
    )
    web_ui = service.analyze_script_readiness(
        ManualTestCase("TC-021", ["REQ-021"], "Portal", "Login page button flow", steps=["Open login page", "Click submit button"], expected_result="Dashboard appears")
    )
    mobile = service.analyze_script_readiness(
        ManualTestCase("TC-022", ["REQ-022"], "Mobile App", "Android permission flow", steps=["Open mobile app", "Tap allow permission"], expected_result="Permission granted")
    )
    manual_only = service.analyze_script_readiness(
        ManualTestCase("TC-023", ["REQ-023"], "Checkout", "Manual observation review", steps=["Review screen manually"], expected_result="Looks good visually")
    )

    assert api.target_type == "api"
    assert web_ui.target_type == "web_ui"
    assert mobile.target_type == "mobile"
    assert manual_only.target_type == "manual_only"


def test_no_script_is_generated():
    service = ScriptReadinessService()
    readiness = service.analyze_script_readiness(
        ManualTestCase(
            test_case_id="TC-030",
            requirement_ids=["REQ-030"],
            module="Integration",
            title="Workflow smoke",
            steps=["Run workflow"],
            expected_result="Workflow completes",
        )
    )

    assert not hasattr(readiness, "script")
    assert not hasattr(readiness, "script_content")
