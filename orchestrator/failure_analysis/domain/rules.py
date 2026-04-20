from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from .models import FailureInference


@dataclass(frozen=True)
class PatternRule:
    patterns: Tuple[str, ...]
    category: str
    owner: str
    severity: str
    recommended_action: str
    area: str


RULES: Sequence[PatternRule] = (
    PatternRule(
        patterns=("missing integer status",),
        category="api_contract_mismatch",
        owner="backend_api_owner",
        severity="high",
        recommended_action="Fix payload contract to include integer status field and update response validation.",
        area="api_contract",
    ),
    PatternRule(
        patterns=("unexpected status 500",),
        category="server_error",
        owner="backend_service_owner",
        severity="critical",
        recommended_action="Investigate unhandled exception path and add controlled error handling for API endpoint.",
        area="backend_service",
    ),
    PatternRule(
        patterns=(
            "status phase mismatch",
            "not terminal for terminal seed order",
            "eventual convergence",
        ),
        category="cross_surface_consistency",
        owner="order_state_owner",
        severity="critical",
        recommended_action="Investigate order state synchronization across user/admin/merchant surfaces.",
        area="order_state",
    ),
    PatternRule(
        patterns=("unexpected status 200, expected [400]",),
        category="state_transition_guard_missing",
        owner="merchant_flow_owner",
        severity="high",
        recommended_action="Add missing transition guard to reject invalid state mutation with controlled 4xx response.",
        area="merchant_flow",
    ),
)


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def infer_failure(nodeid: str, message: str) -> FailureInference:
    searchable = f"{nodeid} {message}".lower()
    for rule in RULES:
        if any(pattern in searchable for pattern in rule.patterns):
            return FailureInference(
                category=rule.category,
                owner=rule.owner,
                severity=rule.severity,
                recommended_action=rule.recommended_action,
                area=rule.area,
            )
    return FailureInference(
        category="unknown_failure_pattern",
        owner="qa_lead",
        severity="medium",
        recommended_action="Perform manual triage and add deterministic failure rule after root cause is confirmed.",
        area=infer_area_from_nodeid(nodeid),
    )


def highest_severity(values: List[str]) -> str:
    if not values:
        return "low"
    return max(values, key=lambda s: SEVERITY_ORDER.get(str(s).lower(), 0))


def infer_area_from_nodeid(nodeid: str) -> str:
    lowered = nodeid.lower()
    if "admin_consistency" in lowered:
        return "admin_consistency"
    if "merchant" in lowered:
        return "merchant_flow"
    if "search_store" in lowered or "store" in lowered:
        return "search_store"
    if "payment" in lowered:
        return "payment_flow"
    if "order_lifecycle" in lowered or "order" in lowered:
        return "order_flow"
    if "::" in nodeid:
        return nodeid.split("::", 1)[0].replace("\\", "/")
    return "unknown_area"

