from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from orchestrator.decision.domain.models import DecisionPolicyResult

from ..domain.models import (
    LarkNotificationEvent,
    LarkNotificationEventType,
    NormalizedLarkSourceContext,
)


@dataclass
class DecisionHookBuildResult:
    event: Optional[LarkNotificationEvent]
    reason: str
    source_id: str = ""
    context: Optional[NormalizedLarkSourceContext] = None


def notify_from_decision_result(
    *,
    decision_result: DecisionPolicyResult,
    source_context: Optional[NormalizedLarkSourceContext] = None,
) -> DecisionHookBuildResult:
    if decision_result.primary_decision.value != "BLOCK_RELEASE":
        return DecisionHookBuildResult(event=None, reason="decision_not_block_release")

    context = source_context or NormalizedLarkSourceContext()
    severity = str(decision_result.secondary_signals.get("severity", context.severity or "high"))
    title = str(context.metadata.get("title") or "Release blocked by policy")
    root_cause = context.root_cause or (decision_result.rationale[0] if decision_result.rationale else "")
    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.DECISION_RESULT,
        title=title,
        project=context.project_id or "unknown",
        adapter=context.adapter_id or "unknown",
        severity=severity,
        occurrence_count=max(1, int(context.occurrence_count)),
        confidence=decision_result.confidence,
        primary_decision=decision_result.primary_decision.value,
        root_cause=root_cause,
        action_required=context.action_required or "Immediate release manager review required",
        run_id=context.run_id or None,
        metadata={
            "decision_score": decision_result.decision_score,
            "recommended_owner": decision_result.recommended_owner or "",
        },
    )
    source_id = context.run_id or context.failure_id or "decision_result"
    return DecisionHookBuildResult(
        event=event,
        reason="block_release_decision",
        source_id=source_id,
        context=context,
    )

