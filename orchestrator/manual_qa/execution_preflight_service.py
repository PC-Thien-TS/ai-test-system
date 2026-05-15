"""Static execution preflight planning without running draft scripts."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from orchestrator.manual_qa.execution_safety_service import (
    ExecutionSafetyService,
)
from orchestrator.manual_qa.models import (
    ExecutionPlan,
    ExecutionPreflightIssue,
    ExecutionPreflightResult,
    ExecutionSafetyPolicy,
    ExecutionTarget,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class ExecutionPreflightService:
    """Build deterministic offline execution plans from draft metadata."""

    _BASE_TIME = datetime(2024, 1, 17, 0, 0, 0)
    _CRITICAL_TODO_TOKENS = (
        "TODO_ENDPOINT",
        "TODO_PAGE_URL",
        "TODO_SELECTOR",
        '"TODO": "payload"',
        "TODO_TEXT",
    )
    _TODO_PATTERNS = (
        "TODO_ENDPOINT",
        "TODO_PAGE_URL",
        "TODO_SELECTOR",
        "TODO_TEXT",
        "TODO_OPTION",
        "TODO_FILE",
        "TODO_VALUE",
        '"TODO": "payload"',
    )
    _WRITE_METHODS = {"POST", "PUT", "PATCH"}
    _DELETE_METHODS = {"DELETE"}

    def __init__(self) -> None:
        self._workspace_service = ManualQAWorkspaceService()
        self._safety_service = ExecutionSafetyService()
        self._next_target_number = 1
        self._next_issue_number = 1
        self._next_preflight_number = 1
        self._next_timestamp_offset = 0

    def build_execution_plan(
        self,
        workspace_path: str | Path,
        targets: Sequence[ExecutionTarget],
        *,
        policy: ExecutionSafetyPolicy | None = None,
        metadata: dict | None = None,
    ) -> ExecutionPlan:
        safety_policy = policy or self._safety_service.create_default_execution_safety_policy()
        results = [self.preflight_execution_target(target, policy=safety_policy) for target in targets]
        overall_decision = self._derive_overall_decision(results, safety_policy)
        missing_group_types = self._missing_group_types(targets)
        if not targets:
            overall_decision = "Missing Draft Packages"

        plan = ExecutionPlan(
            plan_id="EXEC-PLAN-001",
            workspace_path=str(Path(workspace_path)),
            policy=safety_policy,
            targets=list(targets),
            preflight_results=results,
            total_targets=len(targets),
            allowed_count=len([item for item in results if item.decision == "Allowed"]),
            blocked_count=len([item for item in results if item.decision == "Blocked"]),
            needs_approval_count=len(
                [item for item in results if item.decision in {"Needs Human Approval", "Dry Run Only"}]
            ),
            dry_run_only=safety_policy.dry_run_only,
            overall_decision=overall_decision,
            recommended_next_step=self._recommended_next_step(overall_decision),
            metadata={
                "missing_group_types": missing_group_types,
                "risk_levels": [item.risk_level for item in results],
                "available_script_types": sorted({target.script_type for target in targets}),
                **dict(metadata or {}),
            },
            created_at=self._next_timestamp(),
        )
        return plan

    def build_execution_plan_from_workspace(
        self,
        workspace_path: str | Path,
        *,
        policy: ExecutionSafetyPolicy | None = None,
        metadata: dict | None = None,
    ) -> ExecutionPlan:
        workspace = Path(workspace_path)
        safety_policy = policy or self._safety_service.create_default_execution_safety_policy()
        targets = self._discover_targets(workspace)
        return self.build_execution_plan(
            workspace,
            targets,
            policy=safety_policy,
            metadata=metadata,
        )

    def preflight_execution_target(
        self,
        target: ExecutionTarget,
        *,
        policy: ExecutionSafetyPolicy | None = None,
    ) -> ExecutionPreflightResult:
        safety_policy = policy or self._safety_service.create_default_execution_safety_policy()
        issues: list[ExecutionPreflightIssue] = []

        if target.package_status == "Missing":
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="missing_draft_package",
                    message="Draft package metadata is missing for this target.",
                    recommendation="Generate and validate the package manifest before sandbox planning.",
                )
            )
        if target.package_status == "Invalid" or target.validation_status == "Invalid":
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="invalid_package_manifest",
                    message="The target belongs to an invalid package or invalid validation result.",
                    recommendation="Fix invalid package artifacts before any sandbox work continues.",
                )
            )
        elif target.package_status == "Needs Attention" or target.validation_status == "Needs Attention":
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="package_needs_attention",
                    message="The target package or validation metadata still contains warnings or TODOs.",
                    recommendation="Resolve package warnings and TODO markers before sandbox prototyping.",
                )
            )

        if not self._safety_service.is_script_type_allowed(safety_policy, target.script_type):
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="script_type_not_allowed",
                    message=f"Script type '{target.script_type}' is blocked by policy.",
                    recommendation="Use an allowed script type or update policy intentionally.",
                )
            )

        if not safety_policy.allow_execution:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="execution_disabled_by_policy",
                    message="Execution is disabled by the current safety policy.",
                    recommendation="Keep this plan static until a later sandbox phase enables execution safely.",
                )
            )

        if safety_policy.dry_run_only:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="dry_run_only_mode",
                    message="The current policy only permits dry-run planning.",
                    recommendation="Retain dry-run mode for Phase 8B and defer real execution to a later phase.",
                )
            )

        if safety_policy.require_human_approval and not bool(target.metadata.get("human_approval", False)):
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="missing_human_approval",
                    message="Human approval is required before any execution could be considered.",
                    recommendation="Require explicit human approval in a future sandbox workflow.",
                )
            )

        if target.base_url and not self._safety_service.is_base_url_allowed(safety_policy, target.base_url):
            issue_type = "blocked_base_url" if self._contains_blocked_keyword(target.base_url) else "non_local_base_url"
            severity = "Critical" if issue_type == "blocked_base_url" else "High"
            issues.append(
                self._issue(
                    target.target_id,
                    severity=severity,
                    issue_type=issue_type,
                    message=f"Base URL '{target.base_url}' is not allowed by policy.",
                    recommendation="Use localhost-only targets for sandbox prototyping.",
                )
            )
        elif not target.base_url:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="missing_base_url",
                    message="No base URL could be inferred from the draft metadata.",
                    recommendation="Add or preserve explicit localhost defaults in draft metadata before sandbox work.",
                )
            )

        method = str(target.method or "").upper()
        if method in self._DELETE_METHODS and not safety_policy.allow_delete_methods:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="delete_method_blocked",
                    message="DELETE methods are blocked by policy.",
                    recommendation="Keep DELETE-style targets blocked until stricter sandbox controls exist.",
                )
            )
        elif method in self._WRITE_METHODS and not safety_policy.allow_write_methods:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="write_method_not_allowed",
                    message=f"{method} is treated as a write method and is blocked by policy.",
                    recommendation="Restrict sandbox prototyping to read-only or explicitly approved write scenarios.",
                )
            )

        if target.has_critical_todos and safety_policy.require_no_critical_todos:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="critical_todo_present",
                    message="Critical TODO placeholders remain in endpoint, page, selector, or payload details.",
                    recommendation="Replace critical TODO placeholders before sandbox prototyping.",
                )
            )
        elif target.has_todos:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="todo_present",
                    message="Draft TODO placeholders remain in the target metadata or script content.",
                    recommendation="Refine draft placeholders before treating the target as sandbox-ready.",
                )
            )

        risk_level = self._safety_service.classify_execution_risk(target, safety_policy)
        decision = self._derive_decision(issues, safety_policy)

        result = ExecutionPreflightResult(
            preflight_id=f"EXEC-PREFLIGHT-{self._next_preflight_number:03d}",
            target_id=target.target_id,
            script_type=target.script_type,
            decision=decision,
            is_allowed=decision == "Allowed",
            issues=issues,
            risk_level=risk_level,
            recommended_action=self._recommended_action(decision),
            metadata={
                "package_status": target.package_status,
                "validation_status": target.validation_status,
                "base_url": target.base_url,
                "method": target.method,
            },
            created_at=self._next_timestamp(),
        )
        self._next_preflight_number += 1
        return result

    def _discover_targets(self, workspace: Path) -> list[ExecutionTarget]:
        targets: list[ExecutionTarget] = []
        targets.extend(self._discover_api_targets(workspace))
        targets.extend(self._discover_web_targets(workspace))
        return targets

    def _discover_api_targets(self, workspace: Path) -> list[ExecutionTarget]:
        base_dir = workspace / "script_drafts" / "api"
        manifest = self._read_json_dict(base_dir / "api_script_package_manifest.json")
        validations = self._read_json_list(base_dir / "api_script_validation.json")
        drafts = self._read_json_list(base_dir / "api_script_drafts.json")
        validation_by_draft_id = {
            str(item.get("draft_id", "")): item for item in validations if isinstance(item, dict)
        }
        package_status = str(manifest.get("status", "Missing")) if manifest else "Missing"

        targets: list[ExecutionTarget] = []
        for draft in drafts:
            script_content = str(draft.get("script_content", ""))
            metadata = draft.get("metadata", {}) if isinstance(draft.get("metadata"), dict) else {}
            validation = validation_by_draft_id.get(str(draft.get("draft_id", "")), {})
            endpoint = str(metadata.get("endpoint", "") or self._extract_api_endpoint(script_content))
            base_url = self._extract_base_url(script_content)
            method = str(metadata.get("http_method", "") or self._extract_api_method(script_content) or "GET").upper()
            has_todos = self._has_todos(script_content, metadata, endpoint)
            has_critical_todos = self._has_critical_todos(script_content, metadata, endpoint)
            validation_status = self._validation_status_for_api(validation)
            targets.append(
                ExecutionTarget(
                    target_id=f"EXEC-TARGET-{self._next_target_number:03d}",
                    script_type="api",
                    draft_id=str(draft.get("draft_id", "")),
                    file_name=str(draft.get("file_name", "")),
                    package_status=package_status,
                    validation_status=validation_status,
                    base_url=base_url,
                    method=method,
                    endpoint_or_page=endpoint,
                    has_todos=has_todos,
                    has_critical_todos=has_critical_todos,
                    metadata={
                        "source": "api",
                        "browser_execution_requested": False,
                        "draft_warning_count": len(draft.get("warnings", [])) if isinstance(draft.get("warnings"), list) else 0,
                        "manifest_path": "script_drafts/api/api_script_package_manifest.json",
                        "validation_path": "script_drafts/api/api_script_validation.json",
                        "drafts_path": "script_drafts/api/api_script_drafts.json",
                    },
                )
            )
            self._next_target_number += 1
        return targets

    def _discover_web_targets(self, workspace: Path) -> list[ExecutionTarget]:
        base_dir = workspace / "script_drafts" / "web_playwright"
        manifest = self._read_json_dict(base_dir / "web_playwright_package_manifest.json")
        validations = self._read_json_list(base_dir / "web_playwright_validation.json")
        drafts = self._read_json_list(base_dir / "web_playwright_script_drafts.json")
        validation_by_draft_id = {
            str(item.get("draft_id", "")): item for item in validations if isinstance(item, dict)
        }
        package_status = str(manifest.get("status", "Missing")) if manifest else "Missing"

        targets: list[ExecutionTarget] = []
        for draft in drafts:
            script_content = str(draft.get("script_content", ""))
            metadata = draft.get("metadata", {}) if isinstance(draft.get("metadata"), dict) else {}
            validation = validation_by_draft_id.get(str(draft.get("draft_id", "")), {})
            endpoint_or_page = str(metadata.get("page_url", "") or self._extract_web_page(script_content))
            base_url = self._extract_base_url(script_content)
            has_todos = self._has_todos(script_content, metadata, endpoint_or_page)
            has_critical_todos = self._has_critical_todos(script_content, metadata, endpoint_or_page)
            validation_status = self._validation_status_for_web(validation)
            targets.append(
                ExecutionTarget(
                    target_id=f"EXEC-TARGET-{self._next_target_number:03d}",
                    script_type="web_playwright",
                    draft_id=str(draft.get("draft_id", "")),
                    file_name=str(draft.get("file_name", "")),
                    package_status=package_status,
                    validation_status=validation_status,
                    base_url=base_url,
                    method="BROWSER",
                    endpoint_or_page=endpoint_or_page,
                    has_todos=has_todos,
                    has_critical_todos=has_critical_todos,
                    metadata={
                        "source": "web_playwright",
                        "browser_execution_requested": True,
                        "draft_warning_count": len(draft.get("warnings", [])) if isinstance(draft.get("warnings"), list) else 0,
                        "manifest_path": "script_drafts/web_playwright/web_playwright_package_manifest.json",
                        "validation_path": "script_drafts/web_playwright/web_playwright_validation.json",
                        "drafts_path": "script_drafts/web_playwright/web_playwright_script_drafts.json",
                    },
                )
            )
            self._next_target_number += 1
        return targets

    def _derive_decision(
        self,
        issues: Sequence[ExecutionPreflightIssue],
        policy: ExecutionSafetyPolicy,
    ) -> str:
        if any(issue.severity == "Critical" for issue in issues):
            return "Blocked"
        if policy.dry_run_only:
            return "Dry Run Only"
        if policy.require_human_approval and any(issue.issue_type == "missing_human_approval" for issue in issues):
            return "Needs Human Approval"
        if any(issue.severity == "High" for issue in issues):
            return "Needs Human Approval"
        return "Allowed"

    def _derive_overall_decision(
        self,
        results: Sequence[ExecutionPreflightResult],
        policy: ExecutionSafetyPolicy,
    ) -> str:
        if not results:
            return "Missing Draft Packages"
        if any(item.decision == "Blocked" or item.risk_level == "Critical" for item in results):
            return "Blocked"
        if any(item.decision in {"Needs Human Approval", "Dry Run Only"} for item in results):
            return "Needs Attention"
        if policy.dry_run_only or any(item.risk_level in {"Medium", "High"} for item in results):
            return "Needs Attention"
        return "Ready for Sandbox Design Review"

    def _recommended_next_step(self, decision: str) -> str:
        if decision == "Ready for Sandbox Design Review":
            return "Review the static preflight plan before Phase 8C sandbox prototyping"
        if decision == "Needs Attention":
            return "Review policy issues, TODOs, and approval requirements before sandbox prototyping"
        if decision == "Blocked":
            return "Resolve blocked targets and unsafe conditions before sandbox design review"
        return "Generate and validate draft packages before preflight planning"

    def _recommended_action(self, decision: str) -> str:
        if decision == "Allowed":
            return "Keep the target in the sandbox candidate list for a future execution phase."
        if decision == "Needs Human Approval":
            return "Require explicit human approval before considering execution."
        if decision == "Dry Run Only":
            return "Keep this target in dry-run planning mode only."
        return "Block this target until unsafe conditions are resolved."

    def _missing_group_types(self, targets: Sequence[ExecutionTarget]) -> list[str]:
        available = {target.script_type for target in targets}
        expected = {"api", "web_playwright"}
        return sorted(expected - available)

    def _validation_status_for_api(self, validation: dict[str, Any]) -> str:
        if not validation:
            return "Missing"
        if not bool(validation.get("is_valid", False)):
            return "Invalid"
        if bool(validation.get("has_todo_endpoint")) or bool(validation.get("has_todo_payload")):
            return "Needs Attention"
        issues = validation.get("issues", [])
        if any(str(item.get("severity", "")).strip().lower() == "warning" for item in issues if isinstance(item, dict)):
            return "Needs Attention"
        return "Valid"

    def _validation_status_for_web(self, validation: dict[str, Any]) -> str:
        if not validation:
            return "Missing"
        if not bool(validation.get("is_valid", False)):
            return "Invalid"
        if any(
            bool(validation.get(flag))
            for flag in ("has_todo_page_url", "has_todo_selector", "has_todo_assertion")
        ):
            return "Needs Attention"
        issues = validation.get("issues", [])
        if any(str(item.get("severity", "")).strip().lower() == "warning" for item in issues if isinstance(item, dict)):
            return "Needs Attention"
        return "Valid"

    def _has_todos(self, script_content: str, metadata: dict[str, Any], endpoint_or_page: str) -> bool:
        haystacks: list[str] = [str(script_content or ""), str(endpoint_or_page or "")]
        haystacks.extend(str(value) for value in metadata.values())
        combined = "\n".join(haystacks)
        return any(token in combined for token in self._TODO_PATTERNS)

    def _has_critical_todos(self, script_content: str, metadata: dict[str, Any], endpoint_or_page: str) -> bool:
        haystacks: list[str] = [str(script_content or ""), str(endpoint_or_page or "")]
        haystacks.extend(str(value) for value in metadata.values())
        combined = "\n".join(haystacks)
        return any(token in combined for token in self._CRITICAL_TODO_TOKENS)

    def _extract_base_url(self, script_content: str) -> str:
        match = re.search(
            r'BASE_URL\s*=\s*os\.getenv\(\s*"[^"]+"\s*,\s*"([^"]+)"\s*\)',
            str(script_content or ""),
        )
        if match:
            return match.group(1)
        return ""

    def _extract_api_method(self, script_content: str) -> str:
        match = re.search(r"requests\.(get|post|put|patch|delete)\(", str(script_content or ""), re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return "GET"

    def _extract_api_endpoint(self, script_content: str) -> str:
        match = re.search(r'requests\.[a-z]+\(([^,]+),', str(script_content or ""), re.IGNORECASE)
        if not match:
            return ""
        expression = match.group(1)
        path_match = re.search(r'"(/[^"]*)"', expression)
        if path_match:
            return path_match.group(1)
        return expression.strip()

    def _extract_web_page(self, script_content: str) -> str:
        match = re.search(r'page\.goto\(([^)]+)\)', str(script_content or ""))
        if not match:
            return ""
        expression = match.group(1)
        path_match = re.search(r'"(/[^"]*)"', expression)
        if path_match:
            return path_match.group(1)
        return expression.strip()

    def _contains_blocked_keyword(self, value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return any(keyword in normalized for keyword in ("production", "prod", "live", "payment-live", "real-bank"))

    def _issue(
        self,
        target_id: str,
        *,
        severity: str,
        issue_type: str,
        message: str,
        recommendation: str,
    ) -> ExecutionPreflightIssue:
        issue = ExecutionPreflightIssue(
            issue_id=f"EXEC-ISSUE-{self._next_issue_number:03d}",
            target_id=target_id,
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
        )
        self._next_issue_number += 1
        return issue

    def _read_json_dict(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        payload = self._workspace_service.read_json(path)
        return payload if isinstance(payload, dict) else {}

    def _read_json_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        payload = self._workspace_service.read_json(path)
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


def build_execution_plan(
    workspace_path: str | Path,
    targets: Sequence[ExecutionTarget],
    *,
    policy: ExecutionSafetyPolicy | None = None,
    metadata: dict | None = None,
) -> ExecutionPlan:
    """Convenience wrapper for building a static execution plan from targets."""

    return ExecutionPreflightService().build_execution_plan(
        workspace_path,
        targets,
        policy=policy,
        metadata=metadata,
    )


def build_execution_plan_from_workspace(
    workspace_path: str | Path,
    *,
    policy: ExecutionSafetyPolicy | None = None,
    metadata: dict | None = None,
) -> ExecutionPlan:
    """Convenience wrapper for building a static execution plan from workspace artifacts."""

    return ExecutionPreflightService().build_execution_plan_from_workspace(
        workspace_path,
        policy=policy,
        metadata=metadata,
    )


def preflight_execution_target(
    target: ExecutionTarget,
    *,
    policy: ExecutionSafetyPolicy | None = None,
) -> ExecutionPreflightResult:
    """Convenience wrapper for static target preflight analysis."""

    return ExecutionPreflightService().preflight_execution_target(target, policy=policy)
