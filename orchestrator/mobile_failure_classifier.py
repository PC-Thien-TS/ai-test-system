from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from mobile_appium import MobileRunArtifact
from orchestrator.mobile_evidence_adapter import (
    MOBILE_EXPLORATION_EVIDENCE_TYPE,
    MobileEvidenceAdapter,
    MobileExplorationEvidence,
)


SUCCESS = "SUCCESS"
MOBILE_NAVIGATION_FAILURE = "MOBILE_NAVIGATION_FAILURE"
MOBILE_ELEMENT_NOT_FOUND = "MOBILE_ELEMENT_NOT_FOUND"
MOBILE_POLICY_UNSUPPORTED_ACTION = "MOBILE_POLICY_UNSUPPORTED_ACTION"
MOBILE_COVERAGE_NOT_REACHED = "MOBILE_COVERAGE_NOT_REACHED"
MOBILE_DRIVER_ERROR = "MOBILE_DRIVER_ERROR"
MOBILE_ENVIRONMENT_ERROR = "MOBILE_ENVIRONMENT_ERROR"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MobileFailureIntelligence:
    failure_type: str
    severity: str
    confidence: float
    likely_owner: str
    recommendation: str
    reason: str
    signals: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _normalize_payload(
    payload: MobileExplorationEvidence | MobileRunArtifact | Mapping[str, Any],
) -> MobileExplorationEvidence:
    if isinstance(payload, MobileExplorationEvidence):
        return payload
    if isinstance(payload, MobileRunArtifact):
        return MobileEvidenceAdapter().collect(payload)
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be MobileExplorationEvidence, MobileRunArtifact, or mapping")

    if _as_str(payload.get("evidence_type")) == MOBILE_EXPLORATION_EVIDENCE_TYPE:
        return MobileExplorationEvidence(
            evidence_type=MOBILE_EXPLORATION_EVIDENCE_TYPE,
            richness_score=_as_float(payload.get("richness_score")),
            run_id=_as_str(payload.get("run_id")),
            status=_as_str(payload.get("status")).lower() or "unknown",
            stop_reason=_as_str(payload.get("stop_reason")),
            visited_screen_count=_as_int(payload.get("visited_screen_count")),
            executed_action_count=_as_int(payload.get("executed_action_count")),
            coverage_score=_as_float(payload.get("coverage_score")),
            policy_shape=_as_str(payload.get("policy_shape")),
            artifact_path=_as_str(payload.get("artifact_path")),
            error=_as_str(payload.get("error")),
            failure_signal=_as_str(payload.get("failure_signal")),
        )

    return MobileEvidenceAdapter().collect(payload)


