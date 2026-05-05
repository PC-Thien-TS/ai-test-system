from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from mobile_appium import MobileRunArtifact
from orchestrator.mobile_adapter import MOBILE_EXPLORATION_PLUGIN

MOBILE_EXPLORATION_EVIDENCE_TYPE = "mobile_exploration"


def _as_dict(payload: MobileRunArtifact | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload, MobileRunArtifact):
        return payload.to_dict()
    if isinstance(payload, Mapping):
        return dict(payload)
    raise TypeError("payload must be a MobileRunArtifact or mapping")


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


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return []


def _normalize_status(status: Any, passed: Any | None = None) -> str:
    normalized = _as_str(status).lower()
    if normalized in {"passed", "failed"}:
        return normalized
    if passed is True:
        return "passed"
    if passed is False:
        return "failed"
    return "unknown"


def _normalize_artifact_path(
    explicit_artifact_path: str | Path | None,
    *candidates: Any,
) -> str:
    if explicit_artifact_path is not None and _as_str(explicit_artifact_path):
        return str(explicit_artifact_path)
    for candidate in candidates:
        normalized = _as_str(candidate)
        if normalized:
            return normalized
    return ""


@dataclass(frozen=True)
class MobileExplorationEvidence:
    evidence_type: str
    richness_score: float
    run_id: str
    status: str
    stop_reason: str
    visited_screen_count: int
    executed_action_count: int
    coverage_score: float
    policy_shape: str
    artifact_path: str
    error: str
    failure_signal: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MobileEvidenceAdapter:
    """Normalize mobile exploration outputs into platform-analyzable evidence."""

    def collect(
        self,
        payload: MobileRunArtifact | Mapping[str, Any],
        *,
        artifact_path: str | Path | None = None,
    ) -> MobileExplorationEvidence:
        normalized = _as_dict(payload)
        if "artifact" in normalized:
            return self._from_orchestrator_result(normalized, artifact_path=artifact_path)
        return self._from_artifact_payload(normalized, artifact_path=artifact_path)

    def _from_orchestrator_result(
        self,
        result: Mapping[str, Any],
        *,
        artifact_path: str | Path | None = None,
    ) -> MobileExplorationEvidence:
        summary = dict(result.get("summary") or {})
        artifact = dict(result.get("artifact") or {})

        status = _normalize_status(result.get("status"), artifact.get("passed"))
        stop_reason = _as_str(summary.get("stop_reason") or artifact.get("stop_reason"))
        visited_screen_count = _as_int(
            summary.get("visited_screen_count"),
            default=len(_as_list(artifact.get("visited_screens"))),
        )
        executed_action_count = _as_int(
            summary.get("executed_action_count"),
            default=len(_as_list(artifact.get("executed_actions"))),
        )
        coverage_score = _as_float(
            summary.get("coverage_score"),
            default=_as_float(artifact.get("coverage_score")),
        )
        policy_shape = _as_str(summary.get("policy_shape") or artifact.get("policy_shape"))
        error = _as_str(artifact.get("error") or result.get("error"))
        resolved_artifact_path = _normalize_artifact_path(
            artifact_path,
            result.get("artifact_path"),
            artifact.get("artifact_path"),
        )

        return self._build_evidence(
            run_id=_as_str(result.get("run_id") or artifact.get("run_id")),
            status=status,
            stop_reason=stop_reason,
            visited_screen_count=visited_screen_count,
            executed_action_count=executed_action_count,
            coverage_score=coverage_score,
            policy_shape=policy_shape,
            artifact_path=resolved_artifact_path,
            error=error,
        )

    def _from_artifact_payload(
        self,
        artifact: Mapping[str, Any],
        *,
        artifact_path: str | Path | None = None,
    ) -> MobileExplorationEvidence:
        status = _normalize_status(None, artifact.get("passed"))
        stop_reason = _as_str(artifact.get("stop_reason"))
        visited_screen_count = len(_as_list(artifact.get("visited_screens")))
        executed_action_count = len(_as_list(artifact.get("executed_actions")))
        coverage_score = _as_float(artifact.get("coverage_score"))
        policy_shape = _as_str(artifact.get("policy_shape"))
        error = _as_str(artifact.get("error"))
        resolved_artifact_path = _normalize_artifact_path(
            artifact_path,
            artifact.get("artifact_path"),
            artifact.get("output_path"),
        )

        return self._build_evidence(
            run_id=_as_str(artifact.get("run_id")),
            status=status,
            stop_reason=stop_reason,
            visited_screen_count=visited_screen_count,
            executed_action_count=executed_action_count,
            coverage_score=coverage_score,
            policy_shape=policy_shape,
            artifact_path=resolved_artifact_path,
            error=error,
        )

    def calculate_richness(
        self,
        *,
        run_id: str,
        status: str,
        stop_reason: str,
        visited_screen_count: int,
        executed_action_count: int,
        coverage_score: float,
        policy_shape: str,
        artifact_path: str,
        error: str,
    ) -> float:
        richness = 0.0
        if run_id:
            richness += 0.10
        if status in {"passed", "failed"}:
            richness += 0.10
        if stop_reason:
            richness += 0.10
        richness += min(0.20, max(0.0, visited_screen_count) * (0.20 / 3.0))
        richness += min(0.20, max(0.0, executed_action_count) * (0.20 / 3.0))
        richness += min(0.25, max(0.0, min(coverage_score, 1.0)) * 0.25)
        if policy_shape:
            richness += 0.10
        if artifact_path:
            richness += 0.05
        if error:
            richness += 0.10
        return min(1.0, round(richness, 4))

    def _build_evidence(
        self,
        *,
        run_id: str,
        status: str,
        stop_reason: str,
        visited_screen_count: int,
        executed_action_count: int,
        coverage_score: float,
        policy_shape: str,
        artifact_path: str,
        error: str,
    ) -> MobileExplorationEvidence:
        failure_signal = ""
        if status == "failed":
            failure_signal = error or stop_reason or "failed"

        richness_score = self.calculate_richness(
            run_id=run_id,
            status=status,
            stop_reason=stop_reason,
            visited_screen_count=visited_screen_count,
            executed_action_count=executed_action_count,
            coverage_score=coverage_score,
            policy_shape=policy_shape,
            artifact_path=artifact_path,
            error=error,
        )

        return MobileExplorationEvidence(
            evidence_type=MOBILE_EXPLORATION_EVIDENCE_TYPE,
            richness_score=richness_score,
            run_id=run_id,
            status=status,
            stop_reason=stop_reason,
            visited_screen_count=visited_screen_count,
            executed_action_count=executed_action_count,
            coverage_score=coverage_score,
            policy_shape=policy_shape,
            artifact_path=artifact_path,
            error=error,
            failure_signal=failure_signal,
        )


def collect_mobile_exploration_evidence(
    payload: MobileRunArtifact | Mapping[str, Any],
    *,
    artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convenience entry point for callers that need a serializable evidence object."""
    return MobileEvidenceAdapter().collect(payload, artifact_path=artifact_path).to_dict()
