from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .grouping import normalize_message_pattern
from .models import FailureInference


@dataclass(frozen=True, slots=True)
class FailurePatternRule:
    name: str
    patterns: tuple[str, ...]
    category: str
    owner: str
    severity: str
    recommended_action: str


RULES: tuple[FailurePatternRule, ...] = (
    FailurePatternRule(
        name="missing_integer_status",
        patterns=("missing integer status",),
        category="api_contract_mismatch",
        owner="backend_api_owner",
        severity="high",
        recommended_action="Fix API response contract to return integer status consistently.",
    ),
    FailurePatternRule(
        name="unexpected_status_500",
        patterns=("unexpected status 500",),
        category="server_error",
        owner="backend_service_owner",
        severity="critical",
        recommended_action="Investigate server-side exception path causing 500 responses.",
    ),
    FailurePatternRule(
        name="cross_surface_consistency",
        patterns=(
            "status phase mismatch",
            "not terminal for terminal seed order",
            "eventual convergence",
        ),
        category="cross_surface_consistency",
        owner="order_state_owner",
        severity="critical",
        recommended_action="Investigate order state synchronization across user/admin/merchant surfaces.",
    ),
    FailurePatternRule(
        name="state_transition_guard_missing",
        patterns=("unexpected status 200, expected [400]",),
        category="state_transition_guard_missing",
        owner="merchant_flow_owner",
        severity="high",
        recommended_action="Add terminal-state guard to reject invalid merchant transition with 4xx.",
    ),
)

DEFAULT_CATEGORY = "unknown_failure_pattern"
DEFAULT_OWNER = "qa_lead"
DEFAULT_SEVERITY = "medium"
DEFAULT_RECOMMENDED_ACTION = "Manual triage required to classify this new failure pattern."


def _matches(patterns: Iterable[str], normalized_message: str, raw_message: str) -> bool:
    for pattern in patterns:
        if pattern in normalized_message or pattern in raw_message:
            return True
    return False


def infer_failure(message: str) -> FailureInference:
    raw = (message or "").strip().lower()
    normalized = normalize_message_pattern(message)
    for rule in RULES:
        if _matches(rule.patterns, normalized, raw):
            return FailureInference(
                category=rule.category,
                owner=rule.owner,
                severity=rule.severity,
                recommended_action=rule.recommended_action,
                message_pattern=normalized,
                matched_rule=rule.name,
            )
    return FailureInference(
        category=DEFAULT_CATEGORY,
        owner=DEFAULT_OWNER,
        severity=DEFAULT_SEVERITY,
        recommended_action=DEFAULT_RECOMMENDED_ACTION,
        message_pattern=normalized,
        matched_rule="default_unknown_pattern",
    )


def collect_root_cause_categories(groups: List[dict] | List[FailureInference]) -> List[str]:
    categories: list[str] = []
    for entry in groups:
        category = entry["category"] if isinstance(entry, dict) else entry.category
        if category not in categories:
            categories.append(category)
    return categories
