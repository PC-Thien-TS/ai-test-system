"""Deterministic Manual QA models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


RESULT_STATUSES = (
    "Not Run",
    "Pass",
    "Fail",
    "Blocked",
    "Skipped",
    "Retest",
)


@dataclass
class ProjectProfile:
    """Manual QA project profile."""

    project_id: str
    name: str
    product_type: str
    description: str = ""
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedRequirement:
    """Normalized requirement used by downstream Manual QA generators."""

    requirement_id: str
    title: str
    description: str
    module: str = "General"
    priority: str = "Medium"
    roles: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    source_ref: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChecklistItem:
    """Manual tester checklist item derived from a requirement."""

    checklist_id: str
    requirement_id: str
    module: str
    title: str
    description: str
    priority: str
    checked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ManualTestCase:
    """Deterministic manual test case."""

    test_case_id: str
    requirement_ids: List[str]
    module: str
    title: str
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    priority: str = "Medium"
    test_type: str = "Positive"
    status: str = "Not Run"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExportBundle:
    """Bundle used for stable exports."""

    project: ProjectProfile
    requirements: List[NormalizedRequirement] = field(default_factory=list)
    checklist_items: List[ChecklistItem] = field(default_factory=list)
    test_cases: List[ManualTestCase] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project.to_dict(),
            "requirements": [item.to_dict() for item in self.requirements],
            "checklist_items": [item.to_dict() for item in self.checklist_items],
            "test_cases": [item.to_dict() for item in self.test_cases],
            "metadata": dict(self.metadata),
        }


@dataclass
class TestSuite:
    """Deterministic manual test suite."""

    __test__ = False
    suite_id: str
    project_id: str
    name: str
    test_case_ids: List[str]
    scope: str = ""
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestResult:
    """Deterministic manual test result."""

    __test__ = False
    result_id: str
    run_id: str
    test_case_id: str
    status: str = "Not Run"
    actual_result: str = ""
    notes: str = ""
    updated_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestRun:
    """Deterministic manual test run."""

    __test__ = False
    run_id: str
    project_id: str
    suite_id: str
    environment: str
    build: str
    tester: str
    status: str = "Not Started"
    results: List[TestResult] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "suite_id": self.suite_id,
            "environment": self.environment,
            "build": self.build,
            "tester": self.tester,
            "status": self.status,
            "results": [result.to_dict() for result in self.results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class RunSummary:
    """Deterministic summary for a manual test run."""

    run_id: str
    total: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    not_run: int
    pass_rate: float
    status: str
    retest: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    """Deterministic evidence metadata attached to a manual run/result."""

    evidence_id: str
    run_id: str
    test_case_id: str
    evidence_type: str
    path_or_url: str
    description: str = ""
    content_type: str = ""
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BugDraft:
    """Deterministic offline bug draft generated from a manual result."""

    bug_id: str
    run_id: str
    test_case_id: str
    title: str
    severity: str
    priority: str
    environment: str
    build: str
    steps_to_reproduce: List[str] = field(default_factory=list)
    expected_result: str = ""
    actual_result: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    status: str = "Draft"
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailureSignature:
    """Deterministic failure signature for Manual QA memory."""

    signature_id: str
    fingerprint: str
    module: str
    test_case_id: str
    title: str
    symptom: str
    expected_result: str = ""
    actual_result: str = ""
    environment: str = ""
    build: str = ""
    severity: str = ""
    priority: str = ""
    source_bug_id: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailureRecord:
    """Deterministic in-memory failure memory record."""

    record_id: str
    signature: FailureSignature
    occurrence_count: int
    first_seen: str | None = None
    last_seen: str | None = None
    related_bug_ids: List[str] = field(default_factory=list)
    related_run_ids: List[str] = field(default_factory=list)
    related_test_case_ids: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "signature": self.signature.to_dict(),
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "related_bug_ids": list(self.related_bug_ids),
            "related_run_ids": list(self.related_run_ids),
            "related_test_case_ids": list(self.related_test_case_ids),
            "notes": list(self.notes),
            "metadata": dict(self.metadata),
        }


@dataclass
class AutomationCandidate:
    """Deterministic automation candidate recommendation."""

    candidate_id: str
    test_case_id: str
    requirement_ids: List[str] = field(default_factory=list)
    module: str = ""
    title: str = ""
    score: int = 0
    recommendation: str = "Do Not Automate"
    reasons: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    suggested_automation_type: str = "unknown"
    related_failure_record_ids: List[str] = field(default_factory=list)
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkspaceValidationResult:
    """Structured validation result for a local Manual QA workspace."""

    is_valid: bool
    missing_folders: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifact_counts: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScriptGenerationGap:
    """Deterministic readiness gap for future script draft generation."""

    gap_id: str
    test_case_id: str
    gap_type: str
    message: str
    severity: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScriptGenerationReadiness:
    """Deterministic readiness assessment for future script drafting."""

    readiness_id: str
    test_case_id: str
    module: str
    title: str
    target_type: str
    readiness_status: str
    readiness_score: int
    gaps: List[ScriptGenerationGap] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    suggested_next_step: str = ""
    automation_candidate_id: str = ""
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "readiness_id": self.readiness_id,
            "test_case_id": self.test_case_id,
            "module": self.module,
            "title": self.title,
            "target_type": self.target_type,
            "readiness_status": self.readiness_status,
            "readiness_score": self.readiness_score,
            "gaps": [gap.to_dict() for gap in self.gaps],
            "strengths": list(self.strengths),
            "suggested_next_step": self.suggested_next_step,
            "automation_candidate_id": self.automation_candidate_id,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class APITestScriptDraft:
    """Deterministic API test script draft derived from Manual QA assets."""

    draft_id: str
    test_case_id: str
    requirement_ids: List[str] = field(default_factory=list)
    module: str = ""
    title: str = ""
    readiness_id: str = ""
    target_type: str = "api"
    framework: str = "pytest-requests"
    language: str = "python"
    file_name: str = ""
    script_content: str = ""
    status: str = "Draft"
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIScriptValidationIssue:
    """Static validation issue found in an API draft artifact."""

    issue_id: str
    draft_id: str
    severity: str
    issue_type: str
    message: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIScriptValidationResult:
    """Static validation result for an API draft artifact."""

    validation_id: str
    draft_id: str
    test_case_id: str
    file_name: str
    is_valid: bool
    syntax_valid: bool
    has_draft_warning: bool
    has_no_execution_marker: bool
    has_status_assertion: bool
    has_todo_endpoint: bool
    has_todo_payload: bool
    issues: List[APIScriptValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "draft_id": self.draft_id,
            "test_case_id": self.test_case_id,
            "file_name": self.file_name,
            "is_valid": self.is_valid,
            "syntax_valid": self.syntax_valid,
            "has_draft_warning": self.has_draft_warning,
            "has_no_execution_marker": self.has_no_execution_marker,
            "has_status_assertion": self.has_status_assertion,
            "has_todo_endpoint": self.has_todo_endpoint,
            "has_todo_payload": self.has_todo_payload,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class APIScriptPackageManifest:
    """Packaging metadata for a validated set of API draft artifacts."""

    package_id: str
    package_name: str
    draft_count: int
    valid_count: int
    invalid_count: int
    warning_count: int
    draft_files: List[str] = field(default_factory=list)
    validation_report_files: List[str] = field(default_factory=list)
    generated_at: str | None = None
    status: str = "Needs Attention"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebPlaywrightGap:
    """Deterministic readiness gap for future Playwright web draft generation."""

    gap_id: str
    test_case_id: str
    gap_type: str
    message: str
    severity: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebPlaywrightReadiness:
    """Deterministic readiness assessment for future Playwright web draft generation."""

    readiness_id: str
    test_case_id: str
    requirement_ids: List[str] = field(default_factory=list)
    module: str = ""
    title: str = ""
    readiness_status: str = "Needs More Data"
    readiness_score: int = 0
    page_url: str = ""
    selector_hints: List[str] = field(default_factory=list)
    action_hints: List[str] = field(default_factory=list)
    assertion_hints: List[str] = field(default_factory=list)
    gaps: List[WebPlaywrightGap] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    suggested_next_step: str = ""
    automation_candidate_id: str = ""
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "readiness_id": self.readiness_id,
            "test_case_id": self.test_case_id,
            "requirement_ids": list(self.requirement_ids),
            "module": self.module,
            "title": self.title,
            "readiness_status": self.readiness_status,
            "readiness_score": self.readiness_score,
            "page_url": self.page_url,
            "selector_hints": list(self.selector_hints),
            "action_hints": list(self.action_hints),
            "assertion_hints": list(self.assertion_hints),
            "gaps": [gap.to_dict() for gap in self.gaps],
            "strengths": list(self.strengths),
            "suggested_next_step": self.suggested_next_step,
            "automation_candidate_id": self.automation_candidate_id,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class WebPlaywrightScriptDraft:
    """Deterministic Playwright Python script draft derived from Manual QA assets."""

    draft_id: str
    test_case_id: str
    requirement_ids: List[str] = field(default_factory=list)
    module: str = ""
    title: str = ""
    readiness_id: str = ""
    framework: str = "playwright-python"
    language: str = "python"
    file_name: str = ""
    script_content: str = ""
    status: str = "Draft"
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebPlaywrightValidationIssue:
    """Static validation issue found in a Web Playwright draft artifact."""

    issue_id: str
    draft_id: str
    severity: str
    issue_type: str
    message: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebPlaywrightValidationResult:
    """Static validation result for a Web Playwright draft artifact."""

    validation_id: str
    draft_id: str
    test_case_id: str
    file_name: str
    is_valid: bool
    syntax_valid: bool
    has_draft_warning: bool
    has_no_execution_marker: bool
    has_playwright_import: bool
    has_test_function: bool
    has_page_goto: bool
    has_locator_or_todo: bool
    has_action_or_todo: bool
    has_assertion_or_todo: bool
    has_todo_page_url: bool
    has_todo_selector: bool
    has_todo_assertion: bool
    issues: List[WebPlaywrightValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "draft_id": self.draft_id,
            "test_case_id": self.test_case_id,
            "file_name": self.file_name,
            "is_valid": self.is_valid,
            "syntax_valid": self.syntax_valid,
            "has_draft_warning": self.has_draft_warning,
            "has_no_execution_marker": self.has_no_execution_marker,
            "has_playwright_import": self.has_playwright_import,
            "has_test_function": self.has_test_function,
            "has_page_goto": self.has_page_goto,
            "has_locator_or_todo": self.has_locator_or_todo,
            "has_action_or_todo": self.has_action_or_todo,
            "has_assertion_or_todo": self.has_assertion_or_todo,
            "has_todo_page_url": self.has_todo_page_url,
            "has_todo_selector": self.has_todo_selector,
            "has_todo_assertion": self.has_todo_assertion,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class WebPlaywrightPackageManifest:
    """Packaging metadata for a validated set of Web Playwright draft artifacts."""

    package_id: str
    package_name: str
    draft_count: int
    valid_count: int
    invalid_count: int
    warning_count: int
    draft_files: List[str] = field(default_factory=list)
    validation_report_files: List[str] = field(default_factory=list)
    generated_at: str | None = None
    status: str = "Needs Attention"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DraftPackageGroupSummary:
    """Deterministic summary for one offline draft package group."""

    group_id: str
    group_type: str
    manifest_path: str
    validation_path: str
    status: str
    draft_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    warning_count: int = 0
    ready_for_review_count: int = 0
    needs_attention_count: int = 0
    invalid_item_count: int = 0
    missing: bool = False
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UnifiedDraftPackageSummary:
    """Deterministic offline dashboard summary over API and Web draft packages."""

    summary_id: str
    workspace_path: str
    total_groups: int
    total_drafts: int
    total_valid: int
    total_invalid: int
    total_warnings: int
    ready_groups: int
    needs_attention_groups: int
    invalid_groups: int
    missing_groups: int
    groups: List[DraftPackageGroupSummary] = field(default_factory=list)
    overall_status: str = "Missing"
    recommended_next_step: str = ""
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionSafetyPolicy:
    """Deterministic execution safety policy for future sandbox work."""

    policy_id: str
    name: str
    allow_execution: bool
    allowed_base_urls: List[str] = field(default_factory=list)
    blocked_base_urls: List[str] = field(default_factory=list)
    allowed_script_types: List[str] = field(default_factory=list)
    blocked_script_types: List[str] = field(default_factory=list)
    allow_write_methods: bool = False
    allow_delete_methods: bool = False
    require_human_approval: bool = True
    require_valid_package: bool = True
    require_no_critical_todos: bool = True
    timeout_seconds: int = 30
    max_scripts_per_run: int = 5
    dry_run_only: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionTarget:
    """Static execution target discovered from a draft package."""

    target_id: str
    script_type: str
    draft_id: str
    file_name: str
    package_status: str
    validation_status: str
    base_url: str
    method: str
    endpoint_or_page: str
    has_todos: bool = False
    has_critical_todos: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPreflightIssue:
    """Static preflight issue found before any sandbox execution exists."""

    issue_id: str
    target_id: str
    severity: str
    issue_type: str
    message: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPreflightResult:
    """Static preflight decision for one execution target."""

    preflight_id: str
    target_id: str
    script_type: str
    decision: str
    is_allowed: bool
    issues: List[ExecutionPreflightIssue] = field(default_factory=list)
    risk_level: str = "High"
    recommended_action: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preflight_id": self.preflight_id,
            "target_id": self.target_id,
            "script_type": self.script_type,
            "decision": self.decision,
            "is_allowed": self.is_allowed,
            "issues": [issue.to_dict() for issue in self.issues],
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class ExecutionPlan:
    """Static execution plan assembled from draft packages and policy rules."""

    plan_id: str
    workspace_path: str
    policy: ExecutionSafetyPolicy
    targets: List[ExecutionTarget] = field(default_factory=list)
    preflight_results: List[ExecutionPreflightResult] = field(default_factory=list)
    total_targets: int = 0
    allowed_count: int = 0
    blocked_count: int = 0
    needs_approval_count: int = 0
    dry_run_only: bool = True
    overall_decision: str = "Missing Draft Packages"
    recommended_next_step: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "workspace_path": self.workspace_path,
            "policy": self.policy.to_dict(),
            "targets": [target.to_dict() for target in self.targets],
            "preflight_results": [result.to_dict() for result in self.preflight_results],
            "total_targets": self.total_targets,
            "allowed_count": self.allowed_count,
            "blocked_count": self.blocked_count,
            "needs_approval_count": self.needs_approval_count,
            "dry_run_only": self.dry_run_only,
            "overall_decision": self.overall_decision,
            "recommended_next_step": self.recommended_next_step,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class WebExecutionSafetyPolicy:
    """Deterministic web execution safety policy for future browser sandbox work."""

    policy_id: str
    name: str
    allow_browser_execution: bool
    dry_run_only: bool = True
    require_human_approval: bool = True
    require_valid_package: bool = True
    require_no_critical_todos: bool = True
    allowed_base_urls: List[str] = field(default_factory=list)
    blocked_base_urls: List[str] = field(default_factory=list)
    allowed_browsers: List[str] = field(default_factory=list)
    headless_only: bool = True
    allow_file_upload: bool = False
    allow_file_download: bool = False
    allow_external_navigation: bool = False
    allow_payment_flows: bool = False
    allow_captcha_or_otp_flows: bool = False
    timeout_seconds: int = 30
    max_scripts_per_run: int = 3
    capture_screenshot: bool = True
    capture_trace: bool = True
    capture_video: bool = False
    capture_console_log: bool = True
    capture_network_log: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebExecutionTarget:
    """Static web execution target discovered from a Web Playwright draft package."""

    target_id: str
    script_type: str
    draft_id: str
    test_case_id: str
    file_name: str
    package_status: str
    validation_status: str
    base_url: str
    page_url: str
    has_todos: bool = False
    has_critical_todos: bool = False
    requires_login: bool = False
    requires_file_upload: bool = False
    requires_file_download: bool = False
    has_external_navigation: bool = False
    has_payment_flow: bool = False
    has_captcha_or_otp: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebExecutionPreflightIssue:
    """Static web preflight issue found before any browser sandbox exists."""

    issue_id: str
    target_id: str
    severity: str
    issue_type: str
    message: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebExecutionPreflightResult:
    """Static web preflight decision for one web execution target."""

    preflight_id: str
    target_id: str
    decision: str
    is_allowed: bool
    issues: List[WebExecutionPreflightIssue] = field(default_factory=list)
    risk_level: str = "High"
    recommended_action: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preflight_id": self.preflight_id,
            "target_id": self.target_id,
            "decision": self.decision,
            "is_allowed": self.is_allowed,
            "issues": [issue.to_dict() for issue in self.issues],
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class WebExecutionPlan:
    """Static web execution plan assembled from Web Playwright draft artifacts."""

    plan_id: str
    workspace_path: str
    policy: WebExecutionSafetyPolicy
    targets: List[WebExecutionTarget] = field(default_factory=list)
    preflight_results: List[WebExecutionPreflightResult] = field(default_factory=list)
    total_targets: int = 0
    allowed_count: int = 0
    blocked_count: int = 0
    needs_approval_count: int = 0
    dry_run_only: bool = True
    evidence_capture_plan: Dict[str, Any] = field(default_factory=dict)
    overall_decision: str = "Missing Web Draft Packages"
    recommended_next_step: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "workspace_path": self.workspace_path,
            "policy": self.policy.to_dict(),
            "targets": [target.to_dict() for target in self.targets],
            "preflight_results": [result.to_dict() for result in self.preflight_results],
            "total_targets": self.total_targets,
            "allowed_count": self.allowed_count,
            "blocked_count": self.blocked_count,
            "needs_approval_count": self.needs_approval_count,
            "dry_run_only": self.dry_run_only,
            "evidence_capture_plan": dict(self.evidence_capture_plan),
            "overall_decision": self.overall_decision,
            "recommended_next_step": self.recommended_next_step,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class APIExecutionRequest:
    """Static request built for a gated API sandbox execution attempt."""

    request_id: str
    draft_id: str
    test_case_id: str
    file_name: str
    method: str
    base_url: str
    endpoint: str
    headers: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    policy_id: str = ""
    preflight_id: str = ""
    dry_run: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIExecutionLogEntry:
    """Log entry captured during a sandbox-only API execution attempt."""

    log_id: str
    level: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIExecutionResult:
    """Sandbox-only API execution result kept separate from Manual QA run state."""

    execution_id: str
    request: APIExecutionRequest
    status: str
    http_status_code: int | None = None
    duration_ms: int = 0
    response_excerpt: str = ""
    error_type: str = ""
    error_message: str = ""
    assertion_expected_status: int | None = None
    assertion_passed: bool | None = None
    logs: List[APIExecutionLogEntry] = field(default_factory=list)
    executed_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "request": self.request.to_dict(),
            "status": self.status,
            "http_status_code": self.http_status_code,
            "duration_ms": self.duration_ms,
            "response_excerpt": self.response_excerpt,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "assertion_expected_status": self.assertion_expected_status,
            "assertion_passed": self.assertion_passed,
            "logs": [item.to_dict() for item in self.logs],
            "executed_at": self.executed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class APIExecutionEvidence:
    """Metadata-only evidence derived from an API sandbox execution result."""

    evidence_id: str
    execution_id: str
    draft_id: str
    test_case_id: str
    evidence_type: str
    title: str
    summary: str
    status: str
    method: str
    base_url: str
    endpoint: str
    http_status_code: int | None = None
    assertion_passed: bool | None = None
    response_excerpt: str = ""
    error_type: str = ""
    error_message: str = ""
    log_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIExecutionSummary:
    """Aggregate summary over API sandbox execution results."""

    summary_id: str
    total: int
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    dry_run: int = 0
    error: int = 0
    not_run: int = 0
    pass_rate: float = 0.0
    failure_rate: float = 0.0
    evidence_ids: List[str] = field(default_factory=list)
    bug_suggestion_ids: List[str] = field(default_factory=list)
    failure_signature_ids: List[str] = field(default_factory=list)
    status: str = "No Results"
    recommended_next_step: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIExecutionHistoryEntry:
    """Historical snapshot derived from one saved API execution summary."""

    history_id: str
    source_file: str
    run_label: str
    summary_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    dry_run: int = 0
    error: int = 0
    not_run: int = 0
    pass_rate: float = 0.0
    failure_rate: float = 0.0
    status: str = "No Results"
    evidence_ids: List[str] = field(default_factory=list)
    bug_suggestion_ids: List[str] = field(default_factory=list)
    failure_signature_ids: List[str] = field(default_factory=list)
    created_at: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIExecutionTrendSummary:
    """Aggregate trend summary over multiple API execution history entries."""

    trend_id: str
    total_runs: int = 0
    total_executions: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_blocked: int = 0
    total_dry_run: int = 0
    total_error: int = 0
    total_not_run: int = 0
    average_pass_rate: float = 0.0
    average_failure_rate: float = 0.0
    latest_status: str = "No Results"
    trend_status: str = "No History"
    repeated_failure_count: int = 0
    flaky_candidate_count: int = 0
    repeated_failure_keys: List[str] = field(default_factory=list)
    flaky_candidate_keys: List[str] = field(default_factory=list)
    entries: List[APIExecutionHistoryEntry] = field(default_factory=list)
    recommended_next_step: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "total_runs": self.total_runs,
            "total_executions": self.total_executions,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_blocked": self.total_blocked,
            "total_dry_run": self.total_dry_run,
            "total_error": self.total_error,
            "total_not_run": self.total_not_run,
            "average_pass_rate": self.average_pass_rate,
            "average_failure_rate": self.average_failure_rate,
            "latest_status": self.latest_status,
            "trend_status": self.trend_status,
            "repeated_failure_count": self.repeated_failure_count,
            "flaky_candidate_count": self.flaky_candidate_count,
            "repeated_failure_keys": list(self.repeated_failure_keys),
            "flaky_candidate_keys": list(self.flaky_candidate_keys),
            "entries": [item.to_dict() for item in self.entries],
            "recommended_next_step": self.recommended_next_step,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


def count_result_statuses(results: List[TestResult]) -> Dict[str, int]:
    """Count result statuses in a stable shape."""

    counts = {
        "Pass": 0,
        "Fail": 0,
        "Blocked": 0,
        "Skipped": 0,
        "Not Run": 0,
        "Retest": 0,
    }
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    return counts


def aggregate_run_status(results: List[TestResult]) -> str:
    """Derive aggregate run status from result states."""

    if not results:
        return "Not Started"

    counts = count_result_statuses(results)

    if counts["Not Run"] == len(results):
        return "Not Started"
    if counts["Fail"] > 0:
        return "Failed"
    if counts["Blocked"] > 0:
        return "Blocked"
    if counts["Pass"] == len(results):
        return "Passed"
    if counts["Pass"] + counts["Skipped"] == len(results):
        return "Passed"
    return "In Progress"
