"""Deterministic web execution safety policy helpers for future browser sandbox work."""

from __future__ import annotations

from datetime import datetime, timedelta

from orchestrator.manual_qa.models import WebExecutionSafetyPolicy, WebExecutionTarget


class WebExecutionSafetyService:
    """Build static web safety policies and classify browser execution risk offline."""

    _BASE_TIME = datetime(2024, 1, 22, 0, 0, 0)
    _BLOCKED_KEYWORDS = ("production", "prod", "live", "payment-live", "real-bank")

    def __init__(self) -> None:
        self._next_timestamp_offset = 0

    def create_default_web_execution_safety_policy(
        self,
        *,
        allow_localhost_only: bool = False,
        dry_run_only: bool = True,
        metadata: dict | None = None,
    ) -> WebExecutionSafetyPolicy:
        allowed_base_urls = ["http://localhost", "http://127.0.0.1"]
        if allow_localhost_only:
            allowed_base_urls = ["http://localhost", "http://127.0.0.1"]
        return WebExecutionSafetyPolicy(
            policy_id="WEB-EXEC-POLICY-DEFAULT",
            name="default",
            allow_browser_execution=False,
            dry_run_only=dry_run_only,
            require_human_approval=True,
            require_valid_package=True,
            require_no_critical_todos=True,
            allowed_base_urls=allowed_base_urls,
            blocked_base_urls=list(self._BLOCKED_KEYWORDS),
            allowed_browsers=["chromium"],
            headless_only=True,
            allow_file_upload=False,
            allow_file_download=False,
            allow_external_navigation=False,
            allow_payment_flows=False,
            allow_captcha_or_otp_flows=False,
            timeout_seconds=30,
            max_scripts_per_run=3,
            capture_screenshot=True,
            capture_trace=True,
            capture_video=False,
            capture_console_log=True,
            capture_network_log=True,
            metadata=dict(metadata or {}),
            created_at=self._next_timestamp(),
        )

    def create_strict_web_execution_safety_policy(
        self,
        *,
        dry_run_only: bool = True,
        metadata: dict | None = None,
    ) -> WebExecutionSafetyPolicy:
        return WebExecutionSafetyPolicy(
            policy_id="WEB-EXEC-POLICY-STRICT",
            name="strict",
            allow_browser_execution=False,
            dry_run_only=dry_run_only,
            require_human_approval=True,
            require_valid_package=True,
            require_no_critical_todos=True,
            allowed_base_urls=["http://localhost", "http://127.0.0.1"],
            blocked_base_urls=list(self._BLOCKED_KEYWORDS),
            allowed_browsers=["chromium"],
            headless_only=True,
            allow_file_upload=False,
            allow_file_download=False,
            allow_external_navigation=False,
            allow_payment_flows=False,
            allow_captcha_or_otp_flows=False,
            timeout_seconds=30,
            max_scripts_per_run=3,
            capture_screenshot=True,
            capture_trace=True,
            capture_video=False,
            capture_console_log=True,
            capture_network_log=True,
            metadata={"localhost_only": True, **dict(metadata or {})},
            created_at=self._next_timestamp(),
        )

    def is_web_base_url_allowed(
        self,
        policy: WebExecutionSafetyPolicy,
        base_url: str,
    ) -> bool:
        normalized = str(base_url or "").strip().lower()
        if not normalized:
            return False
        if self._contains_blocked_keyword(normalized):
            return False
        allowed_prefixes = [item.lower() for item in policy.allowed_base_urls]
        if allowed_prefixes:
            return any(normalized.startswith(prefix) for prefix in allowed_prefixes)
        return True

    def classify_web_execution_risk(
        self,
        target: WebExecutionTarget,
        policy: WebExecutionSafetyPolicy,
    ) -> str:
        base_url = str(target.base_url or "")
        package_status = str(target.package_status or "")
        validation_status = str(target.validation_status or "")

        if self._contains_blocked_keyword(base_url):
            return "Critical"
        if package_status == "Invalid" or validation_status == "Invalid":
            return "Critical"
        if target.has_captcha_or_otp and not policy.allow_captcha_or_otp_flows:
            return "Critical"
        if target.has_payment_flow and not policy.allow_payment_flows:
            return "Critical"
        if target.metadata.get("browser_execution_requested") and not policy.allow_browser_execution:
            return "Critical"

        if target.requires_file_upload and not policy.allow_file_upload:
            return "High"
        if target.requires_file_download and not policy.allow_file_download:
            return "High"
        if target.has_external_navigation and not policy.allow_external_navigation:
            return "High"
        if package_status == "Needs Attention" or validation_status == "Needs Attention":
            return "High"
        if policy.require_human_approval and not bool(target.metadata.get("human_approval", False)):
            return "High"

        if target.requires_login or target.has_todos:
            return "Medium"

        return "Low"

    def build_web_evidence_capture_plan(
        self,
        policy: WebExecutionSafetyPolicy,
    ) -> dict[str, object]:
        return {
            "capture_screenshot": policy.capture_screenshot,
            "capture_trace": policy.capture_trace,
            "capture_video": policy.capture_video,
            "capture_console_log": policy.capture_console_log,
            "capture_network_log": policy.capture_network_log,
            "allowed_browsers": list(policy.allowed_browsers),
            "headless_only": policy.headless_only,
            "sandbox_only": True,
        }

    def _contains_blocked_keyword(self, value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return any(keyword in normalized for keyword in self._BLOCKED_KEYWORDS)

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


def create_default_web_execution_safety_policy(
    *,
    allow_localhost_only: bool = False,
    dry_run_only: bool = True,
    metadata: dict | None = None,
) -> WebExecutionSafetyPolicy:
    return WebExecutionSafetyService().create_default_web_execution_safety_policy(
        allow_localhost_only=allow_localhost_only,
        dry_run_only=dry_run_only,
        metadata=metadata,
    )


def create_strict_web_execution_safety_policy(
    *,
    dry_run_only: bool = True,
    metadata: dict | None = None,
) -> WebExecutionSafetyPolicy:
    return WebExecutionSafetyService().create_strict_web_execution_safety_policy(
        dry_run_only=dry_run_only,
        metadata=metadata,
    )


def is_web_base_url_allowed(
    policy: WebExecutionSafetyPolicy,
    base_url: str,
) -> bool:
    return WebExecutionSafetyService().is_web_base_url_allowed(policy, base_url)


def classify_web_execution_risk(
    target: WebExecutionTarget,
    policy: WebExecutionSafetyPolicy,
) -> str:
    return WebExecutionSafetyService().classify_web_execution_risk(target, policy)


def build_web_evidence_capture_plan(
    policy: WebExecutionSafetyPolicy,
) -> dict[str, object]:
    return WebExecutionSafetyService().build_web_evidence_capture_plan(policy)
