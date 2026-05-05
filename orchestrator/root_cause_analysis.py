from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


PRODUCT_BUG = "PRODUCT_BUG"
TEST_SCRIPT_ISSUE = "TEST_SCRIPT_ISSUE"
ENVIRONMENT_ISSUE = "ENVIRONMENT_ISSUE"
TEST_DATA_ISSUE = "TEST_DATA_ISSUE"
FLAKY_TEST = "FLAKY_TEST"
KNOWN_BACKEND_DEFECT = "KNOWN_BACKEND_DEFECT"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RootCauseAnalysisResult:
    root_cause_type: str
    confidence: float
    severity: str
    likely_owner: str
    reason: str
    suggested_action: str
    signals: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RootCauseAnalyzer:
    """Deterministically classify high-level root cause from aggregated failure signals."""

    def analyze(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload)

        locator_result = normalized["locator_healing_result"]
        if bool(locator_result.get("healing_applicable")):
            return self._result(
                root_cause_type=TEST_SCRIPT_ISSUE,
                confidence=max(0.82, self._as_float(locator_result.get("confidence"), 0.82)),
                severity="medium",
                likely_owner="qa_automation",
                reason="Locator self-healing found a safe replacement candidate, which points to a test-script locator issue.",
                suggested_action="Review the recommended replacement locator and update the affected UI test manually.",
                normalized=normalized,
            )

        flaky_score = normalized["flaky_score"]
        if flaky_score >= 0.75:
            return self._result(
                root_cause_type=FLAKY_TEST,
                confidence=min(0.97, max(0.8, flaky_score)),
                severity="medium",
                likely_owner="qa_automation",
                reason="The flaky score is high enough to classify this as a non-deterministic test failure.",
                suggested_action="Stabilize timing/state assumptions and review rerun history before escalating as a product defect.",
                normalized=normalized,
            )

        searchable = normalized["searchable_text"]
        api_status_code = normalized["api_status_code"]
        seen_count = normalized["seen_count"]
        mobile_failure_type = normalized["mobile_failure_type"]

        if self._contains_any(
            searchable,
            [
                "connection refused",
                "read timed out",
                "connect timeout",
                "network is unreachable",
                "name or service not known",
                "temporary failure in name resolution",
                "dns",
                "host unreachable",
                "appium server",
            ],
        ) or mobile_failure_type in {"MOBILE_DRIVER_ERROR", "MOBILE_ENVIRONMENT_ERROR"}:
            return self._result(
                root_cause_type=ENVIRONMENT_ISSUE,
                confidence=0.91,
                severity="high",
                likely_owner="qa_infra",
                reason="The failure signals indicate an environment, network, or execution dependency problem.",
                suggested_action="Check infrastructure availability, network connectivity, and external runtime dependencies.",
                normalized=normalized,
            )

        if (
            api_status_code in {401, 403}
            and self._contains_any(
                searchable,
                [
                    "auth",
                    "token",
                    "credential",
                    "forbidden",
                    "unauthorized",
                    "permission",
                    "seed",
                    "fixture",
                    "missing user",
                    "missing account",
                ],
            )
        ):
            return self._result(
                root_cause_type=TEST_DATA_ISSUE,
                confidence=0.9,
                severity="medium",
                likely_owner="qa_automation",
                reason="Authorization failure signals are consistent with missing or invalid test data/setup rather than an application defect.",
                suggested_action="Verify credentials, seeded data, account permissions, and fixture setup for the failing test.",
                normalized=normalized,
            )

        if api_status_code >= 500:
            if seen_count >= 3:
                return self._result(
                    root_cause_type=KNOWN_BACKEND_DEFECT,
                    confidence=0.9,
                    severity="high",
                    likely_owner="backend_team",
                    reason="A repeated 5xx failure pattern suggests a known or recurring backend defect.",
                    suggested_action="Compare against recent recurring backend failures and route to the owning backend service team.",
                    normalized=normalized,
                )
            return self._result(
                root_cause_type=PRODUCT_BUG,
                confidence=0.88,
                severity="high",
                likely_owner="backend_team",
                reason="The API returned a 5xx response, which points to an application-side defect.",
                suggested_action="Inspect backend logs and the failing endpoint path to isolate the server-side regression.",
                normalized=normalized,
            )

        if mobile_failure_type == "MOBILE_POLICY_UNSUPPORTED_ACTION":
            return self._result(
                root_cause_type=TEST_SCRIPT_ISSUE,
                confidence=0.89,
                severity="medium",
                likely_owner="qa_policy",
                reason="The mobile failure intelligence indicates an unsupported policy action rather than product behavior.",
                suggested_action="Review mobile exploration policy mappings and unsupported action fallback behavior.",
                normalized=normalized,
            )

        if mobile_failure_type == "MOBILE_ELEMENT_NOT_FOUND":
            return self._result(
                root_cause_type=TEST_SCRIPT_ISSUE,
                confidence=0.86,
                severity="medium",
                likely_owner="mobile_automation",
                reason="The mobile failure intelligence points to missing UI element bindings or brittle locator assumptions.",
                suggested_action="Review mobile element locators and state assumptions for the affected flow.",
                normalized=normalized,
            )

        if mobile_failure_type == "MOBILE_NAVIGATION_FAILURE":
            if self._contains_any(searchable, ["unsupported", "policy", "locator", "test step"]):
                return self._result(
                    root_cause_type=TEST_SCRIPT_ISSUE,
                    confidence=0.76,
                    severity="medium",
                    likely_owner="mobile_automation",
                    reason="Navigation failed and the surrounding signals suggest the automation path or policy is incorrect.",
                    suggested_action="Review the navigation script/policy sequence and recovery behavior for the failing mobile flow.",
                    normalized=normalized,
                )
            return self._result(
                root_cause_type=PRODUCT_BUG,
                confidence=0.8,
                severity="high",
                likely_owner="mobile_app",
                reason="Navigation failed without strong automation-only signals, which suggests an app behavior or screen-transition defect.",
                suggested_action="Inspect app navigation state transitions and view-loading behavior around the failing flow.",
                normalized=normalized,
            )

        if mobile_failure_type == "MOBILE_COVERAGE_NOT_REACHED":
            if self._contains_any(searchable, ["policy", "max_steps", "coverage target", "no_valid_action"]):
                return self._result(
                    root_cause_type=TEST_SCRIPT_ISSUE,
                    confidence=0.74,
                    severity="medium",
                    likely_owner="qa_automation",
                    reason="Coverage did not complete and the stop signals suggest exploration configuration limits or policy issues.",
                    suggested_action="Tune exploration depth, policy coverage targets, or action availability for the mobile run.",
                    normalized=normalized,
                )
            return self._result(
                root_cause_type=PRODUCT_BUG,
                confidence=0.68,
                severity="medium",
                likely_owner="mobile_app",
                reason="Coverage stopped short without a stronger automation-only signal, so product behavior remains the more likely cause.",
                suggested_action="Review the app behavior around incomplete mobile flows and confirm whether execution stalled in-product.",
                normalized=normalized,
            )

        if self._contains_any(
            searchable,
            [
                "assertionerror",
                "expected",
                "mismatch",
                "schema validation failed",
                "response body mismatch",
            ],
        ):
            return self._result(
                root_cause_type=PRODUCT_BUG,
                confidence=0.66,
                severity="medium",
                likely_owner="product_team",
                reason="Assertion-style failure signals indicate the product output did not match the expected behavior.",
                suggested_action="Review the failing expectation against current product behavior and confirm whether a regression was introduced.",
                normalized=normalized,
            )

        return self._result(
            root_cause_type=UNKNOWN,
            confidence=0.25,
            severity="medium",
            likely_owner="qa_platform",
            reason="The available signals are insufficient for a higher-confidence deterministic root cause classification.",
            suggested_action="Capture more evidence such as locator output, API response details, rerun history, or environment logs.",
            normalized=normalized,
        )

    def _normalize_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")

        locator_healing_result = payload.get("locator_healing_result")
        if not isinstance(locator_healing_result, Mapping):
            locator_healing_result = {}

        evidence_summary = payload.get("evidence_summary")
        if not isinstance(evidence_summary, Mapping):
            evidence_summary = {}

        normalized = {
            "failure_type": self._as_str(payload.get("failure_type")),
            "error_message": self._as_str(payload.get("error_message")),
            "pytest_log": self._as_str(payload.get("pytest_log")),
            "api_status_code": self._as_int(payload.get("api_status_code"), 0),
            "api_response_text": self._as_str(payload.get("api_response_text")),
            "mobile_failure_type": self._as_str(payload.get("mobile_failure_type")),
            "locator_healing_result": dict(locator_healing_result),
            "evidence_summary": dict(evidence_summary),
            "flaky_score": self._as_float(payload.get("flaky_score"), 0.0),
            "seen_count": self._as_int(payload.get("seen_count"), 0),
        }
        normalized["searchable_text"] = " ".join(
            part.lower()
            for part in [
                normalized["failure_type"],
                normalized["error_message"],
                normalized["pytest_log"],
                normalized["api_response_text"],
                normalized["mobile_failure_type"],
                self._as_str(locator_healing_result.get("failure_type")),
                self._as_str(locator_healing_result.get("reason")),
                self._as_str(evidence_summary.get("summary")),
                self._as_str(evidence_summary.get("error")),
                self._as_str(evidence_summary.get("stop_reason")),
            ]
            if part
        )
        return normalized

    def _result(
        self,
        *,
        root_cause_type: str,
        confidence: float,
        severity: str,
        likely_owner: str,
        reason: str,
        suggested_action: str,
        normalized: dict[str, Any],
    ) -> dict[str, Any]:
        return RootCauseAnalysisResult(
            root_cause_type=root_cause_type,
            confidence=round(confidence, 3),
            severity=severity,
            likely_owner=likely_owner,
            reason=reason,
            suggested_action=suggested_action,
            signals={
                "failure_type": normalized["failure_type"],
                "api_status_code": normalized["api_status_code"],
                "mobile_failure_type": normalized["mobile_failure_type"],
                "locator_healing_applicable": bool(normalized["locator_healing_result"].get("healing_applicable")),
                "flaky_score": normalized["flaky_score"],
                "seen_count": normalized["seen_count"],
                "has_pytest_log": bool(normalized["pytest_log"]),
                "has_api_response_text": bool(normalized["api_response_text"]),
                "evidence_keys": sorted(normalized["evidence_summary"].keys()),
            },
        ).to_dict()

    def _contains_any(self, haystack: str, needles: list[str]) -> bool:
        return any(needle in haystack for needle in needles)

    def _as_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _as_float(self, value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _as_int(self, value: Any, default: int) -> int:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default


def analyze_root_cause(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministically classify high-level root cause from aggregated failure signals."""
    return RootCauseAnalyzer().analyze(payload)
