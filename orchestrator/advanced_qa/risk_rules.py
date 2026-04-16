"""Rule tables and helpers for deterministic risk prioritization."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set, Tuple

from orchestrator.advanced_qa.requirement_models import PlanBucket, RiskLevel
from orchestrator.advanced_qa.requirement_rules import normalize_priority, tokenize_text
from orchestrator.advanced_qa.risk_models import BlastRadius, ExecutionDepth, PriorityLevel

MODULE_CRITICALITY_WEIGHTS: Dict[str, float] = {
    "Payment": 0.36,
    "Order Creation": 0.33,
    "Order Lifecycle": 0.33,
    "Permission / Security": 0.32,
    "Auth & Account": 0.30,
    "Search & Discovery": 0.22,
    "Cart": 0.22,
    "Merchant Operations": 0.21,
    "Admin Operations": 0.20,
    "Booking / Reservation": 0.16,
    "Verification / Email": 0.16,
    "Notifications": 0.14,
    "Store Detail & Menu": 0.18,
    "Exploratory High-Risk Flows": 0.18,
}

PLAN_BUCKET_WEIGHTS: Dict[PlanBucket, float] = {
    PlanBucket.SMOKE: 0.18,
    PlanBucket.REGRESSION: 0.12,
    PlanBucket.EDGE_CASE: 0.20,
    PlanBucket.PERMISSION: 0.18,
    PlanBucket.INTEGRATION: 0.17,
    PlanBucket.ACCEPTANCE: 0.10,
    PlanBucket.HIGH_RISK: 0.24,
}

RISK_LEVEL_WEIGHTS: Dict[RiskLevel, float] = {
    RiskLevel.LOW: 0.06,
    RiskLevel.MEDIUM: 0.16,
    RiskLevel.HIGH: 0.28,
    RiskLevel.CRITICAL: 0.40,
}

PRIORITY_WEIGHTS: Dict[str, float] = {
    "p0": 0.22,
    "p1": 0.15,
    "p2": 0.09,
    "p3": 0.04,
}

GAP_TYPE_WEIGHTS: Dict[str, float] = {
    "missing_acceptance_criteria": 0.08,
    "missing_role_coverage": 0.12,
    "missing_error_path_coverage": 0.16,
    "missing_state_transition_coverage": 0.18,
    "missing_flow_dependency": 0.12,
    "business_rule_uncovered": 0.14,
    "inferred_role_not_explicit": 0.06,
}

SOURCE_TYPE_BASE_WEIGHTS: Dict[str, float] = {
    "plan": 0.08,
    "test_case": 0.10,
    "coverage_gap": 0.14,
}

BLAST_RADIUS_SEVERITY: Dict[BlastRadius, int] = {
    BlastRadius.NARROW: 0,
    BlastRadius.MEDIUM: 1,
    BlastRadius.WIDE: 2,
}

EXECUTION_DEPTH_SEVERITY: Dict[ExecutionDepth, int] = {
    ExecutionDepth.BASIC: 0,
    ExecutionDepth.STANDARD: 1,
    ExecutionDepth.DEEP: 2,
}

EXPLORATORY_TRIGGER_KEYWORDS: Set[str] = {
    "callback",
    "webhook",
    "retry",
    "race",
    "duplicate",
    "state_transition",
    "state transition",
    "permission",
    "timeout",
    "stale",
}

DEEP_EXECUTION_KEYWORDS: Set[str] = {
    "callback",
    "webhook",
    "state transition",
    "state_transition",
    "timeout",
    "retry",
    "duplicate",
    "permission",
    "invalid",
}

WIDE_RADIUS_KEYWORDS: Set[str] = {
    "payment",
    "order",
    "checkout",
    "state transition",
    "permission",
    "auth",
    "callback",
}

CRITICAL_MODULES: Set[str] = {
    "Payment",
    "Order Creation",
    "Order Lifecycle",
    "Auth & Account",
    "Permission / Security",
}

MEDIUM_HIGH_MODULES: Set[str] = {
    "Search & Discovery",
    "Cart",
    "Merchant Operations",
    "Admin Operations",
}


def safe_module_weight(module_name: str | None) -> float:
    """Return module criticality weight with deterministic fallback."""

    if not module_name:
        return 0.10
    return MODULE_CRITICALITY_WEIGHTS.get(module_name, 0.10)


def safe_priority_weight(priority: str | None) -> float:
    """Return normalized requirement priority weight."""

    normalized = normalize_priority(priority)
    return PRIORITY_WEIGHTS.get(normalized, PRIORITY_WEIGHTS["p2"])


def safe_risk_level_weight(level: RiskLevel | None) -> float:
    """Return risk level weight with fallback."""

    if level is None:
        return RISK_LEVEL_WEIGHTS[RiskLevel.MEDIUM]
    return RISK_LEVEL_WEIGHTS.get(level, RISK_LEVEL_WEIGHTS[RiskLevel.MEDIUM])


def safe_bucket_weight(bucket: PlanBucket | None) -> float:
    """Return plan bucket weight."""

    if bucket is None:
        return 0.10
    return PLAN_BUCKET_WEIGHTS.get(bucket, 0.10)


def safe_gap_weight(gap_type: str | None) -> float:
    """Return coverage gap influence weight."""

    if not gap_type:
        return 0.10
    return GAP_TYPE_WEIGHTS.get(gap_type, 0.10)


def map_score_to_priority_level(score: float) -> PriorityLevel:
    """Map priority score to stable priority levels."""

    if score >= 0.95:
        return PriorityLevel.CRITICAL
    if score >= 0.72:
        return PriorityLevel.HIGH
    if score >= 0.45:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def recommend_execution_depth(
    module: str,
    text_fragments: Sequence[str],
    score: float,
    priority_level: PriorityLevel,
    source_type: str,
) -> Tuple[ExecutionDepth, List[str]]:
    """Recommend execution depth with explicit reasons."""

    text = tokenize_text(list(text_fragments) + [module])
    reasons: List[str] = []

    if module in CRITICAL_MODULES:
        reasons.append("critical_module")
    if any(keyword in text for keyword in DEEP_EXECUTION_KEYWORDS):
        reasons.append("complex_behavior")
    if source_type == "coverage_gap":
        reasons.append("coverage_gap_item")

    if module in CRITICAL_MODULES and (priority_level in {PriorityLevel.CRITICAL, PriorityLevel.HIGH}):
        return ExecutionDepth.DEEP, reasons + ["critical_module_high_priority"]

    if any(keyword in text for keyword in DEEP_EXECUTION_KEYWORDS) and score >= 0.68:
        return ExecutionDepth.DEEP, reasons + ["keyword_driven_deep"]

    if "smoke" in text and priority_level == PriorityLevel.LOW:
        return ExecutionDepth.BASIC, reasons + ["smoke_low_priority"]

    if priority_level in {PriorityLevel.CRITICAL, PriorityLevel.HIGH}:
        return ExecutionDepth.STANDARD, reasons + ["high_priority_standard"]

    return ExecutionDepth.BASIC if source_type == "plan" and "smoke" in text else ExecutionDepth.STANDARD, reasons or ["default_depth"]


def recommend_blast_radius(
    module: str,
    text_fragments: Sequence[str],
    score: float,
    role_count: int,
    dependency_count: int,
) -> Tuple[BlastRadius, List[str]]:
    """Estimate blast radius hint from module and behavior signals."""

    text = tokenize_text(list(text_fragments) + [module])
    reasons: List[str] = []

    if module in CRITICAL_MODULES:
        reasons.append("critical_module")
    if any(keyword in text for keyword in WIDE_RADIUS_KEYWORDS):
        reasons.append("critical_flow_keyword")
    if role_count > 1:
        reasons.append("cross_role")
    if dependency_count >= 2:
        reasons.append("dependency_chain")

    if module in CRITICAL_MODULES and (score >= 0.70 or role_count > 1):
        return BlastRadius.WIDE, reasons + ["critical_module_with_complexity"]

    if any(keyword in text for keyword in WIDE_RADIUS_KEYWORDS) and score >= 0.78:
        return BlastRadius.WIDE, reasons + ["high_score_critical_keyword"]

    if module in MEDIUM_HIGH_MODULES or role_count > 1 or dependency_count >= 1:
        return BlastRadius.MEDIUM, reasons + ["medium_operational_impact"]

    return BlastRadius.NARROW, reasons or ["localized_impact"]


def should_flag_exploratory(
    text_fragments: Sequence[str],
    module: str,
    priority_level: PriorityLevel,
    depth: ExecutionDepth,
    role_count: int,
) -> bool:
    """Determine whether item should be flagged for exploratory follow-up."""

    text = tokenize_text(list(text_fragments) + [module])

    keyword_hit = any(keyword in text for keyword in EXPLORATORY_TRIGGER_KEYWORDS)
    cross_role = role_count > 1
    deep_or_critical = depth == ExecutionDepth.DEEP or priority_level == PriorityLevel.CRITICAL

    return keyword_hit and (deep_or_critical or cross_role)


def make_tiebreak_key(parts: Iterable[str]) -> str:
    """Build stable tie-break key for deterministic queue ordering."""

    return "::".join(str(part) for part in parts)
