"""Deterministic safety policy helpers for future script sandbox work."""

from __future__ import annotations

from datetime import datetime, timedelta

from orchestrator.manual_qa.models import ExecutionSafetyPolicy, ExecutionTarget


class ExecutionSafetyService:
    """Build static safety policies and classify execution risk offline."""

    _BASE_TIME = datetime(2024, 1, 16, 0, 0, 0)
    _BLOCKED_KEYWORDS = ("production", "prod", "live", "payment-live", "real-bank")
    _WRITE_METHODS = {"POST", "PUT", "PATCH"}
    _DELETE_METHODS = {"DELETE"}

    def __init__(self) -> None:
        self._next_timestamp_offset = 0

    def create_default_execution_safety_policy(
        self,
        *,
        allow_localhost_only: bool = False,
        dry_run_only: bool = True,
        metadata: dict | None = None,
    ) -> ExecutionSafetyPolicy:
        allowed_base_urls = ["http://localhost", "http://127.0.0.1"]
        if allow_localhost_only:
            allowed_base_urls = ["http://localhost", "http://127.0.0.1"]
        return ExecutionSafetyPolicy(
            policy_id="EXEC-POLICY-DEFAULT",
            name="default",
            allow_execution=False,
            allowed_base_urls=allowed_base_urls,
            blocked_base_urls=list(self._BLOCKED_KEYWORDS),
            allowed_script_types=["api", "web_playwright"],
            blocked_script_types=["mobile_appium"],
            allow_write_methods=False,
            allow_delete_methods=False,
            require_human_approval=True,
            require_valid_package=True,
            require_no_critical_todos=True,
            timeout_seconds=30,
            max_scripts_per_run=5,
            dry_run_only=dry_run_only,
            metadata=dict(metadata or {}),
            created_at=self._next_timestamp(),
        )

    def create_strict_execution_safety_policy(
        self,
        *,
        dry_run_only: bool = True,
        metadata: dict | None = None,
    ) -> ExecutionSafetyPolicy:
        return ExecutionSafetyPolicy(
            policy_id="EXEC-POLICY-STRICT",
            name="strict",
            allow_execution=False,
            allowed_base_urls=["http://localhost", "http://127.0.0.1"],
            blocked_base_urls=list(self._BLOCKED_KEYWORDS),
            allowed_script_types=["api", "web_playwright"],
            blocked_script_types=["mobile_appium"],
            allow_write_methods=False,
            allow_delete_methods=False,
            require_human_approval=True,
            require_valid_package=True,
            require_no_critical_todos=True,
            timeout_seconds=30,
            max_scripts_per_run=5,
            dry_run_only=dry_run_only,
            metadata={"localhost_only": True, **dict(metadata or {})},
            created_at=self._next_timestamp(),
        )

    def classify_execution_risk(
        self,
        target: ExecutionTarget,
        policy: ExecutionSafetyPolicy,
    ) -> str:
        method = str(target.method or "").upper()
        package_status = str(target.package_status or "")
        validation_status = str(target.validation_status or "")
        base_url = str(target.base_url or "")

        if not self.is_script_type_allowed(policy, target.script_type):
            return "Critical"
        if self._contains_blocked_keyword(base_url):
            return "Critical"
        if method in self._DELETE_METHODS and not policy.allow_delete_methods:
            return "Critical"
        if package_status == "Invalid" or validation_status == "Invalid":
            return "Critical"
        if target.script_type == "web_playwright" and target.metadata.get("browser_execution_requested") and not policy.allow_execution:
            return "Critical"

        if (
            method in self._WRITE_METHODS
            and not policy.allow_write_methods
        ):
            return "High"
        if base_url and not self.is_base_url_allowed(policy, base_url):
            return "High"
        if policy.require_human_approval and not bool(target.metadata.get("human_approval", False)):
            return "High"
        if package_status == "Needs Attention" or validation_status == "Needs Attention":
            return "High"

        if target.has_todos or target.has_critical_todos:
            return "Medium"

        return "Low"

    def is_base_url_allowed(
        self,
        policy: ExecutionSafetyPolicy,
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

    def is_script_type_allowed(
        self,
        policy: ExecutionSafetyPolicy,
        script_type: str,
    ) -> bool:
        normalized = str(script_type or "").strip().lower()
        if normalized in {item.lower() for item in policy.blocked_script_types}:
            return False
        allowed = {item.lower() for item in policy.allowed_script_types}
        if allowed:
            return normalized in allowed
        return True

    def _contains_blocked_keyword(self, value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return any(keyword in normalized for keyword in self._BLOCKED_KEYWORDS)

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


def create_default_execution_safety_policy(
    *,
    allow_localhost_only: bool = False,
    dry_run_only: bool = True,
    metadata: dict | None = None,
) -> ExecutionSafetyPolicy:
    """Convenience wrapper for the default static execution safety policy."""

    return ExecutionSafetyService().create_default_execution_safety_policy(
        allow_localhost_only=allow_localhost_only,
        dry_run_only=dry_run_only,
        metadata=metadata,
    )


def create_strict_execution_safety_policy(
    *,
    dry_run_only: bool = True,
    metadata: dict | None = None,
) -> ExecutionSafetyPolicy:
    """Convenience wrapper for the strict static execution safety policy."""

    return ExecutionSafetyService().create_strict_execution_safety_policy(
        dry_run_only=dry_run_only,
        metadata=metadata,
    )


def classify_execution_risk(
    target: ExecutionTarget,
    policy: ExecutionSafetyPolicy,
) -> str:
    """Convenience wrapper for static risk classification."""

    return ExecutionSafetyService().classify_execution_risk(target, policy)


def is_base_url_allowed(
    policy: ExecutionSafetyPolicy,
    base_url: str,
) -> bool:
    """Convenience wrapper for base URL allow/block checks."""

    return ExecutionSafetyService().is_base_url_allowed(policy, base_url)


def is_script_type_allowed(
    policy: ExecutionSafetyPolicy,
    script_type: str,
) -> bool:
    """Convenience wrapper for script type allow/block checks."""

    return ExecutionSafetyService().is_script_type_allowed(policy, script_type)
