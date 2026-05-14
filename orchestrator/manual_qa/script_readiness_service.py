"""Deterministic script draft readiness analysis for Manual QA."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Sequence

from orchestrator.manual_qa.models import (
    AutomationCandidate,
    ManualTestCase,
    ScriptGenerationGap,
    ScriptGenerationReadiness,
)


class ScriptReadinessService:
    """Analyze whether manual test cases are ready for future script drafting."""

    _BASE_TIME = datetime(2024, 1, 7, 0, 0, 0)
    _VAGUE_EXPECTED_TERMS = (
        "looks good",
        "visual judgment",
        "subjective",
        "manual observation",
        "ux feeling",
        "works correctly",
        "works as expected",
        "appropriate",
        "proper",
        "user friendly",
    )
    _MANUAL_ONLY_TERMS = (
        "visual judgment",
        "looks good",
        "ux feeling",
        "subjective",
        "manual observation",
    )
    _API_TERMS = ("api", "endpoint", "request", "response", "status code", "payload", "header", "token")
    _WEB_UI_TERMS = ("page", "button", "form", "field", "browser", "click", "login page", "ui")
    _MOBILE_TERMS = ("mobile", "app", "android", "ios", "tap", "permission", "push notification")
    _INTEGRATION_TERMS = ("workflow", "integration", "end-to-end", "cross-system")
    _UNIT_TERMS = ("function", "service", "class", "method", "unit")
    _SELECTOR_HINT_TERMS = (
        "button",
        "field",
        "input",
        "selector",
        "css",
        "xpath",
        "data-testid",
        "label",
        "placeholder",
        "link",
        "menu",
    )
    _ENDPOINT_HINT_TERMS = (
        "endpoint",
        "status code",
        "payload",
        "header",
        "get ",
        "post ",
        "put ",
        "delete ",
        "patch ",
        "/api",
        "/v1/",
        "/v2/",
    )
    _EXTERNAL_DEPENDENCY_TERMS = (
        "otp",
        "captcha",
        "third-party",
        "external payment",
        "email provider",
        "sms",
        "webhook",
        "bank",
    )
    _ENVIRONMENT_DEPENDENCY_TERMS = (
        "staging",
        "production",
        "prod",
        "environment",
        "vpn",
        "network dependency",
    )

    def __init__(self) -> None:
        self._next_readiness_number = 1
        self._next_gap_number = 1
        self._next_timestamp_offset = 0

    def analyze_script_readiness(
        self,
        test_case: ManualTestCase,
        automation_candidate: AutomationCandidate | None = None,
        project_type_hint: str | None = None,
        metadata: dict | None = None,
    ) -> ScriptGenerationReadiness:
        text = self._combined_text(test_case, project_type_hint=project_type_hint)
        target_type = self._classify_target_type(text)

        score = 50
        strengths: list[str] = []
        gaps: list[ScriptGenerationGap] = []

        if test_case.steps:
            score += 15
            strengths.append("Manual test case includes explicit execution steps.")
        else:
            score -= 20
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="missing_steps",
                    message="The test case does not contain execution steps.",
                    severity="High",
                    recommendation="Add clear ordered steps before attempting script draft generation.",
                )
            )

        if test_case.expected_result.strip():
            score += 15
            strengths.append("Expected result is present.")
        else:
            score -= 25
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="missing_expected_result",
                    message="The test case is missing an expected result.",
                    severity="High",
                    recommendation="Add an expected result with explicit assertions.",
                )
            )

        if test_case.requirement_ids:
            score += 10
            strengths.append("Requirement traceability is available.")
        else:
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="no_requirement_traceability",
                    message="The test case is not linked to a requirement.",
                    severity="Medium",
                    recommendation="Link the test case to one or more requirements.",
                )
            )

        if automation_candidate is not None and automation_candidate.recommendation == "Should Automate":
            score += 15
            strengths.append("Automation candidate analysis recommends automation.")

        if target_type != "unknown":
            score += 10
            strengths.append(f"Automation target is classifiable as {target_type}.")
        else:
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="target_unknown",
                    message="The automation target cannot be classified reliably.",
                    severity="Medium",
                    recommendation="Add clearer API, UI, mobile, unit, or integration hints.",
                )
            )

        if self._has_test_data(test_case):
            score += 5
            strengths.append("Test data hints are present in the test case.")
        else:
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="missing_test_data",
                    message="No explicit test data hints were detected.",
                    severity="Medium",
                    recommendation="Add concrete test data, payloads, credentials, or input examples.",
                )
            )

        if self._is_vague_expected_result(test_case.expected_result):
            score -= 20
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="vague_expected_result",
                    message="The expected result is too vague for reliable assertions.",
                    severity="High",
                    recommendation="Replace subjective or generic expectations with precise assertions.",
                )
            )

        if target_type == "manual_only":
            score -= 30
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="manual_judgment_required",
                    message="The test outcome depends on manual or subjective judgment.",
                    severity="Critical",
                    recommendation="Keep this test manual or redesign it around objective assertions.",
                )
            )

        if self._has_any(text, self._EXTERNAL_DEPENDENCY_TERMS):
            score -= 15
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="external_dependency",
                    message="The test case depends on external services or approvals.",
                    severity="Medium",
                    recommendation="Isolate or mock the external dependency before script drafting.",
                )
            )

        if self._has_any(text, self._ENVIRONMENT_DEPENDENCY_TERMS):
            score -= 10
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="environment_dependency",
                    message="The test case appears environment-sensitive.",
                    severity="Medium",
                    recommendation="Document the environment requirements or reduce environment coupling.",
                )
            )

        if target_type == "api" and not self._has_any(text, self._ENDPOINT_HINT_TERMS) and not self._contains_path_hint(text):
            score -= 15
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="missing_endpoint_hint",
                    message="API target detected but endpoint or request details are missing.",
                    severity="High",
                    recommendation="Add endpoint, method, payload, and expected status details.",
                )
            )

        if target_type == "web_ui" and not self._has_any(text, self._SELECTOR_HINT_TERMS):
            score -= 10
            gaps.append(
                self._gap(
                    test_case_id=test_case.test_case_id,
                    gap_type="missing_selector_hint",
                    message="Web UI target detected but selector or control hints are missing.",
                    severity="Medium",
                    recommendation="Add control identifiers, labels, selectors, or visible UI anchors.",
                )
            )

        score = max(0, min(100, score))

        high_severity_gap = any(gap.severity in {"High", "Critical"} for gap in gaps)
        critical_manual_gap = any(
            gap.gap_type == "manual_judgment_required" and gap.severity == "Critical"
            for gap in gaps
        )
        if critical_manual_gap or score < 40:
            readiness_status = "Not Suitable"
            suggested_next_step = "Keep as manual test or redesign test for automation"
        elif score >= 75 and not high_severity_gap:
            readiness_status = "Ready"
            suggested_next_step = "Proceed to script draft generation"
        else:
            readiness_status = "Needs More Data"
            suggested_next_step = "Add missing test data/selectors/endpoints/assertions before generation"

        readiness = ScriptGenerationReadiness(
            readiness_id=f"READ-{self._next_readiness_number:03d}",
            test_case_id=test_case.test_case_id,
            module=test_case.module,
            title=test_case.title,
            target_type=target_type,
            readiness_status=readiness_status,
            readiness_score=score,
            gaps=gaps,
            strengths=self._dedupe(strengths),
            suggested_next_step=suggested_next_step,
            automation_candidate_id=automation_candidate.candidate_id if automation_candidate is not None else "",
            created_at=self._next_timestamp(),
            metadata={
                "project_type_hint": str(project_type_hint or ""),
                **dict(metadata or {}),
            },
        )
        self._next_readiness_number += 1
        return readiness

    def analyze_script_readiness_batch(
        self,
        test_cases: Sequence[ManualTestCase],
        automation_candidates: Sequence[AutomationCandidate] | None = None,
        project_type_hint: str | None = None,
        metadata: dict | None = None,
    ) -> list[ScriptGenerationReadiness]:
        candidate_by_test_case_id = {
            item.test_case_id: item for item in (automation_candidates or [])
        }
        return [
            self.analyze_script_readiness(
                test_case,
                automation_candidate=candidate_by_test_case_id.get(test_case.test_case_id),
                project_type_hint=project_type_hint,
                metadata=metadata,
            )
            for test_case in test_cases
        ]

    def _classify_target_type(self, text: str) -> str:
        if self._has_any(text, self._MANUAL_ONLY_TERMS):
            return "manual_only"
        if self._has_any(text, self._API_TERMS) or self._contains_path_hint(text):
            return "api"
        if self._has_any(text, self._MOBILE_TERMS):
            return "mobile"
        if self._has_any(text, self._INTEGRATION_TERMS):
            return "integration"
        if self._has_any(text, self._UNIT_TERMS):
            return "unit"
        if self._has_any(text, self._WEB_UI_TERMS):
            return "web_ui"
        return "unknown"

    def _combined_text(self, test_case: ManualTestCase, *, project_type_hint: str | None) -> str:
        return " ".join(
            [
                test_case.module,
                test_case.title,
                test_case.expected_result,
                " ".join(test_case.preconditions),
                " ".join(test_case.steps),
                test_case.test_type,
                str(project_type_hint or ""),
                str(test_case.metadata.get("notes", "")),
                str(test_case.metadata.get("selector_hints", "")),
                str(test_case.metadata.get("endpoint_hints", "")),
            ]
        ).lower()

    def _has_test_data(self, test_case: ManualTestCase) -> bool:
        text = " ".join(
            [
                " ".join(test_case.preconditions),
                " ".join(test_case.steps),
                test_case.expected_result,
                str(test_case.metadata.get("test_data", "")),
            ]
        ).lower()
        data_terms = (
            "valid",
            "invalid",
            "email",
            "password",
            "query",
            "payload",
            "username",
            "token",
            "id ",
            "record",
            "user ",
            "account",
        )
        return self._has_any(text, data_terms) or bool(re.search(r"\b\d+\b", text))

    def _is_vague_expected_result(self, expected_result: str) -> bool:
        text = str(expected_result or "").strip().lower()
        if not text:
            return False
        return self._has_any(text, self._VAGUE_EXPECTED_TERMS)

    def _contains_path_hint(self, text: str) -> bool:
        return bool(re.search(r"/[a-z0-9/_-]+", text))

    def _has_any(self, text: str, needles: Sequence[str]) -> bool:
        haystack = str(text or "").lower()
        for needle in needles:
            term = str(needle).lower()
            if re.search(self._needle_pattern(term), haystack):
                return True
        return False

    def _dedupe(self, items: Sequence[str]) -> list[str]:
        values: list[str] = []
        for item in items:
            clean = str(item or "").strip()
            if clean and clean not in values:
                values.append(clean)
        return values

    def _needle_pattern(self, term: str) -> str:
        if re.fullmatch(r"[a-z0-9 ]+", term):
            normalized = r"\s+".join(re.escape(part) for part in term.split())
            return rf"\b{normalized}\b"
        return re.escape(term)

    def _gap(
        self,
        *,
        test_case_id: str,
        gap_type: str,
        message: str,
        severity: str,
        recommendation: str,
    ) -> ScriptGenerationGap:
        gap = ScriptGenerationGap(
            gap_id=f"GAP-{self._next_gap_number:03d}",
            test_case_id=test_case_id,
            gap_type=gap_type,
            message=message,
            severity=severity,
            recommendation=recommendation,
        )
        self._next_gap_number += 1
        return gap

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_SCRIPT_READINESS_SERVICE = ScriptReadinessService()


def analyze_script_readiness(
    test_case: ManualTestCase,
    automation_candidate: AutomationCandidate | None = None,
    project_type_hint: str | None = None,
    metadata: dict | None = None,
) -> ScriptGenerationReadiness:
    """Convenience wrapper for deterministic script readiness analysis."""

    return _DEFAULT_SCRIPT_READINESS_SERVICE.analyze_script_readiness(
        test_case,
        automation_candidate=automation_candidate,
        project_type_hint=project_type_hint,
        metadata=metadata,
    )


def analyze_script_readiness_batch(
    test_cases: Sequence[ManualTestCase],
    automation_candidates: Sequence[AutomationCandidate] | None = None,
    project_type_hint: str | None = None,
    metadata: dict | None = None,
) -> list[ScriptGenerationReadiness]:
    """Convenience wrapper for batch readiness analysis in input order."""

    return _DEFAULT_SCRIPT_READINESS_SERVICE.analyze_script_readiness_batch(
        test_cases,
        automation_candidates=automation_candidates,
        project_type_hint=project_type_hint,
        metadata=metadata,
    )
