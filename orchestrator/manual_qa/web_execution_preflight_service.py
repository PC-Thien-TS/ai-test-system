"""Static web execution preflight planning without running Web Playwright drafts."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.manual_qa.models import (
    WebExecutionPlan,
    WebExecutionPreflightIssue,
    WebExecutionPreflightResult,
    WebExecutionSafetyPolicy,
    WebExecutionTarget,
)
from orchestrator.manual_qa.web_execution_safety_service import (
    WebExecutionSafetyService,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class WebExecutionPreflightService:
    """Build deterministic offline web execution plans from Web Playwright draft metadata."""

    _BASE_TIME = datetime(2024, 1, 23, 0, 0, 0)
    _CRITICAL_TODO_TOKENS = ("TODO_PAGE_URL", "TODO_SELECTOR", "TODO_ASSERTION_URL", "TODO_TEXT")
    _LOGIN_TOKENS = ("login", "sign in", "signin", "authenticated", "session", "password", "username")
    _UPLOAD_TOKENS = ("upload", "set_input_files", "file-input", "todo_file")
    _DOWNLOAD_TOKENS = ("download", "save_as", "export", "download file")
    _PAYMENT_TOKENS = ("payment", "checkout", "pay now", "card-number", "real-bank", "payment-live")
    _CAPTCHA_OTP_TOKENS = ("captcha", "otp", "2fa", "two-factor", "one-time password")

    def __init__(self) -> None:
        self._workspace_service = ManualQAWorkspaceService()
        self._safety_service = WebExecutionSafetyService()
        self._next_target_number = 1
        self._next_issue_number = 1
        self._next_preflight_number = 1
        self._next_timestamp_offset = 0

    def build_web_execution_plan(
        self,
        workspace_path: str | Path,
        targets: list[WebExecutionTarget],
        *,
        policy: WebExecutionSafetyPolicy | None = None,
        metadata: dict | None = None,
    ) -> WebExecutionPlan:
        safety_policy = policy or self._safety_service.create_default_web_execution_safety_policy()
        results = [self.preflight_web_execution_target(target, policy=safety_policy) for target in targets]
        overall_decision = self._derive_overall_decision(results)
        if not targets:
            overall_decision = "Missing Web Draft Packages"
        return WebExecutionPlan(
            plan_id="WEB-EXEC-PLAN-001",
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
            evidence_capture_plan=self._safety_service.build_web_evidence_capture_plan(safety_policy),
            overall_decision=overall_decision,
            recommended_next_step=self._recommended_next_step(overall_decision),
            metadata={
                "risk_levels": [item.risk_level for item in results],
                "available_script_types": sorted({target.script_type for target in targets}),
                **dict(metadata or {}),
            },
            created_at=self._next_timestamp(),
        )

    def build_web_execution_plan_from_workspace(
        self,
        workspace_path: str | Path,
        *,
        policy: WebExecutionSafetyPolicy | None = None,
        metadata: dict | None = None,
    ) -> WebExecutionPlan:
        workspace = Path(workspace_path)
        safety_policy = policy or self._safety_service.create_default_web_execution_safety_policy()
        targets = self._discover_targets(workspace)
        return self.build_web_execution_plan(
            workspace,
            targets,
            policy=safety_policy,
            metadata=metadata,
        )

    def preflight_web_execution_target(
        self,
        target: WebExecutionTarget,
        *,
        policy: WebExecutionSafetyPolicy | None = None,
    ) -> WebExecutionPreflightResult:
        safety_policy = policy or self._safety_service.create_default_web_execution_safety_policy()
        issues: list[WebExecutionPreflightIssue] = []

        if target.package_status == "Invalid" or target.validation_status == "Invalid":
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="invalid_package_manifest",
                    message="The Web Playwright package or validation result is invalid.",
                    recommendation="Fix invalid draft artifacts before browser sandbox design continues.",
                )
            )
        elif target.package_status == "Needs Attention" or target.validation_status == "Needs Attention":
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="package_needs_attention",
                    message="The web draft package still contains warnings or unresolved validation markers.",
                    recommendation="Resolve package warnings and TODO markers before browser sandbox prototyping.",
                )
            )

        if not safety_policy.allow_browser_execution:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="browser_execution_disabled_by_policy",
                    message="Browser execution is disabled by the current web safety policy.",
                    recommendation="Keep this plan static until a later sandbox phase intentionally enables browser execution.",
                )
            )

        if safety_policy.dry_run_only:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="dry_run_only_mode",
                    message="The current policy only permits dry-run planning for web execution.",
                    recommendation="Retain dry-run mode for Phase 9A and defer real Playwright execution to a later phase.",
                )
            )

        if safety_policy.require_human_approval and not bool(target.metadata.get("human_approval", False)):
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="missing_human_approval",
                    message="Human approval is required before any browser execution could be considered.",
                    recommendation="Require explicit human approval in a future web sandbox workflow.",
                )
            )

        if target.base_url and not self._safety_service.is_web_base_url_allowed(safety_policy, target.base_url):
            issue_type = "blocked_base_url" if self._contains_blocked_keyword(target.base_url) else "non_local_base_url"
            severity = "Critical" if issue_type == "blocked_base_url" else "High"
            issues.append(
                self._issue(
                    target.target_id,
                    severity=severity,
                    issue_type=issue_type,
                    message=f"Base URL '{target.base_url}' is not allowed by policy.",
                    recommendation="Use localhost-only web targets for browser sandbox prototyping.",
                )
            )
        elif not target.base_url:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="missing_base_url",
                    message="No base URL could be inferred from the Web Playwright draft metadata.",
                    recommendation="Preserve explicit localhost defaults in draft content before sandbox work.",
                )
            )

        if target.page_url == "/TODO_PAGE_URL" or "TODO_PAGE_URL" in target.page_url:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="todo_page_url",
                    message="The draft still contains a TODO page URL placeholder.",
                    recommendation="Replace the TODO page URL with a real local route before browser sandbox work.",
                )
            )
        if target.metadata.get("has_todo_selector", False):
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="todo_selector",
                    message="The draft still contains a TODO selector placeholder.",
                    recommendation="Replace TODO selectors with stable locators before browser sandbox work.",
                )
            )
        if target.metadata.get("has_todo_assertion", False):
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="todo_assertion",
                    message="The draft still contains a TODO assertion placeholder.",
                    recommendation="Replace TODO assertions with concrete UI expectations before browser sandbox work.",
                )
            )

        if target.requires_login:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Medium",
                    issue_type="login_session_dependency",
                    message="The draft appears to require login or session setup.",
                    recommendation="Design controlled login/session fixtures before browser execution.",
                )
            )
        if target.requires_file_upload and not safety_policy.allow_file_upload:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="file_upload_not_allowed",
                    message="The draft appears to require file upload, which is blocked by policy.",
                    recommendation="Keep upload flows blocked until browser sandbox file controls exist.",
                )
            )
        if target.requires_file_download and not safety_policy.allow_file_download:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="file_download_not_allowed",
                    message="The draft appears to require file download, which is blocked by policy.",
                    recommendation="Keep download flows blocked until artifact handling is designed.",
                )
            )
        if target.has_external_navigation and not safety_policy.allow_external_navigation:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="High",
                    issue_type="external_navigation_not_allowed",
                    message="The draft appears to navigate outside the allowed local target scope.",
                    recommendation="Restrict browser sandbox design to internal localhost navigation only.",
                )
            )
        if target.has_payment_flow and not safety_policy.allow_payment_flows:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="payment_flow_blocked",
                    message="The draft appears to include a payment flow that is blocked by policy.",
                    recommendation="Keep payment flows out of browser sandbox work until explicit payment-safe controls exist.",
                )
            )
        if target.has_captcha_or_otp and not safety_policy.allow_captcha_or_otp_flows:
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="captcha_or_otp_blocked",
                    message="The draft appears to require captcha or OTP handling, which is blocked by policy.",
                    recommendation="Exclude captcha or OTP flows from browser sandbox design until approved handling exists.",
                )
            )
        if target.script_type != "web_playwright":
            issues.append(
                self._issue(
                    target.target_id,
                    severity="Critical",
                    issue_type="script_type_not_allowed",
                    message=f"Script type '{target.script_type}' is not supported by the web preflight service.",
                    recommendation="Use Web Playwright draft artifacts only for this preflight flow.",
                )
            )

        risk_level = self._safety_service.classify_web_execution_risk(target, safety_policy)
        decision = self._derive_decision(issues, safety_policy)
        result = WebExecutionPreflightResult(
            preflight_id=f"WEB-PREFLIGHT-{self._next_preflight_number:03d}",
            target_id=target.target_id,
            decision=decision,
            is_allowed=decision == "Allowed",
            issues=issues,
            risk_level=risk_level,
            recommended_action=self._recommended_action(decision),
            metadata={
                "package_status": target.package_status,
                "validation_status": target.validation_status,
                "base_url": target.base_url,
                "page_url": target.page_url,
            },
            created_at=self._next_timestamp(),
        )
        self._next_preflight_number += 1
        return result

    def _discover_targets(self, workspace: Path) -> list[WebExecutionTarget]:
        base_dir = workspace / "script_drafts" / "web_playwright"
        manifest = self._read_json_dict(base_dir / "web_playwright_package_manifest.json")
        validations = self._read_json_list(base_dir / "web_playwright_validation.json")
        drafts = self._read_json_list(base_dir / "web_playwright_script_drafts.json")
        validation_by_draft_id = {str(item.get("draft_id", "")): item for item in validations if isinstance(item, dict)}
        package_status = str(manifest.get("status", "Missing")) if manifest else "Missing"

        targets: list[WebExecutionTarget] = []
        for draft in drafts:
            script_content = str(draft.get("script_content", ""))
            metadata = draft.get("metadata", {}) if isinstance(draft.get("metadata"), dict) else {}
            validation = validation_by_draft_id.get(str(draft.get("draft_id", "")), {})
            page_url = str(metadata.get("page_url", "") or self._extract_page_url(script_content))
            base_url = self._extract_base_url(script_content)
            combined_text = " ".join(
                [
                    str(draft.get("title", "")),
                    script_content,
                    page_url,
                    " ".join(metadata.get("selector_hints", [])) if isinstance(metadata.get("selector_hints"), list) else "",
                    " ".join(metadata.get("action_hints", [])) if isinstance(metadata.get("action_hints"), list) else "",
                    " ".join(metadata.get("assertion_hints", [])) if isinstance(metadata.get("assertion_hints"), list) else "",
                ]
            ).lower()
            targets.append(
                WebExecutionTarget(
                    target_id=f"WEB-TARGET-{self._next_target_number:03d}",
                    script_type="web_playwright",
                    draft_id=str(draft.get("draft_id", "")),
                    test_case_id=str(draft.get("test_case_id", "")),
                    file_name=str(draft.get("file_name", "")),
                    package_status=package_status,
                    validation_status=self._validation_status(validation),
                    base_url=base_url,
                    page_url=page_url,
                    has_todos=self._has_todos(script_content, metadata, page_url),
                    has_critical_todos=self._has_critical_todos(script_content, metadata, page_url),
                    requires_login=self._contains_any(combined_text, self._LOGIN_TOKENS),
                    requires_file_upload=self._contains_any(combined_text, self._UPLOAD_TOKENS),
                    requires_file_download=self._contains_any(combined_text, self._DOWNLOAD_TOKENS),
                    has_external_navigation=self._has_external_navigation(base_url, page_url),
                    has_payment_flow=self._contains_any(combined_text, self._PAYMENT_TOKENS),
                    has_captcha_or_otp=self._contains_any(combined_text, self._CAPTCHA_OTP_TOKENS),
                    metadata={
                        "source": "web_playwright",
                        "browser_execution_requested": False,
                        "manifest_path": "script_drafts/web_playwright/web_playwright_package_manifest.json",
                        "validation_path": "script_drafts/web_playwright/web_playwright_validation.json",
                        "drafts_path": "script_drafts/web_playwright/web_playwright_script_drafts.json",
                        "has_todo_page_url": bool(validation.get("has_todo_page_url", False)),
                        "has_todo_selector": bool(validation.get("has_todo_selector", False) or "TODO_SELECTOR" in script_content),
                        "has_todo_assertion": bool(validation.get("has_todo_assertion", False)),
                    },
                    created_at=self._next_timestamp(),
                )
            )
            self._next_target_number += 1
        return targets

    def _derive_decision(
        self,
        issues: list[WebExecutionPreflightIssue],
        policy: WebExecutionSafetyPolicy,
    ) -> str:
        if any(issue.severity == "Critical" for issue in issues):
            return "Blocked"
        if policy.dry_run_only or not policy.allow_browser_execution:
            return "Dry Run Only"
        if policy.require_human_approval and any(issue.issue_type == "missing_human_approval" for issue in issues):
            return "Needs Human Approval"
        if any(issue.severity == "High" for issue in issues):
            return "Needs Human Approval"
        return "Allowed"

    def _derive_overall_decision(self, results: list[WebExecutionPreflightResult]) -> str:
        if not results:
            return "Missing Web Draft Packages"
        if any(item.decision == "Blocked" for item in results):
            return "Blocked"
        actionable_issue_types = {
            "package_needs_attention",
            "todo_page_url",
            "todo_selector",
            "todo_assertion",
            "login_session_dependency",
            "file_upload_not_allowed",
            "file_download_not_allowed",
            "external_navigation_not_allowed",
            "payment_flow_blocked",
            "captcha_or_otp_blocked",
            "blocked_base_url",
            "non_local_base_url",
        }
        if any(any(issue.issue_type in actionable_issue_types for issue in result.issues) for result in results):
            return "Needs Attention"
        return "Ready for Browser Sandbox Design Review"

    def _recommended_next_step(self, overall_decision: str) -> str:
        steps = {
            "Ready for Browser Sandbox Design Review": "Review web sandbox preflight before implementing browser execution gates",
            "Needs Attention": "Resolve Web Playwright warnings and blocked browser flow risks before sandbox design advances",
            "Blocked": "Fix blocked Web Playwright draft packages before continuing",
            "Missing Web Draft Packages": "Generate and validate Web Playwright draft packages first",
        }
        return steps.get(overall_decision, "Review web sandbox preflight outputs")

    def _recommended_action(self, decision: str) -> str:
        actions = {
            "Allowed": "Eligible for a future strictly gated browser sandbox prototype.",
            "Blocked": "Do not proceed until critical web safety issues are resolved.",
            "Needs Human Approval": "Require explicit human approval and tighter browser controls first.",
            "Dry Run Only": "Keep this target in design-only dry-run mode for now.",
        }
        return actions.get(decision, "Review browser sandbox constraints.")

    def _read_json_dict(self, path: Path) -> dict:
        if not path.exists():
            return {}
        payload = self._workspace_service.read_json(path)
        return payload if isinstance(payload, dict) else {}

    def _read_json_list(self, path: Path) -> list:
        if not path.exists():
            return []
        payload = self._workspace_service.read_json(path)
        return payload if isinstance(payload, list) else []

    def _extract_base_url(self, script_content: str) -> str:
        match = re.search(r'BASE_URL\s*=\s*os\.getenv\([^,]+,\s*"([^"]+)"\)', script_content)
        return match.group(1) if match else ""

    def _extract_page_url(self, script_content: str) -> str:
        match = re.search(r'page\.goto\(\s*BASE_URL\s*\+\s*"([^"]+)"\s*\)', script_content)
        if match:
            return match.group(1)
        match = re.search(r'page\.goto\(\s*"([^"]+)"\s*\)', script_content)
        return match.group(1) if match else ""

    def _validation_status(self, validation: dict) -> str:
        if not validation:
            return "Missing"
        if not bool(validation.get("is_valid", False)):
            return "Invalid"
        if (
            bool(validation.get("has_todo_page_url", False))
            or bool(validation.get("has_todo_selector", False))
            or bool(validation.get("has_todo_assertion", False))
        ):
            return "Needs Attention"
        return "Ready for Review"

    def _has_todos(self, script_content: str, metadata: dict, page_url: str) -> bool:
        haystack = " ".join(
            [
                script_content,
                page_url,
                " ".join(metadata.get("selector_hints", [])) if isinstance(metadata.get("selector_hints"), list) else "",
                " ".join(metadata.get("action_hints", [])) if isinstance(metadata.get("action_hints"), list) else "",
                " ".join(metadata.get("assertion_hints", [])) if isinstance(metadata.get("assertion_hints"), list) else "",
            ]
        )
        return "todo" in haystack.lower()

    def _has_critical_todos(self, script_content: str, metadata: dict, page_url: str) -> bool:
        haystack = " ".join(
            [
                script_content,
                page_url,
                " ".join(metadata.get("selector_hints", [])) if isinstance(metadata.get("selector_hints"), list) else "",
            ]
        )
        return any(token in haystack for token in self._CRITICAL_TODO_TOKENS)

    def _has_external_navigation(self, base_url: str, page_url: str) -> bool:
        normalized_page = str(page_url or "").strip().lower()
        normalized_base = str(base_url or "").strip().lower()
        if normalized_page.startswith("http://") or normalized_page.startswith("https://"):
            return bool(normalized_base and not normalized_page.startswith(normalized_base))
        return "external" in normalized_page

    def _contains_any(self, value: str, tokens: tuple[str, ...]) -> bool:
        normalized = str(value or "").lower()
        return any(token in normalized for token in tokens)

    def _contains_blocked_keyword(self, value: str) -> bool:
        return any(keyword in str(value or "").lower() for keyword in self._safety_service._BLOCKED_KEYWORDS)

    def _issue(
        self,
        target_id: str,
        *,
        severity: str,
        issue_type: str,
        message: str,
        recommendation: str,
        metadata: dict | None = None,
    ) -> WebExecutionPreflightIssue:
        issue = WebExecutionPreflightIssue(
            issue_id=f"WEB-PREFLIGHT-ISSUE-{self._next_issue_number:03d}",
            target_id=target_id,
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            metadata=dict(metadata or {}),
        )
        self._next_issue_number += 1
        return issue

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


def build_web_execution_plan(
    workspace_path: str | Path,
    targets: list[WebExecutionTarget],
    *,
    policy: WebExecutionSafetyPolicy | None = None,
    metadata: dict | None = None,
) -> WebExecutionPlan:
    return WebExecutionPreflightService().build_web_execution_plan(
        workspace_path,
        targets,
        policy=policy,
        metadata=metadata,
    )


def build_web_execution_plan_from_workspace(
    workspace_path: str | Path,
    *,
    policy: WebExecutionSafetyPolicy | None = None,
    metadata: dict | None = None,
) -> WebExecutionPlan:
    return WebExecutionPreflightService().build_web_execution_plan_from_workspace(
        workspace_path,
        policy=policy,
        metadata=metadata,
    )


def preflight_web_execution_target(
    target: WebExecutionTarget,
    *,
    policy: WebExecutionSafetyPolicy | None = None,
) -> WebExecutionPreflightResult:
    return WebExecutionPreflightService().preflight_web_execution_target(target, policy=policy)
