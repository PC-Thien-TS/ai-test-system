from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from orchestrator.self_healing.domain.models import ActionExecutionBundle, ActionContext

from ..domain.models import (
    LarkNotificationEvent,
    LarkNotificationEventType,
    NormalizedLarkSourceContext,
)


@dataclass
class SelfHealingHookBuildResult:
    event: Optional[LarkNotificationEvent]
    reason: str
    source_id: str = ""
    context: Optional[NormalizedLarkSourceContext] = None


def notify_from_self_healing_result(
    *,
    action_bundle: ActionExecutionBundle,
    action_context: Optional[ActionContext] = None,
) -> SelfHealingHookBuildResult:
    if action_bundle.execution_result.success:
        return SelfHealingHookBuildResult(event=None, reason="self_healing_success")

    context = NormalizedLarkSourceContext()
    if action_context is not None:
        context = NormalizedLarkSourceContext(
            adapter_id=action_context.adapter_id,
            project_id=action_context.project_id,
            run_id=action_context.run_id,
            failure_id=action_context.failure_id,
            occurrence_count=int(action_context.memory_context.get("occurrence_count", 1)),
            metadata=dict(action_context.metadata),
        )

    decision = action_bundle.decision_result
    severity = str(decision.secondary_signals.get("severity", context.severity or "high"))
    root_cause = str(context.metadata.get("root_cause", "Self-healing action failed on current failure path"))

    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.SELF_HEALING_RESULT,
        title="Self-healing action failed repeatedly",
        project=context.project_id or "unknown",
        adapter=context.adapter_id or "unknown",
        severity=severity,
        occurrence_count=max(1, int(context.occurrence_count)),
        confidence=decision.confidence,
        primary_decision=decision.primary_decision.value,
        self_healing_status="FAILED",
        self_healing_success=False,
        attempts_used=action_bundle.execution_result.attempts_used,
        root_cause=root_cause,
        action_required="Manual investigation required after repeated self-healing failure",
        run_id=context.run_id or None,
        metadata={
            "action_id": action_bundle.execution_result.action_id,
            "failure_id": context.failure_id,
            "decision_score": decision.decision_score,
        },
    )
    source_id = action_bundle.execution_result.action_id or context.failure_id or "self_healing"
    return SelfHealingHookBuildResult(
        event=event,
        reason="self_healing_failed",
        source_id=source_id,
        context=context,
    )

