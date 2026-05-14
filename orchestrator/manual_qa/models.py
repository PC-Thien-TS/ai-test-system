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
