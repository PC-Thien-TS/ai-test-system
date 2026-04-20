from __future__ import annotations

from typing import Optional

from orchestrator.adapters import get_active_adapter
from orchestrator.decision.application.engine import DecisionPolicyEngine


def build_decision_policy_engine(
    *,
    profile_name: Optional[str] = None,
    adapter_profile_overrides: Optional[dict[str, str]] = None,
) -> DecisionPolicyEngine:
    adapter = get_active_adapter()
    return DecisionPolicyEngine(
        profile_name=profile_name,
        adapter_id=adapter.get_adapter_id(),
        adapter_profile_overrides=adapter_profile_overrides,
    )
