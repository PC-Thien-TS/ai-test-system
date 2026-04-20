from __future__ import annotations

from typing import Any, Dict, Optional

from ..application.engine import DecisionPolicyEngine


def build_decision_policy_engine(
    *,
    default_profile_name: str = "balanced",
    adapter_profile_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> DecisionPolicyEngine:
    return DecisionPolicyEngine(
        default_profile_name=default_profile_name,
        adapter_profile_overrides=adapter_profile_overrides or {},
    )

