from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


LOCATOR_NOT_FOUND = "LOCATOR_NOT_FOUND"
LOCATOR_NOT_VISIBLE = "LOCATOR_NOT_VISIBLE"
LOCATOR_AMBIGUOUS = "LOCATOR_AMBIGUOUS"
NON_LOCATOR_FAILURE = "NON_LOCATOR_FAILURE"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LocatorCandidate:
    locator: str
    strategy: str
    confidence: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocatorHealingRecommendation:
    healing_applicable: bool
    failure_type: str
    confidence: float
    original_locator: str
    candidate_locators: list[dict[str, Any]]
    recommended_locator: str
    recommendation: str
    reason: str
    signals: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LocatorSelfHealingEngine:
    """Deterministic locator self-healing recommender for UI automation failures."""

    def analyze(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload)
        failure_type = self._classify_failure(normalized)
        candidates = self._build_candidates(normalized, failure_type)
        healing_applicable = failure_type in {
            LOCATOR_NOT_FOUND,
            LOCATOR_NOT_VISIBLE,
            LOCATOR_AMBIGUOUS,
        } and bool(candidates)
        recommended_locator = candidates[0].locator if candidates else ""
        confidence = candidates[0].confidence if candidates else self._fallback_confidence(failure_type)
        reason = self._build_reason(normalized, failure_type, candidates)
        recommendation = self._build_recommendation(failure_type, candidates)

        return LocatorHealingRecommendation(
            healing_applicable=healing_applicable,
            failure_type=failure_type,
            confidence=confidence,
            original_locator=normalized["failed_locator"],
            candidate_locators=[candidate.to_dict() for candidate in candidates],
            recommended_locator=recommended_locator,
            recommendation=recommendation,
            reason=reason,
            signals=self._build_signals(normalized, failure_type, candidates),
        ).to_dict()

    def _normalize_payload(self, payload: Mapping[str, Any]) -> dict[str, str]:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return {
            "failed_locator": self._as_str(payload.get("failed_locator")),
            "error_message": self._as_str(payload.get("error_message")),
            "dom_snapshot": self._as_str(payload.get("dom_snapshot")),
            "accessible_role": self._as_str(payload.get("accessible_role")).lower(),
            "visible_text": self._as_str(payload.get("visible_text")),
            "nearby_text": self._as_str(payload.get("nearby_text")),
            "test_name": self._as_str(payload.get("test_name")),
            "source_file": self._as_str(payload.get("source_file")),
        }

    def _classify_failure(self, payload: dict[str, str]) -> str:
        error = payload["error_message"].lower()
        locator = payload["failed_locator"].lower()
        searchable = " ".join(part for part in [error, locator] if part)

        if not searchable:
            return UNKNOWN

        if self._contains_any(
            error,
            [
                "assertionerror: expected status code",
                "networkerror",
                "500 internal server error",
                "timeout waiting for response",
                "api failure",
                "authentication failed",
            ],
        ):
            return NON_LOCATOR_FAILURE

        if self._contains_any(
            searchable,
            [
                "strict mode violation",
                "resolved to",
                "multiple elements",
                "ambiguous",
                "more than one element",
            ],
        ):
            return LOCATOR_AMBIGUOUS

        if self._contains_any(
            searchable,
            [
                "not visible",
                "is hidden",
                "element is not visible",
                "not attached",
                "obscured",
                "not enabled",
            ],
        ):
            return LOCATOR_NOT_VISIBLE

        if self._contains_any(
            searchable,
            [
                "no such element",
                "element not found",
                "unable to locate",
                "waiting for locator",
                "failed to find element",
                "selector resolved to 0 elements",
                "timeout exceeded while waiting for",
                "locator(",
                "get_by_role(",
                "get_by_text(",
                "get_by_label(",
            ],
        ):
            return LOCATOR_NOT_FOUND

        return UNKNOWN

    def _build_candidates(self, payload: dict[str, str], failure_type: str) -> list[LocatorCandidate]:
        if failure_type not in {LOCATOR_NOT_FOUND, LOCATOR_NOT_VISIBLE, LOCATOR_AMBIGUOUS}:
            return []

        candidates: list[LocatorCandidate] = []
        role = payload["accessible_role"]
        visible_text = payload["visible_text"]
        nearby_text = payload["nearby_text"]
        dom_snapshot = payload["dom_snapshot"]

        if role and visible_text:
            candidates.append(
                LocatorCandidate(
                    locator=f'page.get_by_role("{role}", name="{self._escape(visible_text)}")',
                    strategy="get_by_role",
                    confidence=0.93,
                    evidence="accessible_role + visible_text",
                )
            )

        label_text = nearby_text or visible_text
        if label_text and self._looks_like_label_candidate(payload):
            candidates.append(
                LocatorCandidate(
                    locator=f'page.get_by_label("{self._escape(label_text)}")',
                    strategy="get_by_label",
                    confidence=0.88,
                    evidence="input-like locator + label/nearby text",
                )
            )

        if visible_text:
            candidates.append(
                LocatorCandidate(
                    locator=f'page.get_by_text("{self._escape(visible_text)}")',
                    strategy="get_by_text",
                    confidence=0.8,
                    evidence="visible_text",
                )
            )

        test_ids = self._extract_test_ids(dom_snapshot)
        matched_test_ids = self._rank_test_ids(test_ids, payload)
        for idx, test_id in enumerate(matched_test_ids[:2]):
            confidence = 0.91 if idx == 0 else 0.83
            candidates.append(
                LocatorCandidate(
                    locator=f'page.get_by_test_id("{self._escape(test_id)}")',
                    strategy="get_by_test_id",
                    confidence=confidence,
                    evidence="data-testid/test-id found in dom_snapshot",
                )
            )

        return self._dedupe_candidates(candidates)

    def _rank_test_ids(self, test_ids: list[str], payload: dict[str, str]) -> list[str]:
        if not test_ids:
            return []

        hints = " ".join(
            part.lower()
            for part in [
                payload["failed_locator"],
                payload["visible_text"],
                payload["nearby_text"],
                payload["test_name"],
                payload["source_file"],
            ]
            if part
        )

        def sort_key(test_id: str) -> tuple[int, str]:
            normalized = test_id.lower()
            score = 0
            for token in re.findall(r"[a-z0-9]+", hints):
                if token and token in normalized:
                    score += 1
            return (-score, normalized)

        unique_ids = list(dict.fromkeys(test_ids))
        return sorted(unique_ids, key=sort_key)

    def _extract_test_ids(self, dom_snapshot: str) -> list[str]:
        if not dom_snapshot:
            return []
        matches = re.findall(
            r'(?:data-testid|data-testid|test-id)\s*=\s*["\']([^"\']+)["\']',
            dom_snapshot,
            flags=re.IGNORECASE,
        )
        return [match.strip() for match in matches if match.strip()]

    def _looks_like_label_candidate(self, payload: dict[str, str]) -> bool:
        locator = payload["failed_locator"].lower()
        error = payload["error_message"].lower()
        text = " ".join([locator, error])
        return any(token in text for token in ["input", "textbox", "field", "placeholder", "fill", "type"])

    def _dedupe_candidates(self, candidates: list[LocatorCandidate]) -> list[LocatorCandidate]:
        deduped: dict[str, LocatorCandidate] = {}
        for candidate in sorted(candidates, key=lambda item: (-item.confidence, item.locator)):
            deduped.setdefault(candidate.locator, candidate)
        return list(deduped.values())

    def _build_reason(
        self,
        payload: dict[str, str],
        failure_type: str,
        candidates: list[LocatorCandidate],
    ) -> str:
        if failure_type == NON_LOCATOR_FAILURE:
            return "The failure signal does not look locator-related, so locator healing is not applicable."
        if failure_type == UNKNOWN:
            return "The failure signal is too sparse to classify confidently as a locator issue."
        if not candidates:
            return "The failure looks locator-related, but there is not enough evidence to suggest a safe replacement locator."
        top = candidates[0]
        return f"Detected {failure_type.lower()} and found evidence for {top.strategy} as the safest replacement strategy."

    def _build_recommendation(self, failure_type: str, candidates: list[LocatorCandidate]) -> str:
        if failure_type == NON_LOCATOR_FAILURE:
            return "Investigate the underlying test/application failure before attempting locator healing."
        if failure_type == UNKNOWN:
            return "Capture more locator context such as visible text, role, or DOM snapshot before healing."
        if not candidates:
            return "Collect role/text/test-id evidence before replacing the failing locator."
        return f"Try {candidates[0].locator} first and review the remaining candidates manually before editing test scripts."

    def _build_signals(
        self,
        payload: dict[str, str],
        failure_type: str,
        candidates: list[LocatorCandidate],
    ) -> dict[str, Any]:
        return {
            "failed_locator": payload["failed_locator"],
            "error_message": payload["error_message"],
            "accessible_role": payload["accessible_role"],
            "visible_text": payload["visible_text"],
            "nearby_text": payload["nearby_text"],
            "test_name": payload["test_name"],
            "source_file": payload["source_file"],
            "dom_has_test_id": bool(self._extract_test_ids(payload["dom_snapshot"])),
            "candidate_count": len(candidates),
            "failure_type": failure_type,
        }

    def _fallback_confidence(self, failure_type: str) -> float:
        if failure_type == NON_LOCATOR_FAILURE:
            return 0.95
        if failure_type == UNKNOWN:
            return 0.2
        return 0.45

    def _contains_any(self, haystack: str, needles: list[str]) -> bool:
        return any(needle in haystack for needle in needles)

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _as_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


def suggest_locator_healing(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Generate safe locator self-healing recommendations without modifying scripts."""
    return LocatorSelfHealingEngine().analyze(payload)
