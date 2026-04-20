from __future__ import annotations

from typing import Any, Dict, Optional

from ..application.engine import DecisionPolicyEngine
from ..domain.models import DecisionPolicyInput
from orchestrator.connectors.lark.domain.models import NormalizedLarkSourceContext


def build_self_healing_policy_instruction(
    engine: DecisionPolicyEngine,
    input_data: DecisionPolicyInput,
    *,
    lark_notifier: Optional[Any] = None,
) -> Dict[str, Any]:
    result = engine.evaluate(input_data)
    if lark_notifier is not None:
        try:
            lark_notifier.notify_decision(
                decision_result=result,
                source_context=NormalizedLarkSourceContext(
                    adapter_id=input_data.adapter_id,
                    project_id=input_data.project_id,
                    run_id=input_data.run_id,
                    severity=input_data.severity,
                    confidence=input_data.confidence,
                    occurrence_count=input_data.occurrence_count,
                    root_cause=input_data.triage_root_cause or "",
                    metadata={"source": "self_healing_policy"},
                ),
            )
        except Exception:
            pass
    instruction = engine.build_self_healing_instruction(result)
    return {
        "policy_result": result,
        "self_healing_instruction": instruction,
    }
