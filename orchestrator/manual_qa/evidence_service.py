"""Evidence metadata attachment for Manual QA Phase 3A."""

from __future__ import annotations

from datetime import datetime, timedelta

from orchestrator.manual_qa.models import Evidence, TestRun


class EvidenceService:
    """Attach deterministic evidence metadata to a manual test run/result."""

    _BASE_TIME = datetime(2024, 1, 2, 0, 0, 0)

    def __init__(self) -> None:
        self._next_evidence_number = 1
        self._next_timestamp_offset = 0

    def attach_evidence(
        self,
        test_run: TestRun,
        test_case_id: str,
        evidence_type: str,
        path_or_url: str,
        description: str | None = None,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> Evidence:
        target_id = str(test_case_id or "").strip()
        if not target_id:
            raise ValueError("test_case_id is required")

        matching_result = next(
            (result for result in test_run.results if result.test_case_id == target_id),
            None,
        )
        if matching_result is None:
            raise ValueError(f"test_case_id '{target_id}' does not exist in run '{test_run.run_id}'")

        evidence = Evidence(
            evidence_id=f"EVD-{self._next_evidence_number:03d}",
            run_id=test_run.run_id,
            test_case_id=target_id,
            evidence_type=str(evidence_type or "").strip(),
            path_or_url=str(path_or_url or "").strip(),
            description=str(description or "").strip(),
            content_type=str(content_type or "").strip(),
            created_at=self._next_timestamp(),
            metadata=dict(metadata or {}),
        )
        self._next_evidence_number += 1

        evidence_ids = list(matching_result.metadata.get("evidence_ids", []))
        evidence_ids.append(evidence.evidence_id)
        matching_result.metadata["evidence_ids"] = evidence_ids

        evidence_records = list(matching_result.metadata.get("evidence", []))
        evidence_records.append(evidence.to_dict())
        matching_result.metadata["evidence"] = evidence_records

        run_evidence = list(test_run.metadata.get("evidence", []))
        run_evidence.append(evidence.to_dict())
        test_run.metadata["evidence"] = run_evidence

        return evidence

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_EVIDENCE_SERVICE = EvidenceService()


def attach_evidence(
    test_run: TestRun,
    test_case_id: str,
    evidence_type: str,
    path_or_url: str,
    description: str | None = None,
    content_type: str | None = None,
    metadata: dict | None = None,
) -> Evidence:
    """Convenience wrapper for deterministic evidence attachment."""

    return _DEFAULT_EVIDENCE_SERVICE.attach_evidence(
        test_run,
        test_case_id,
        evidence_type,
        path_or_url,
        description=description,
        content_type=content_type,
        metadata=metadata,
    )
