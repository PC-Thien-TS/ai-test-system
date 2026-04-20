from __future__ import annotations

from typing import Any, Dict, Optional

from ..application.engine import DecisionPolicyEngine
from ..domain.models import DecisionPolicyInput
from orchestrator.connectors.lark.domain.models import NormalizedLarkSourceContext


def build_ci_policy_hint(
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
                    metadata={"source": "ci_gate"},
                ),
            )
        except Exception:
            pass
    hint = engine.build_ci_decision_hint(result)
    return {
        "policy_result": result,
        "ci_hint": hint,
    }
