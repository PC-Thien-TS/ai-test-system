from __future__ import annotations

from orchestrator.decision.application.engine import DecisionPolicyEngine
from orchestrator.decision.domain.models import DecisionPolicyInput


def build_release_policy_signal(
    *,
    engine: DecisionPolicyEngine,
    value: DecisionPolicyInput,
) -> dict:
    result = engine.evaluate(value)
    severity = str(result.secondary_signals.get("severity_level", "low"))
    penalty = 0
    if result.should_block_release:
        penalty = -20 if severity == "critical" else -12
    elif result.should_escalate:
        penalty = -8
    elif result.should_open_bug_candidate:
        penalty = -4
    return {
        "decision": result.primary_decision.value,
        "should_block_release": result.should_block_release,
        "should_escalate": result.should_escalate,
        "penalty_recommendation": penalty,
        "rationale": result.rationale,
        "policy_result": result.to_dict(),
    }
