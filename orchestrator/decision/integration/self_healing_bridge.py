from __future__ import annotations

from orchestrator.decision.application.engine import DecisionPolicyEngine
from orchestrator.decision.domain.models import DecisionPolicyInput


def build_self_healing_policy_instruction(
    *,
    engine: DecisionPolicyEngine,
    value: DecisionPolicyInput,
) -> dict:
    result = engine.evaluate(value)
    instruction = engine.build_self_healing_instruction(result)
    instruction["policy_result"] = result.to_dict()
    return instruction
