from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from orchestrator.candidates.domain.models import CandidateGenerationResult, CandidateInputBase

from ..domain.models import (
    LarkNotificationEvent,
    LarkNotificationEventType,
    NormalizedLarkSourceContext,
)


@dataclass
class CandidateHookBuildResult:
    event: Optional[LarkNotificationEvent]
    reason: str
    source_id: str = ""
    context: Optional[NormalizedLarkSourceContext] = None


def _healing_status_from_metadata(artifact: dict) -> Optional[str]:
    metadata = artifact.get("metadata", {})
    value = metadata.get("self_healing_success")
    if value is None:
        return None
    return "SUCCESS" if bool(value) else "FAILED"


def notify_from_candidate_result(
    *,
    candidate_result: CandidateGenerationResult,
    candidate_input: Optional[CandidateInputBase] = None,
) -> CandidateHookBuildResult:
    if not candidate_result.generated:
        return CandidateHookBuildResult(event=None, reason="candidate_not_generated")
    if not candidate_result.artifact:
        return CandidateHookBuildResult(event=None, reason="candidate_artifact_missing")

    artifact = candidate_result.artifact
    artifact_type = str(artifact.get("artifact_type", "")).strip().lower()
    metadata = artifact.get("metadata", {})
    adapter_id = str(metadata.get("adapter_id") or (candidate_input.adapter_id if candidate_input else ""))
    project_id = str(metadata.get("project_id") or (candidate_input.project_id if candidate_input else ""))
    run_id = str(metadata.get("run_id") or (candidate_input.run_id if candidate_input else ""))
    memory_id = str(metadata.get("memory_id") or (candidate_input.memory_id if candidate_input else ""))
    failure_id = str(metadata.get("failure_id") or (candidate_input.failure_id if candidate_input else ""))
    decision_primary = str(metadata.get("decision_primary") or "")

    if artifact_type == "incident_candidate":
        event_type = LarkNotificationEventType.INCIDENT_CANDIDATE
        action_required = "Immediate investigation required"
        root_cause = str(artifact.get("escalation_reason") or artifact.get("summary") or "")
    elif artifact_type == "bug_candidate":
        event_type = LarkNotificationEventType.BUG_CANDIDATE
        action_required = "Investigate owner path and prepare fix"
        root_cause = str(artifact.get("root_cause") or artifact.get("summary") or "")
    else:
        return CandidateHookBuildResult(event=None, reason="unsupported_candidate_type")

    occurrence_count = int(artifact.get("recurrence") or (candidate_input.occurrence_count if candidate_input else 1))
    confidence = artifact.get("confidence")
    if confidence is None and candidate_input is not None:
        confidence = candidate_input.confidence

    event = LarkNotificationEvent(
        event_type=event_type,
        title=str(artifact.get("title") or "Candidate generated"),
        project=project_id or "unknown",
        adapter=adapter_id or "unknown",
        severity=str(artifact.get("severity") or (candidate_input.severity if candidate_input else "medium")),
        occurrence_count=occurrence_count,
        confidence=float(confidence) if confidence is not None else None,
        primary_decision=decision_primary or None,
        self_healing_status=_healing_status_from_metadata(artifact),
        root_cause=root_cause,
        action_required=action_required,
        run_id=run_id or None,
        memory_id=memory_id or None,
        metadata={
            "candidate_id": str(artifact.get("candidate_id") or candidate_result.candidate_id),
            "failure_id": failure_id,
            "artifact_type": artifact_type,
        },
    )
    context = NormalizedLarkSourceContext(
        adapter_id=adapter_id,
        project_id=project_id,
        run_id=run_id,
        failure_id=failure_id,
        severity=event.severity,
        confidence=event.confidence,
        occurrence_count=event.occurrence_count,
        root_cause=event.root_cause,
        action_required=event.action_required,
        metadata={"candidate_type": artifact_type},
    )
    return CandidateHookBuildResult(
        event=event,
        reason="candidate_notification_ready",
        source_id=str(artifact.get("candidate_id") or candidate_result.candidate_id),
        context=context,
    )

