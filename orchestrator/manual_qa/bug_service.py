"""Bug draft generation for Manual QA Phase 3A."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from orchestrator.manual_qa.models import BugDraft, Evidence, ManualTestCase, TestRun


class BugDraftService:
    """Generate deterministic offline bug drafts from manual results."""

    _BASE_TIME = datetime(2024, 1, 3, 0, 0, 0)
    _ALLOWED_RESULT_STATUSES = {"Fail", "Blocked", "Retest"}

    def __init__(self) -> None:
        self._next_bug_number = 1
        self._next_timestamp_offset = 0

    def generate_bug_draft(
        self,
        test_run: TestRun,
        test_case_id: str,
        test_case: ManualTestCase | None = None,
        evidence: Evidence | Iterable[Evidence] | None = None,
        severity: str | None = None,
        priority: str | None = None,
        metadata: dict | None = None,
    ) -> BugDraft:
        target_id = str(test_case_id or "").strip()
        if not target_id:
            raise ValueError("test_case_id is required")

        matching_result = next(
            (result for result in test_run.results if result.test_case_id == target_id),
            None,
        )
        if matching_result is None:
            raise ValueError(f"test_case_id '{target_id}' does not exist in run '{test_run.run_id}'")

        if matching_result.status not in self._ALLOWED_RESULT_STATUSES:
            allowed = ", ".join(sorted(self._ALLOWED_RESULT_STATUSES))
            raise ValueError(
                f"Bug draft generation is only allowed for result statuses: {allowed}"
            )

        resolved_title = self._build_title(test_case_id=target_id, test_case=test_case)
        resolved_severity = str(severity or self._default_severity(matching_result.status)).strip()
        resolved_priority = str(priority or self._default_priority(matching_result.status)).strip()
        evidence_ids = self._resolve_evidence_ids(evidence)

        bug_draft = BugDraft(
            bug_id=f"BUG-{self._next_bug_number:03d}",
            run_id=test_run.run_id,
            test_case_id=target_id,
            title=resolved_title,
            severity=resolved_severity,
            priority=resolved_priority,
            environment=test_run.environment,
            build=test_run.build,
            steps_to_reproduce=list(test_case.steps) if test_case is not None else [],
            expected_result=test_case.expected_result if test_case is not None else "",
            actual_result=matching_result.actual_result,
            evidence_ids=evidence_ids,
            status="Draft",
            created_at=self._next_timestamp(),
            metadata=dict(metadata or {}),
        )
        self._next_bug_number += 1
        return bug_draft

    def _build_title(self, *, test_case_id: str, test_case: ManualTestCase | None) -> str:
        if test_case is not None and str(test_case.title).strip():
            return f"{test_case.title} - manual bug draft"
        return f"{test_case_id} - manual bug draft"

    def _resolve_evidence_ids(self, evidence: Evidence | Iterable[Evidence] | None) -> list[str]:
        if evidence is None:
            return []
        if isinstance(evidence, Evidence):
            return [evidence.evidence_id]
        return [item.evidence_id for item in evidence]

    def _default_severity(self, result_status: str) -> str:
        defaults = {
            "Fail": "Major",
            "Blocked": "Major",
            "Retest": "Minor",
        }
        return defaults[result_status]

    def _default_priority(self, result_status: str) -> str:
        defaults = {
            "Fail": "High",
            "Blocked": "High",
            "Retest": "Medium",
        }
        return defaults[result_status]

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_BUG_DRAFT_SERVICE = BugDraftService()


def generate_bug_draft(
    test_run: TestRun,
    test_case_id: str,
    test_case: ManualTestCase | None = None,
    evidence: Evidence | Iterable[Evidence] | None = None,
    severity: str | None = None,
    priority: str | None = None,
    metadata: dict | None = None,
) -> BugDraft:
    """Convenience wrapper for deterministic bug draft generation."""

    return _DEFAULT_BUG_DRAFT_SERVICE.generate_bug_draft(
        test_run,
        test_case_id,
        test_case=test_case,
        evidence=evidence,
        severity=severity,
        priority=priority,
        metadata=metadata,
    )
