"""Deterministic readiness analysis for future Web Playwright draft generation."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Sequence

from orchestrator.manual_qa.models import (
    AutomationCandidate,
    ManualTestCase,
    ScriptGenerationReadiness,
    WebPlaywrightGap,
    WebPlaywrightReadiness,
)


class WebPlaywrightReadinessService:
    """Analyze whether web UI-like manual cases are ready for Playwright drafting."""

    _BASE_TIME = datetime(2024, 1, 11, 0, 0, 0)
    _WEB_UI_TERMS = (
        "page",
        "screen",
        "form",
        "field",
        "button",
        "link",
        "dropdown",
        "modal",
        "table",
        "browser",
        "click",
        "submit",
        "login page",
        "homepage",
        "dashboard",
        "navbar",
        "sidebar",
        "search box",
    )
    _MANUAL_ONLY_TERMS = (
        "visual judgment",
        "looks good",
        "ux feeling",
        "subjective",
        "manual observation",
        "visual only",
    )
    _ACTION_TERMS = (
        "click",
        "fill",
        "type",
        "select",
        "upload",
        "download",
        "submit",
        "navigate",
        "hover",
        "check",
        "uncheck",
        "tap",
    )
    _ASSERTION_TERMS = (
        "should see",
        "displays",
        "redirects",
        "status message",
        "validation error",
        "success message",
        "table contains",
        "url contains",
        "element visible",
        "user lands on",
        "dashboard appears",
        "message appears",
        "shown",
        "visible",
    )
    _SESSION_TERMS = ("login", "sign in", "session", "authenticated", "logged in")
    _DYNAMIC_TERMS = ("dynamic", "flaky", "animation", "timing", "async", "auto-refresh", "polling")
    _FILE_TERMS = ("file upload", "upload file", "download file", "download csv", "attachment")
    _EXTERNAL_BLOCKER_TERMS = (
        "otp",
        "captcha",
        "manual approval",
        "external payment",
        "payment gateway",
        "bank redirect",
    )

    def __init__(self) -> None:
        self._next_readiness_number = 1
        self._next_gap_number = 1
        self._next_timestamp_offset = 0

    def analyze_web_playwright_readiness(
        self,
        test_case: ManualTestCase,
        script_readiness: ScriptGenerationReadiness | None = None,
        automation_candidate: AutomationCandidate | None = None,
        project_type_hint: str | None = None,
        metadata: dict | None = None,
    ) -> WebPlaywrightReadiness:
        text = self._combined_text(test_case, project_type_hint=project_type_hint)
        page_text = self._page_context_text(test_case)
        action_text = self._action_context_text(test_case)
        assertion_text = self._assertion_context_text(test_case)
        target_type = script_readiness.target_type if script_readiness is not None else ""
        web_ui_like = target_type in {"web_ui", "manual_only"} or self._looks_web_ui_like(text)

        score = 50
        strengths: list[str] = []
        gaps: list[WebPlaywrightGap] = []
        page_url = self._detect_page_url(page_text)
        selector_hints = self._detect_selector_hints(text)
        action_hints = self._detect_action_hints(action_text)
        assertion_hints = self._detect_assertion_hints(assertion_text)

        if not web_ui_like or target_type in {"api", "mobile", "unit"}:
            score = 0
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "not_web_ui_target",
                    "The test case is not a web UI automation target.",
                    "Critical",
                    "Keep this test in its current automation domain or evaluate a different generator path.",
                )
            )
        if target_type == "manual_only" or self._has_any(text, self._MANUAL_ONLY_TERMS):
            score -= 30
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "visual_manual_judgment",
                    "The test depends on subjective visual or manual judgment.",
                    "Critical",
                    "Keep as manual test or redesign it around objective DOM-based assertions.",
                )
            )

        if page_url:
            score += 15
            strengths.append("Page URL or route hint is present.")
        else:
            score -= 15
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "missing_page_url",
                    "No page URL or route hint was detected.",
                    "High",
                    "Add the page URL or route path before Playwright draft generation.",
                )
            )

        if selector_hints:
            score += 15
            strengths.append("Selector or control hints are present.")
        else:
            score -= 20
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "missing_selector_hints",
                    "No selector or control hints were detected.",
                    "High",
                    "Add data-testid, role, id, label, button text, or other stable UI anchors.",
                )
            )

        if action_hints:
            score += 15
            strengths.append("User actions are explicit.")
        else:
            score -= 20
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "missing_user_action_details",
                    "User actions are missing or too vague for Playwright drafting.",
                    "High",
                    "Add explicit actions such as click, fill, select, submit, or navigate.",
                )
            )

        if assertion_hints:
            score += 15
            strengths.append("Expected UI assertions are explicit.")
        else:
            score -= 20
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "missing_assertion",
                    "Expected UI assertion details are missing.",
                    "High",
                    "Add visible element, URL, message, or table assertions for the outcome.",
                )
            )

        if test_case.requirement_ids:
            score += 10
            strengths.append("Requirement traceability is available.")

        if automation_candidate is not None and automation_candidate.recommendation == "Should Automate":
            score += 10
            strengths.append("Automation candidate analysis recommends automation.")

        if script_readiness is not None and script_readiness.readiness_status == "Ready":
            score += 10
            strengths.append("Upstream script readiness analysis marked the case as Ready.")

        if self._has_any(text, self._SESSION_TERMS):
            score -= 10
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "login_session_dependency",
                    "The test appears to depend on login or session setup.",
                    "Medium",
                    "Document session setup and add stable auth-state or login details before generation.",
                )
            )

        if self._has_any(text, self._DYNAMIC_TERMS):
            score -= 15
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "dynamic_flaky_ui_dependency",
                    "The case appears to depend on dynamic or timing-sensitive UI behavior.",
                    "High",
                    "Add stable waiting conditions or redesign the scenario around deterministic states.",
                )
            )

        if self._has_any(text, self._FILE_TERMS):
            score -= 10
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "file_upload_download_complexity",
                    "The case includes file upload or download handling complexity.",
                    "Medium",
                    "Document file handling details and expected browser interactions before generation.",
                )
            )

        if self._has_any(text, self._EXTERNAL_BLOCKER_TERMS):
            score -= 30
            gaps.append(
                self._gap(
                    test_case.test_case_id,
                    "external_blocker_dependency",
                    "The case depends on OTP, captcha, manual approval, or external payment behavior.",
                    "Critical",
                    "Keep this test manual or redesign it around a safe mocked flow before generation.",
                )
            )

        score = max(0, min(100, score))
        critical_gap = any(gap.severity == "Critical" for gap in gaps)
        high_gap = any(gap.severity == "High" for gap in gaps)
        if critical_gap or score < 40:
            readiness_status = "Not Suitable"
            suggested_next_step = "Keep as manual test or redesign test for stable web automation"
        elif score >= 75 and not high_gap:
            readiness_status = "Ready"
            suggested_next_step = "Proceed to Playwright script draft generation"
        else:
            readiness_status = "Needs More Data"
            suggested_next_step = "Add URL, selector, action, and assertion details before generation"

        readiness = WebPlaywrightReadiness(
            readiness_id=f"WPREAD-{self._next_readiness_number:03d}",
            test_case_id=test_case.test_case_id,
            requirement_ids=list(test_case.requirement_ids),
            module=test_case.module,
            title=test_case.title,
            readiness_status=readiness_status,
            readiness_score=score,
            page_url=page_url or "",
            selector_hints=selector_hints,
            action_hints=action_hints,
            assertion_hints=assertion_hints,
            gaps=gaps,
            strengths=self._dedupe(strengths),
            suggested_next_step=suggested_next_step,
            automation_candidate_id=automation_candidate.candidate_id if automation_candidate is not None else "",
            created_at=self._next_timestamp(),
            metadata={
                "project_type_hint": str(project_type_hint or ""),
                "upstream_target_type": target_type,
                **dict(metadata or {}),
            },
        )
        self._next_readiness_number += 1
        return readiness

    def analyze_web_playwright_readiness_batch(
        self,
        test_cases: Sequence[ManualTestCase],
        script_readiness_items: Sequence[ScriptGenerationReadiness] | None = None,
        automation_candidates: Sequence[AutomationCandidate] | None = None,
        project_type_hint: str | None = None,
        metadata: dict | None = None,
    ) -> list[WebPlaywrightReadiness]:
        readiness_by_case_id = {item.test_case_id: item for item in (script_readiness_items or [])}
        candidate_by_case_id = {item.test_case_id: item for item in (automation_candidates or [])}
        results: list[WebPlaywrightReadiness] = []
        for test_case in test_cases:
            script_readiness = readiness_by_case_id.get(test_case.test_case_id)
            text = self._combined_text(test_case, project_type_hint=project_type_hint)
            target_type = script_readiness.target_type if script_readiness is not None else ""
            if not (
                target_type in {"web_ui", "manual_only"}
                or self._looks_web_ui_like(text)
            ):
                continue
            results.append(
                self.analyze_web_playwright_readiness(
                    test_case,
                    script_readiness=script_readiness,
                    automation_candidate=candidate_by_case_id.get(test_case.test_case_id),
                    project_type_hint=project_type_hint,
                    metadata=metadata,
                )
            )
        return results

    def _combined_text(self, test_case: ManualTestCase, *, project_type_hint: str | None) -> str:
        return " ".join(
            [
                test_case.module,
                test_case.title,
                " ".join(test_case.preconditions),
                " ".join(test_case.steps),
                test_case.expected_result,
                test_case.test_type,
                str(project_type_hint or ""),
                str(test_case.metadata.get("selector_hints", "")),
                str(test_case.metadata.get("page_url", "")),
                str(test_case.metadata.get("notes", "")),
            ]
        ).lower()

    def _page_context_text(self, test_case: ManualTestCase) -> str:
        return " ".join(
            [
                test_case.module,
                test_case.title,
                " ".join(test_case.preconditions),
                " ".join(test_case.steps),
                str(test_case.metadata.get("page_url", "")),
            ]
        ).lower()

    def _action_context_text(self, test_case: ManualTestCase) -> str:
        return " ".join(
            [
                test_case.title,
                " ".join(test_case.steps),
                str(test_case.metadata.get("selector_hints", "")),
            ]
        ).lower()

    def _assertion_context_text(self, test_case: ManualTestCase) -> str:
        return " ".join([test_case.expected_result, " ".join(test_case.steps)]).lower()

    def _looks_web_ui_like(self, text: str) -> bool:
        return self._has_any(text, self._WEB_UI_TERMS)

    def _detect_page_url(self, text: str) -> str | None:
        full_url = re.search(r"https?://[^\s'\"`]+", text)
        if full_url:
            return full_url.group(0).rstrip(".,;:)")
        route = re.search(r"(?<!api)(/[a-z0-9][a-z0-9/_-]*)", text)
        if route:
            return route.group(1).rstrip(".,;:)")
        return None

    def _detect_selector_hints(self, text: str) -> list[str]:
        hints: list[str] = []
        patterns = (
            r"data-testid[=\s:\"'-]+[a-z0-9_-]+",
            r"id=[\"']?[a-z0-9_-]+",
            r"#[a-z0-9_-]+",
            r"\.[a-z0-9_-]+",
            r"role=[\"']?[a-z0-9_-]+",
            r"aria-label[=\s:\"'-]+[a-z0-9 _-]+",
            r"button text[=\s:\"'-]+[a-z0-9 _-]+",
            r"field label[=\s:\"'-]+[a-z0-9 _-]+",
            r"search box",
        )
        for pattern in patterns:
            for match in re.findall(pattern, text):
                clean = str(match).strip().rstrip(".,;:)")
                if clean and clean not in hints:
                    hints.append(clean)
        return hints

    def _detect_action_hints(self, text: str) -> list[str]:
        hints: list[str] = []
        for term in self._ACTION_TERMS:
            if self._has_any(text, (term,)):
                hints.append(term)
        return hints

    def _detect_assertion_hints(self, text: str) -> list[str]:
        hints: list[str] = []
        for term in self._ASSERTION_TERMS:
            if self._has_any(text, (term,)):
                hints.append(term)
        return hints

    def _has_any(self, text: str, needles: Sequence[str]) -> bool:
        haystack = str(text or "").lower()
        for needle in needles:
            term = str(needle).lower()
            if re.search(self._needle_pattern(term), haystack):
                return True
        return False

    def _needle_pattern(self, term: str) -> str:
        if re.fullmatch(r"[a-z0-9 ]+", term):
            normalized = r"\s+".join(re.escape(part) for part in term.split())
            return rf"\b{normalized}\b"
        return re.escape(term)

    def _dedupe(self, items: Sequence[str]) -> list[str]:
        values: list[str] = []
        for item in items:
            clean = str(item or "").strip()
            if clean and clean not in values:
                values.append(clean)
        return values

    def _gap(
        self,
        test_case_id: str,
        gap_type: str,
        message: str,
        severity: str,
        recommendation: str,
    ) -> WebPlaywrightGap:
        gap = WebPlaywrightGap(
            gap_id=f"WPGAP-{self._next_gap_number:03d}",
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


_DEFAULT_WEB_PLAYWRIGHT_READINESS_SERVICE = WebPlaywrightReadinessService()


def analyze_web_playwright_readiness(
    test_case: ManualTestCase,
    script_readiness: ScriptGenerationReadiness | None = None,
    automation_candidate: AutomationCandidate | None = None,
    project_type_hint: str | None = None,
    metadata: dict | None = None,
) -> WebPlaywrightReadiness:
    """Convenience wrapper for deterministic web Playwright readiness analysis."""

    return _DEFAULT_WEB_PLAYWRIGHT_READINESS_SERVICE.analyze_web_playwright_readiness(
        test_case,
        script_readiness=script_readiness,
        automation_candidate=automation_candidate,
        project_type_hint=project_type_hint,
        metadata=metadata,
    )


def analyze_web_playwright_readiness_batch(
    test_cases: Sequence[ManualTestCase],
    script_readiness_items: Sequence[ScriptGenerationReadiness] | None = None,
    automation_candidates: Sequence[AutomationCandidate] | None = None,
    project_type_hint: str | None = None,
    metadata: dict | None = None,
) -> list[WebPlaywrightReadiness]:
    """Convenience wrapper for batch web Playwright readiness analysis in input order."""

    return _DEFAULT_WEB_PLAYWRIGHT_READINESS_SERVICE.analyze_web_playwright_readiness_batch(
        test_cases,
        script_readiness_items=script_readiness_items,
        automation_candidates=automation_candidates,
        project_type_hint=project_type_hint,
        metadata=metadata,
    )
