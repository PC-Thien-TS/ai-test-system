"""Deterministic in-memory failure memory for Manual QA Phase 3B."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Iterable

from orchestrator.manual_qa.models import BugDraft, FailureRecord, FailureSignature


class FailureMemoryService:
    """Create, remember, and query deterministic manual failure records."""

    _BASE_TIME = datetime(2024, 1, 4, 0, 0, 0)

    def __init__(self) -> None:
        self._next_signature_number = 1
        self._next_record_number = 1
        self._next_timestamp_offset = 0
        self._records_by_fingerprint: dict[str, FailureRecord] = {}

    def create_failure_signature(
        self,
        *,
        module: str = "",
        test_case_id: str = "",
        title: str = "",
        symptom: str = "",
        expected_result: str = "",
        actual_result: str = "",
        environment: str = "",
        build: str = "",
        severity: str = "",
        priority: str = "",
        source_bug_id: str = "",
        tags: Iterable[str] | None = None,
        metadata: dict | None = None,
    ) -> FailureSignature:
        normalized_title = str(title or "").strip()
        normalized_symptom = str(symptom or "").strip()
        normalized_expected = str(expected_result or "").strip()
        normalized_actual = str(actual_result or "").strip()
        normalized_module = str(module or "").strip()
        normalized_environment = str(environment or "").strip()
        normalized_build = str(build or "").strip()
        normalized_test_case_id = str(test_case_id or "").strip()
        normalized_severity = str(severity or "").strip()
        normalized_priority = str(priority or "").strip()
        normalized_source_bug_id = str(source_bug_id or "").strip()

        fingerprint = self._build_fingerprint(
            module=normalized_module,
            title=normalized_title,
            symptom=normalized_symptom,
            expected_result=normalized_expected,
            actual_result=normalized_actual,
            environment=normalized_environment,
            build=normalized_build,
        )

        signature = FailureSignature(
            signature_id=f"FSIG-{self._next_signature_number:03d}",
            fingerprint=fingerprint,
            module=normalized_module,
            test_case_id=normalized_test_case_id,
            title=normalized_title,
            symptom=normalized_symptom or normalized_actual or normalized_title,
            expected_result=normalized_expected,
            actual_result=normalized_actual,
            environment=normalized_environment,
            build=normalized_build,
            severity=normalized_severity,
            priority=normalized_priority,
            source_bug_id=normalized_source_bug_id,
            tags=self._normalize_list(tags),
            created_at=self._next_timestamp(),
            metadata=dict(metadata or {}),
        )
        self._next_signature_number += 1
        return signature

    def create_failure_signature_from_bug_draft(self, bug_draft: BugDraft) -> FailureSignature:
        metadata = dict(bug_draft.metadata)
        metadata.setdefault("run_id", bug_draft.run_id)
        return self.create_failure_signature(
            module=str(metadata.get("module", "")).strip(),
            test_case_id=bug_draft.test_case_id,
            title=bug_draft.title,
            symptom=bug_draft.actual_result or bug_draft.title,
            expected_result=bug_draft.expected_result,
            actual_result=bug_draft.actual_result,
            environment=bug_draft.environment,
            build=bug_draft.build,
            severity=bug_draft.severity,
            priority=bug_draft.priority,
            source_bug_id=bug_draft.bug_id,
            tags=metadata.get("tags", []),
            metadata=metadata,
        )

    def remember_failure(self, signature: FailureSignature) -> FailureRecord:
        existing = self._records_by_fingerprint.get(signature.fingerprint)
        if existing is not None:
            existing.occurrence_count += 1
            existing.last_seen = signature.created_at
            self._append_unique(existing.related_bug_ids, signature.source_bug_id)
            self._append_unique(
                existing.related_run_ids,
                str(signature.metadata.get("run_id", "")).strip(),
            )
            self._append_unique(existing.related_test_case_ids, signature.test_case_id)
            self._append_unique(existing.notes, str(signature.metadata.get("note", "")).strip())
            return existing

        record = FailureRecord(
            record_id=f"FMEM-{self._next_record_number:03d}",
            signature=signature,
            occurrence_count=1,
            first_seen=signature.created_at,
            last_seen=signature.created_at,
            related_bug_ids=[signature.source_bug_id] if signature.source_bug_id else [],
            related_run_ids=[str(signature.metadata.get("run_id", "")).strip()]
            if str(signature.metadata.get("run_id", "")).strip()
            else [],
            related_test_case_ids=[signature.test_case_id] if signature.test_case_id else [],
            notes=[str(signature.metadata.get("note", "")).strip()]
            if str(signature.metadata.get("note", "")).strip()
            else [],
            metadata=dict(signature.metadata),
        )
        self._records_by_fingerprint[signature.fingerprint] = record
        self._next_record_number += 1
        return record

    def find_exact_failure(self, fingerprint: str) -> FailureRecord | None:
        return self._records_by_fingerprint.get(str(fingerprint or "").strip())

    def find_similar_failures(
        self,
        signature: FailureSignature | None = None,
        *,
        module: str = "",
        test_case_id: str = "",
        title: str = "",
        symptom: str = "",
        actual_result: str = "",
        severity: str = "",
        priority: str = "",
        limit: int = 5,
    ) -> list[FailureRecord]:
        if signature is not None:
            module = signature.module
            test_case_id = signature.test_case_id
            title = signature.title
            symptom = signature.symptom
            actual_result = signature.actual_result
            severity = signature.severity
            priority = signature.priority

        ranked: list[tuple[int, FailureRecord]] = []
        for record in self._records_by_fingerprint.values():
            score = self._similarity_score(
                record=record,
                module=module,
                test_case_id=test_case_id,
                title=title,
                symptom=symptom,
                actual_result=actual_result,
                severity=severity,
                priority=priority,
            )
            if score <= 0:
                continue
            ranked.append((score, record))

        ranked.sort(key=lambda item: (-item[0], item[1].record_id))
        return [self._copy_record_with_score(record, score) for score, record in ranked[:limit]]

    def _build_fingerprint(
        self,
        *,
        module: str,
        title: str,
        symptom: str,
        expected_result: str,
        actual_result: str,
        environment: str,
        build: str,
    ) -> str:
        basis = "||".join(
            [
                self._normalize_text(module),
                self._normalize_text(symptom or title),
                self._normalize_text(expected_result),
                self._normalize_text(actual_result),
                self._normalize_text(environment),
                self._normalize_text(build),
            ]
        )
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12].upper()
        return f"FP-{digest}"

    def _similarity_score(
        self,
        *,
        record: FailureRecord,
        module: str,
        test_case_id: str,
        title: str,
        symptom: str,
        actual_result: str,
        severity: str,
        priority: str,
    ) -> int:
        record_signature = record.signature
        score = 0

        if self._normalize_text(module) and self._normalize_text(module) == self._normalize_text(record_signature.module):
            score += 4
        if str(test_case_id).strip() and str(test_case_id).strip() == record_signature.test_case_id:
            score += 3

        query_tokens = self._tokenize(" ".join([title, symptom, actual_result]))
        record_tokens = self._tokenize(
            " ".join([record_signature.title, record_signature.symptom, record_signature.actual_result])
        )
        overlap = len(query_tokens & record_tokens)
        score += min(overlap * 2, 8)

        actual_tokens = self._tokenize(actual_result)
        record_actual_tokens = self._tokenize(record_signature.actual_result)
        score += min(len(actual_tokens & record_actual_tokens), 4)

        if str(severity).strip() and str(severity).strip().lower() == record_signature.severity.lower():
            score += 1
        if str(priority).strip() and str(priority).strip().lower() == record_signature.priority.lower():
            score += 1

        return score

    def _copy_record_with_score(self, record: FailureRecord, score: int) -> FailureRecord:
        metadata = dict(record.metadata)
        metadata["similarity_score"] = score
        return FailureRecord(
            record_id=record.record_id,
            signature=record.signature,
            occurrence_count=record.occurrence_count,
            first_seen=record.first_seen,
            last_seen=record.last_seen,
            related_bug_ids=list(record.related_bug_ids),
            related_run_ids=list(record.related_run_ids),
            related_test_case_ids=list(record.related_test_case_ids),
            notes=list(record.notes),
            metadata=metadata,
        )

    def _append_unique(self, target: list[str], value: str) -> None:
        normalized = str(value or "").strip()
        if normalized and normalized not in target:
            target.append(normalized)

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    def _tokenize(self, value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", self._normalize_text(value))
            if len(token) > 2
        }

    def _normalize_list(self, items: Iterable[str] | None) -> list[str]:
        normalized: list[str] = []
        for item in items or []:
            text = str(item or "").strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_FAILURE_MEMORY_SERVICE = FailureMemoryService()


def create_failure_signature(**kwargs: object) -> FailureSignature:
    """Convenience wrapper for deterministic failure signature creation."""

    return _DEFAULT_FAILURE_MEMORY_SERVICE.create_failure_signature(**kwargs)


def create_failure_signature_from_bug_draft(bug_draft: BugDraft) -> FailureSignature:
    """Convenience wrapper for BugDraft-to-signature mapping."""

    return _DEFAULT_FAILURE_MEMORY_SERVICE.create_failure_signature_from_bug_draft(bug_draft)


def remember_failure(signature: FailureSignature) -> FailureRecord:
    """Convenience wrapper for deterministic failure memory update."""

    return _DEFAULT_FAILURE_MEMORY_SERVICE.remember_failure(signature)


def find_exact_failure(fingerprint: str) -> FailureRecord | None:
    """Convenience wrapper for exact fingerprint lookup."""

    return _DEFAULT_FAILURE_MEMORY_SERVICE.find_exact_failure(fingerprint)


def find_similar_failures(
    signature: FailureSignature | None = None,
    **kwargs: object,
) -> list[FailureRecord]:
    """Convenience wrapper for deterministic similar-failure lookup."""

    return _DEFAULT_FAILURE_MEMORY_SERVICE.find_similar_failures(signature, **kwargs)
