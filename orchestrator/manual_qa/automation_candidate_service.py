"""Deterministic automation candidate scoring for Manual QA Phase 4."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from orchestrator.manual_qa.models import AutomationCandidate, FailureRecord, ManualTestCase, TestResult


class AutomationCandidateService:
    """Score manual test cases for future automation suitability."""

    _BASE_TIME = datetime(2024, 1, 5, 0, 0, 0)
    _CRITICAL_BLOCKER_TERMS = (
        "captcha",
        "manual approval",
        "physical device",
        "external payment without mock",
        "missing expected result",
        "subjective visual judgment",
    )

    def __init__(self) -> None:
        self._next_candidate_number = 1
        self._next_timestamp_offset = 0

    def score_automation_candidate(
        self,
        test_case: ManualTestCase,
        test_result: TestResult | None = None,
        failure_records: Sequence[FailureRecord] | None = None,
        module_hint: str | None = None,
        test_type_hint: str | None = None,
        metadata: dict | None = None,
    ) -> AutomationCandidate:
        working_metadata = dict(test_case.metadata)
        working_metadata.update(dict(metadata or {}))

        text = " ".join(
            [
                test_case.module,
                test_case.title,
                test_case.expected_result,
                " ".join(test_case.steps),
                test_case.test_type,
                str(module_hint or ""),
                str(test_type_hint or ""),
                str(working_metadata.get("notes", "")),
            ]
        ).lower()

        score = 0
        reasons: list[str] = []
        blockers: list[str] = []
        critical_blockers: list[str] = []

        normalized_type = (test_type_hint or test_case.test_type or "").strip().lower()
        normalized_priority = (test_case.priority or "").strip().lower()

        if self._has_any(text, ("smoke", "regression")) or self._has_any(normalized_type, ("smoke", "regression")):
            score += 20
            reasons.append("Smoke or regression coverage benefits from repeatable automation.")

        if self._has_any(text, ("login", "search", "create", "update", "delete")):
            score += 10
            reasons.append("Functional CRUD or access flow is a strong automation target.")

        if test_case.steps and test_case.expected_result:
            score += 15
            reasons.append("Test case provides explicit steps and expected result.")

        if self._has_stable_expected_result(test_case.expected_result):
            score += 15
            reasons.append("Expected result is deterministic and machine-checkable.")

        matching_failure_records = self._matching_failure_records(test_case, failure_records or [])
        if any(record.occurrence_count >= 2 for record in matching_failure_records):
            score += 10
            reasons.append("Repeated failure history increases automation value.")

        if normalized_priority == "high":
            score += 10
            reasons.append("High-priority coverage is worth automating sooner.")

        if self._has_any(text, ("authentication", "auth", "payment", "order", "search", "store", "profile", "api")):
            score += 5
            reasons.append("Module is a common automation-friendly business flow.")

        if test_case.requirement_ids:
            score += 5
            reasons.append("Requirement traceability is present.")
        else:
            score -= 10
            blockers.append("No requirement traceability.")

        if self._has_any(text, ("exploratory", "usability", "visual judgment", "manual judgment", "ux feeling")):
            score -= 25
            blockers.append("Exploratory or judgment-heavy coverage is difficult to automate reliably.")

        if not self._has_stable_expected_result(test_case.expected_result):
            score -= 20
            blockers.append("Expected result is vague or subjective.")

        critical_phrase_matches = [
            ("captcha", "Requires captcha."),
            ("manual approval", "Requires manual approval."),
            ("external payment without mock", "Requires external payment without mock."),
            ("otp", "Requires OTP."),
            ("physical device", "Requires physical device."),
            ("hardware", "Requires hardware interaction."),
            ("manual observation", "Requires manual observation."),
        ]
        for needle, message in critical_phrase_matches:
            if needle in text:
                score -= 25
                blockers.append(message)
                if needle in self._CRITICAL_BLOCKER_TERMS or needle in {"otp", "hardware", "manual observation"}:
                    critical_blockers.append(message)

        if test_result is not None and test_result.status in {"Skipped", "Blocked"}:
            score -= 15
            blockers.append(f"Recent result status '{test_result.status}' suggests environment sensitivity.")

        if not test_case.steps or not test_case.expected_result:
            score -= 20
            blockers.append("Missing steps or expected result.")
            if not test_case.expected_result:
                critical_blockers.append("Missing expected result.")

        if self._has_any(text, ("visual only", "looks good", "manual judgment", "ux feeling")):
            score -= 20
            blockers.append("Outcome depends on subjective visual judgment.")
            critical_blockers.append("Subjective visual judgment.")

        score = max(0, min(100, score))
        suggested_automation_type = self._suggest_automation_type(
            text=text,
            blockers=blockers,
            module_hint=module_hint,
        )
        recommendation = self._recommend(score, blockers, critical_blockers)

        candidate = AutomationCandidate(
            candidate_id=f"AUTO-{self._next_candidate_number:03d}",
            test_case_id=test_case.test_case_id,
            requirement_ids=list(test_case.requirement_ids),
            module=(module_hint or test_case.module or "").strip(),
            title=test_case.title,
            score=score,
            recommendation=recommendation,
            reasons=self._dedupe(reasons),
            blockers=self._dedupe(blockers),
            suggested_automation_type=suggested_automation_type,
            related_failure_record_ids=[record.record_id for record in matching_failure_records],
            created_at=self._next_timestamp(),
            metadata={
                **working_metadata,
                "test_type_hint": test_type_hint or "",
                "critical_blockers": self._dedupe(critical_blockers),
            },
        )
        self._next_candidate_number += 1
        return candidate

    def score_automation_candidates(
        self,
        test_cases: Sequence[ManualTestCase],
        test_results: Sequence[TestResult] | None = None,
        failure_records: Sequence[FailureRecord] | None = None,
        metadata: dict | None = None,
    ) -> list[AutomationCandidate]:
        result_by_test_case_id = {
            result.test_case_id: result for result in (test_results or [])
        }
        return [
            self.score_automation_candidate(
                test_case,
                test_result=result_by_test_case_id.get(test_case.test_case_id),
                failure_records=failure_records,
                metadata=metadata,
            )
            for test_case in test_cases
        ]

    def _matching_failure_records(
        self,
        test_case: ManualTestCase,
        failure_records: Sequence[FailureRecord],
    ) -> list[FailureRecord]:
        matched: list[FailureRecord] = []
        for record in failure_records:
            signature = record.signature
            if signature.test_case_id == test_case.test_case_id:
                matched.append(record)
                continue
            if signature.module and signature.module.lower() == test_case.module.lower():
                if self._tokenize(signature.title) & self._tokenize(test_case.title):
                    matched.append(record)
        return matched

    def _has_stable_expected_result(self, expected_result: str) -> bool:
        text = (expected_result or "").strip().lower()
        if not text:
            return False
        subjective_terms = (
            "looks good",
            "good",
            "nice",
            "user friendly",
            "subjective",
            "visual only",
            "manual judgment",
            "ux feeling",
        )
        return not self._has_any(text, subjective_terms)

    def _suggest_automation_type(
        self,
        *,
        text: str,
        blockers: Sequence[str],
        module_hint: str | None,
    ) -> str:
        combined = " ".join([text, str(module_hint or "").lower()])
        blockers_text = " ".join(blockers).lower()
        if self._has_any(blockers_text, ("subjective", "manual approval", "manual observation", "physical device")):
            return "manual_only"
        if self._has_any(combined, ("api", "endpoint", "status code", "request", "response")):
            return "api"
        if self._has_any(combined, ("mobile", "android", "ios", "app")):
            return "mobile"
        if self._has_any(combined, ("unit", "function", "service")):
            return "unit"
        if self._has_any(combined, ("integration", "workflow")):
            return "integration"
        if self._has_any(combined, ("visual only", "looks good", "manual judgment", "ux feeling")):
            return "manual_only"
        if combined.strip():
            return "web_ui"
        return "unknown"

    def _recommend(self, score: int, blockers: Sequence[str], critical_blockers: Sequence[str]) -> str:
        if critical_blockers:
            return "Do Not Automate"
        if score >= 70:
            return "Should Automate"
        if 40 <= score <= 69:
            return "Consider Later"
        return "Do Not Automate"

    def _has_any(self, text: str, needles: Iterable[str]) -> bool:
        haystack = str(text or "").lower()
        return any(str(needle).lower() in haystack for needle in needles)

    def _dedupe(self, items: Sequence[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            text = str(item or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_AUTOMATION_CANDIDATE_SERVICE = AutomationCandidateService()


def score_automation_candidate(
    test_case: ManualTestCase,
    test_result: TestResult | None = None,
    failure_records: Sequence[FailureRecord] | None = None,
    module_hint: str | None = None,
    test_type_hint: str | None = None,
    metadata: dict | None = None,
) -> AutomationCandidate:
    """Convenience wrapper for deterministic automation candidate scoring."""

    return _DEFAULT_AUTOMATION_CANDIDATE_SERVICE.score_automation_candidate(
        test_case,
        test_result=test_result,
        failure_records=failure_records,
        module_hint=module_hint,
        test_type_hint=test_type_hint,
        metadata=metadata,
    )


def score_automation_candidates(
    test_cases: Sequence[ManualTestCase],
    test_results: Sequence[TestResult] | None = None,
    failure_records: Sequence[FailureRecord] | None = None,
    metadata: dict | None = None,
) -> list[AutomationCandidate]:
    """Convenience wrapper for scoring multiple manual test cases in order."""

    return _DEFAULT_AUTOMATION_CANDIDATE_SERVICE.score_automation_candidates(
        test_cases,
        test_results=test_results,
        failure_records=failure_records,
        metadata=metadata,
    )
