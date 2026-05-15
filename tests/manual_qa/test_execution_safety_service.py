from __future__ import annotations

from orchestrator.manual_qa.execution_safety_service import (
    classify_execution_risk,
    create_default_execution_safety_policy,
    create_strict_execution_safety_policy,
    is_base_url_allowed,
    is_script_type_allowed,
)
from orchestrator.manual_qa.models import ExecutionSafetyPolicy, ExecutionTarget


def _relaxed_policy() -> ExecutionSafetyPolicy:
    return ExecutionSafetyPolicy(
        policy_id="EXEC-POLICY-RELAXED",
        name="relaxed",
        allow_execution=True,
        allowed_base_urls=["http://localhost", "http://127.0.0.1"],
        blocked_base_urls=["production", "prod", "live", "payment-live", "real-bank"],
        allowed_script_types=["api", "web_playwright"],
        blocked_script_types=["mobile_appium"],
        allow_write_methods=True,
        allow_delete_methods=True,
        require_human_approval=False,
        require_valid_package=True,
        require_no_critical_todos=True,
        timeout_seconds=30,
        max_scripts_per_run=5,
        dry_run_only=False,
        metadata={},
        created_at="2024-01-16T00:00:00Z",
    )


def _target(**overrides: object) -> ExecutionTarget:
    payload = {
        "target_id": "EXEC-TARGET-001",
        "script_type": "api",
        "draft_id": "API-DRAFT-001",
        "file_name": "test_api_tc_001.py",
        "package_status": "Ready for Review",
        "validation_status": "Valid",
        "base_url": "http://localhost:8000",
        "method": "GET",
        "endpoint_or_page": "/api/orders",
        "has_todos": False,
        "has_critical_todos": False,
        "metadata": {},
    }
    payload.update(overrides)
    return ExecutionTarget(**payload)


def test_default_policy_is_dry_run_only_and_execution_disabled():
    policy = create_default_execution_safety_policy()

    assert policy.allow_execution is False
    assert policy.dry_run_only is True
    assert policy.require_human_approval is True
    assert policy.allow_write_methods is False
    assert policy.allow_delete_methods is False


def test_strict_policy_blocks_non_localhost():
    policy = create_strict_execution_safety_policy()

    assert is_base_url_allowed(policy, "http://localhost:8000") is True
    assert is_base_url_allowed(policy, "https://staging.example.com") is False


def test_base_url_allowlist_works_for_localhost():
    policy = create_default_execution_safety_policy()

    assert is_base_url_allowed(policy, "http://localhost:8000") is True
    assert is_base_url_allowed(policy, "http://127.0.0.1:3000") is True


def test_base_url_blocklist_blocks_production_live_and_payment():
    policy = create_default_execution_safety_policy()

    assert is_base_url_allowed(policy, "https://production.example.com") is False
    assert is_base_url_allowed(policy, "https://live.example.com") is False
    assert is_base_url_allowed(policy, "https://payment-live.example.com") is False


def test_script_type_allowlist_works():
    policy = create_default_execution_safety_policy()

    assert is_script_type_allowed(policy, "api") is True
    assert is_script_type_allowed(policy, "web_playwright") is True
    assert is_script_type_allowed(policy, "mobile_appium") is False


def test_risk_classification_low_medium_high_and_critical():
    relaxed = _relaxed_policy()
    low_target = _target()
    medium_target = _target(has_todos=True)
    high_target = _target(base_url="https://staging.example.com")
    critical_target = _target(base_url="https://production.example.com")

    assert classify_execution_risk(low_target, relaxed) == "Low"
    assert classify_execution_risk(medium_target, relaxed) == "Medium"
    assert classify_execution_risk(high_target, relaxed) == "High"
    assert classify_execution_risk(critical_target, relaxed) == "Critical"
