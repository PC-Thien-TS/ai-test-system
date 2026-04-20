from __future__ import annotations

from orchestrator.decision.application.engine import DecisionPolicyEngine
from orchestrator.decision.domain.models import DecisionPolicyInput


def build_ci_policy_hint(
    *,
    engine: DecisionPolicyEngine,
    value: DecisionPolicyInput,
) -> dict:
    result = engine.evaluate(value)
    hint = engine.build_ci_decision_hint(result)
    hint["policy_result"] = result.to_dict()
    return hint
