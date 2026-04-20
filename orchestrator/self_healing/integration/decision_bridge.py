from __future__ import annotations

from typing import Any, Optional

from orchestrator.decision.domain.models import DecisionPolicyResult

from ..application.engine import SelfHealingEngine
from ..domain.models import ActionContext, ActionExecutionBundle


def execute_from_decision(
    engine: SelfHealingEngine,
    decision_result: DecisionPolicyResult,
    context: ActionContext,
    *,
    lark_notifier: Optional[Any] = None,
) -> ActionExecutionBundle:
    context.decision_context.setdefault("recommended_owner", decision_result.recommended_owner or "backend_owner")
    context.decision_context.setdefault("release_critical", bool(decision_result.secondary_signals.get("release_critical")))
    context.decision_context.setdefault("protected_path", bool(decision_result.secondary_signals.get("protected_path")))
    bundle = engine.execute(decision_result, context)
    if lark_notifier is not None:
        try:
            lark_notifier.notify_self_healing(action_bundle=bundle, action_context=context)
        except Exception:
            pass
    return bundle
