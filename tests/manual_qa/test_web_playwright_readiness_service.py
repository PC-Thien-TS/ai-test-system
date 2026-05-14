from __future__ import annotations

from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.models import ManualTestCase, ScriptGenerationReadiness
from orchestrator.manual_qa.web_playwright_readiness_service import WebPlaywrightReadinessService


def _web_case(
    *,
    test_case_id: str = "TC-001",
    title: str = "Login page submit flow",
    steps: list[str] | None = None,
    expected_result: str = "User should see dashboard and URL contains /dashboard.",
    metadata: dict | None = None,
) -> ManualTestCase:
    return ManualTestCase(
        test_case_id=test_case_id,
        requirement_ids=["REQ-001"],
        module="Portal UI",
        title=title,
        steps=steps or [
            "Navigate to /login page.",
            "Fill username field label email.",
            "Fill password field label password.",
            "Click submit button text sign in.",
        ],
        expected_result=expected_result,
        metadata=metadata or {},
    )


def test_clear_web_ui_case_with_url_selectors_actions_assertions_is_ready_or_high_score():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        steps=[
            "Navigate to /login page.",
            "Fill data-testid=login-email with valid email.",
            "Fill data-testid=login-password with valid password.",
            "Click button text sign in.",
        ],
        expected_result="User should see dashboard and URL contains /dashboard and element visible success message.",
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert readiness.readiness_score >= 75
    assert readiness.readiness_status in {"Ready", "Needs More Data"}
    assert readiness.page_url == "/login"


def test_web_ui_case_without_selector_hints_creates_missing_selector_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        steps=["Navigate to /login page.", "Click submit.", "Fill credentials.", "Submit form."],
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert any(gap.gap_type == "missing_selector_hints" for gap in readiness.gaps)


def test_web_ui_case_without_page_url_creates_missing_page_url_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        steps=[
            "Open login page in browser.",
            "Fill data-testid=login-email with valid email.",
            "Click button text sign in.",
        ],
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert any(gap.gap_type == "missing_page_url" for gap in readiness.gaps)


def test_missing_assertion_creates_high_severity_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(expected_result="")

    readiness = service.analyze_web_playwright_readiness(test_case)

    gap = next(gap for gap in readiness.gaps if gap.gap_type == "missing_assertion")
    assert gap.severity == "High"


def test_login_session_dependency_creates_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        title="Authenticated dashboard session flow",
        expected_result="Dashboard appears after authenticated session.",
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert any(gap.gap_type == "login_session_dependency" for gap in readiness.gaps)


def test_captcha_otp_manual_approval_creates_not_suitable_or_critical_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        title="Checkout captcha and OTP approval flow",
        steps=[
            "Navigate to /checkout.",
            "Fill data-testid=card-number.",
            "Click pay now button.",
            "Enter OTP from bank approval screen.",
        ],
        expected_result="Payment success message appears after captcha and OTP approval.",
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert readiness.readiness_status == "Not Suitable"
    assert any(gap.gap_type == "external_blocker_dependency" for gap in readiness.gaps)


def test_visual_judgment_case_is_not_suitable():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        title="Homepage visual review looks good",
        expected_result="Looks good and gives the right UX feeling.",
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert readiness.readiness_status == "Not Suitable"
    assert any(gap.gap_type == "visual_manual_judgment" for gap in readiness.gaps)


def test_dynamic_flaky_ui_creates_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        title="Dynamic dashboard animation flow",
        expected_result="Dashboard displays refreshed cards after animation completes.",
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert any(gap.gap_type == "dynamic_flaky_ui_dependency" for gap in readiness.gaps)


def test_file_upload_download_creates_gap():
    service = WebPlaywrightReadinessService()
    test_case = _web_case(
        title="Document upload form flow",
        steps=[
            "Navigate to /documents/upload.",
            "Fill data-testid=file-name.",
            "Upload file via data-testid=file-input.",
            "Click submit button text upload.",
        ],
        expected_result="Success message appears and download file link displays.",
    )

    readiness = service.analyze_web_playwright_readiness(test_case)

    assert any(gap.gap_type == "file_upload_download_complexity" for gap in readiness.gaps)


def test_script_generation_readiness_ready_increases_score():
    service = WebPlaywrightReadinessService()
    test_case = _web_case()
    without_upstream = service.analyze_web_playwright_readiness(test_case)
    upstream = ScriptGenerationReadiness(
        readiness_id="READ-001",
        test_case_id=test_case.test_case_id,
        module=test_case.module,
        title=test_case.title,
        target_type="web_ui",
        readiness_status="Ready",
        readiness_score=80,
    )
    with_upstream = WebPlaywrightReadinessService().analyze_web_playwright_readiness(
        test_case,
        script_readiness=upstream,
    )

    assert with_upstream.readiness_score >= without_upstream.readiness_score


def test_automation_candidate_should_automate_increases_score():
    candidate_service = AutomationCandidateService()
    test_case = _web_case()
    candidate = candidate_service.score_automation_candidate(
        ManualTestCase(
            test_case_id=test_case.test_case_id,
            requirement_ids=test_case.requirement_ids,
            module=test_case.module,
            title=test_case.title,
            steps=test_case.steps,
            expected_result=test_case.expected_result,
            priority="High",
            test_type="Regression",
        )
    )
    without_candidate = WebPlaywrightReadinessService().analyze_web_playwright_readiness(test_case)
    with_candidate = WebPlaywrightReadinessService().analyze_web_playwright_readiness(
        test_case,
        automation_candidate=candidate,
    )

    assert candidate.recommendation == "Should Automate"
    assert with_candidate.readiness_score >= without_candidate.readiness_score


def test_batch_analysis_preserves_input_order():
    service = WebPlaywrightReadinessService()
    cases = [
        _web_case(test_case_id="TC-010"),
        _web_case(test_case_id="TC-011", title="Dashboard filter flow"),
    ]

    results = service.analyze_web_playwright_readiness_batch(cases)

    assert [item.test_case_id for item in results] == ["TC-010", "TC-011"]


def test_no_playwright_script_is_generated_and_no_browser_automation_is_executed():
    service = WebPlaywrightReadinessService()
    readiness = service.analyze_web_playwright_readiness(_web_case())

    assert not hasattr(readiness, "script_content")
    assert not hasattr(readiness, "playwright_code")