class MobileFailureClassifier:
    """Deterministically classify mobile exploration failures from normalized evidence."""

    def classify(
        self,
        payload: MobileExplorationEvidence | MobileRunArtifact | Mapping[str, Any],
    ) -> MobileFailureIntelligence:
        evidence = _normalize_payload(payload)
        signals = self._signals(evidence)

        if evidence.status == "passed":
            return MobileFailureIntelligence(
                failure_type=SUCCESS,
                severity="low",
                confidence=0.99,
                likely_owner="qa_platform",
                recommendation="No action required. Mobile exploration reached a passing outcome.",
                reason="Mobile exploration evidence indicates a passed run.",
                signals=signals,
            )

        lower_error = evidence.error.lower()
        lower_stop_reason = evidence.stop_reason.lower()
        lower_failure_signal = evidence.failure_signal.lower()
        searchable = " ".join(part for part in [lower_error, lower_stop_reason, lower_failure_signal] if part)

        if self._contains_any(
            searchable,
            [
                "connection refused",
                "failed to establish a new connection",
                "appium server",
                "real appium mode requires",
                "timed out",
                "timeout waiting",
                "dns",
                "host unreachable",
            ],
        ):
            return MobileFailureIntelligence(
                failure_type=MOBILE_ENVIRONMENT_ERROR,
                severity="critical",
                confidence=0.93,
                likely_owner="qa_infra",
                recommendation="Verify Appium availability, device/emulator readiness, and required runtime configuration.",
                reason="Failure signals point to an environment or infrastructure dependency problem.",
                signals=signals,
            )

        if self._contains_any(
            searchable,
            [
                "nosuchelementexception",
                "element not found",
                "unsupported locator strategy",
            ],
        ):
            return MobileFailureIntelligence(
                failure_type=MOBILE_ELEMENT_NOT_FOUND,
                severity="high",
                confidence=0.95,
                likely_owner="mobile_automation",
                recommendation="Check screen locators and app state assumptions for the targeted mobile flow.",
                reason="Failure signals indicate an expected mobile element could not be located.",
                signals=signals,
            )

        if self._contains_any(
            searchable,
            [
                "unsupported navigation action",
                "unsupported journey step action",
                "no_valid_action",
                "no_action_available",
                "unsupported_recovery",
            ],
        ):
            return MobileFailureIntelligence(
                failure_type=MOBILE_POLICY_UNSUPPORTED_ACTION,
                severity="medium",
                confidence=0.9,
                likely_owner="qa_policy",
                recommendation="Review exploration policy action mapping and fallback behavior for unsupported mobile actions.",
                reason="Policy-selected or fallback-selected actions are not executable by the current mobile runner.",
                signals=signals,
            )

        if self._contains_any(
            searchable,
            [
                "driver does not support",
                "webdriverexception",
                "sessionnotcreatedexception",
                "invalidsessionidexception",
                "uiautomator2",
                "webdriver",
            ],
        ):
            return MobileFailureIntelligence(
                failure_type=MOBILE_DRIVER_ERROR,
                severity="high",
                confidence=0.9,
                likely_owner="qa_infra",
                recommendation="Inspect driver capabilities, session lifecycle, and supported driver features for the run mode.",
                reason="Failure signals indicate a mobile driver/session problem rather than app behavior alone.",
                signals=signals,
            )

        if self._contains_any(
            searchable,
            [
                "cycle_detected",
                "repeated_failure_threshold_reached",
                "max_steps_per_screen_reached",
                "screen is not loaded",
                "list items are not visible",
                "detail content is not visible",
                "cannot open detail",
                "cannot navigate back to list",
            ],
        ):
            return MobileFailureIntelligence(
                failure_type=MOBILE_NAVIGATION_FAILURE,
                severity="high",
                confidence=0.88,
                likely_owner="mobile_app",
                recommendation="Investigate screen transitions, navigation assumptions, and state recovery in the affected mobile flow.",
                reason="Failure signals indicate the exploration flow could not progress through expected screens reliably.",
                signals=signals,
            )

        if evidence.status == "failed" and (
            lower_stop_reason == "max_steps_reached"
            or (
                evidence.coverage_score < 1.0
                and lower_stop_reason in {
                    "max_steps_reached",
                    "max_steps_per_screen_reached",
                    "cycle_detected",
                    "repeated_failure_threshold_reached",
                }
            )
        ):
            return MobileFailureIntelligence(
                failure_type=MOBILE_COVERAGE_NOT_REACHED,
                severity="medium",
                confidence=0.82,
                likely_owner="qa_automation",
                recommendation="Increase exploration depth or tune policy coverage targets for the mobile journey under test.",
                reason="The run ended before reaching the intended mobile exploration coverage target.",
                signals=signals,
            )

        return MobileFailureIntelligence(
            failure_type=UNKNOWN,
            severity="medium",
            confidence=0.35,
            likely_owner="qa_platform",
            recommendation="Inspect the raw mobile artifact/evidence payload and add a more specific classifier rule if this pattern repeats.",
            reason="Current mobile failure signals are insufficient for a more specific deterministic classification.",
            signals=signals,
        )

    def _signals(self, evidence: MobileExplorationEvidence) -> dict[str, Any]:
        searchable_terms = [
            term
            for term in {
                evidence.status,
                evidence.stop_reason,
                evidence.policy_shape,
                evidence.failure_signal,
                evidence.error,
            }
            if _as_str(term)
        ]
        return {
            "run_id": evidence.run_id,
            "status": evidence.status,
            "stop_reason": evidence.stop_reason,
            "coverage_score": evidence.coverage_score,
            "visited_screen_count": evidence.visited_screen_count,
            "executed_action_count": evidence.executed_action_count,
            "policy_shape": evidence.policy_shape,
            "artifact_path": evidence.artifact_path,
            "error": evidence.error,
            "failure_signal": evidence.failure_signal,
            "richness_score": evidence.richness_score,
            "matched_terms": searchable_terms,
        }

    def _contains_any(self, haystack: str, needles: list[str]) -> bool:
        return any(needle in haystack for needle in needles)


def classify_mobile_failure(
    payload: MobileExplorationEvidence | MobileRunArtifact | Mapping[str, Any],
) -> dict[str, Any]:
    """Convenience entry point for serializable mobile failure intelligence."""
    return MobileFailureClassifier().classify(payload).to_dict()
