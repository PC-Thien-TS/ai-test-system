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
