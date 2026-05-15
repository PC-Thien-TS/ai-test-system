from __future__ import annotations

from orchestrator.manual_qa.models import WebExecutionTarget
from orchestrator.manual_qa.web_execution_safety_service import (
    build_web_evidence_capture_plan,
    classify_web_execution_risk,
    create_default_web_execution_safety_policy,
    create_strict_web_execution_safety_policy,
    is_web_base_url_allowed,
)


def _target(
    *,
    base_url: str = "http://localhost:3000",
    package_status: str = "Ready for Review",
    validation_status: str = "Ready for Review",
    has_todos: bool = False,
    has_critical_todos: bool = False,
    requires_login: bool = False,
    requires_file_upload: bool = False,
    requires_file_download: bool = False,
    has_external_navigation: bool = False,
    has_payment_flow: bool = False,
    has_captcha_or_otp: bool = False,
    metadata: dict | None = None,
) -> WebExecutionTarget:
    return WebExecutionTarget(
        target_id="WEB-TARGET-001",
        script_type="web_playwright",
        draft_id="WEB-DRAFT-001",
        test_case_id="TC-901",
        file_name="test_web_tc_001.py",
        package_status=package_status,
        validation_status=validation_status,
        base_url=base_url,
        page_url="/login",
        has_todos=has_todos,
        has_critical_todos=has_critical_todos,
        requires_login=requires_login,
        requires_file_upload=requires_file_upload,
        requires_file_download=requires_file_download,
        has_external_navigation=has_external_navigation,
        has_payment_flow=has_payment_flow,
        has_captcha_or_otp=has_captcha_or_otp,
        metadata=dict(metadata or {}),
        created_at="2024-01-23T00:00:00Z",
    )


def test_default_policy_is_dry_run_only_and_browser_execution_disabled():
    policy = create_default_web_execution_safety_policy()

    assert policy.allow_browser_execution is False
    assert policy.dry_run_only is True
    assert policy.allowed_browsers == ["chromium"]


def test_strict_policy_blocks_non_localhost():
    policy = create_strict_web_execution_safety_policy()

    assert is_web_base_url_allowed(policy, "http://localhost:3000") is True
    assert is_web_base_url_allowed(policy, "https://staging.example.com") is False


def test_base_url_allowlist_works_for_localhost():
    policy = create_default_web_execution_safety_policy()

    assert is_web_base_url_allowed(policy, "http://localhost:3000") is True
    assert is_web_base_url_allowed(policy, "http://127.0.0.1:8080") is True


def test_base_url_blocklist_blocks_production_live_payment():
    policy = create_default_web_execution_safety_policy()

    assert is_web_base_url_allowed(policy, "https://production.example.com") is False
    assert is_web_base_url_allowed(policy, "https://payment-live.example.com") is False


def test_risk_classification_low_medium_high_critical():
    policy = create_default_web_execution_safety_policy()

    assert classify_web_execution_risk(_target(metadata={"human_approval": True}), policy) == "Low"
    assert classify_web_execution_risk(_target(requires_login=True, metadata={"human_approval": True}), policy) == "Medium"
    assert classify_web_execution_risk(_target(requires_file_upload=True), policy) == "High"
    assert classify_web_execution_risk(_target(base_url="https://production.example.com"), policy) == "Critical"


def test_evidence_capture_plan_uses_policy_flags():
    policy = create_default_web_execution_safety_policy()

    plan = build_web_evidence_capture_plan(policy)

    assert plan["capture_screenshot"] is True
    assert plan["capture_trace"] is True
    assert plan["capture_video"] is False
    assert plan["capture_console_log"] is True
    assert plan["capture_network_log"] is True
