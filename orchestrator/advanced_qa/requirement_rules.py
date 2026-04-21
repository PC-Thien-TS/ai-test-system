"""Rule tables and helper heuristics for requirement-aware generation."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from orchestrator.advanced_qa.requirement_models import PlanBucket, RiskLevel

RANKMATE_MODULES: List[str] = [
    "Auth & Account",
    "Search & Discovery",
    "Store Detail & Menu",
    "Cart",
    "Booking / Reservation",
    "Order Creation",
    "Payment",
    "Order Lifecycle",
    "Merchant Operations",
    "Admin Operations",
    "Notifications",
    "Verification / Email",
    "Permission / Security",
    "Exploratory High-Risk Flows",
]

MODULE_KEYWORDS: Dict[str, Set[str]] = {
    "Auth & Account": {"auth", "login", "register", "password", "account", "session", "signin"},
    "Search & Discovery": {"search", "discover", "query", "keyword", "filter", "ranking"},
    "Store Detail & Menu": {"store detail", "menu", "sku", "item detail", "catalog", "merchant page"},
    "Cart": {"cart", "basket", "add item", "remove item", "quantity"},
    "Booking / Reservation": {"booking", "reservation", "timeslot", "schedule", "reserve"},
    "Order Creation": {"checkout", "create order", "place order", "submit order", "duplicate checkout"},
    "Payment": {"payment", "pay", "callback", "webhook", "refund", "retry", "timeout"},
    "Order Lifecycle": {"order status", "state transition", "lifecycle", "cancel", "confirm", "reject"},
    "Merchant Operations": {"merchant", "shop owner", "merchant confirm", "merchant reject"},
    "Admin Operations": {"admin", "backoffice", "operation panel", "moderation", "tracking"},
    "Notifications": {"notification", "push", "email notify", "sms", "alert", "reminder"},
    "Verification / Email": {"verify email", "email binding", "verification", "otp", "code"},
    "Permission / Security": {"permission", "role", "rbac", "security", "access control", "authorization"},
}

FLOW_KEYWORDS: Dict[str, Set[str]] = {
    "login_register_verify": {"login", "register", "verify", "email binding"},
    "search_to_store_detail": {"search", "store detail", "discover", "query"},
    "store_detail_to_cart": {"store detail", "add to cart", "menu", "cart"},
    "cart_to_checkout": {"cart", "checkout"},
    "checkout_create_order": {"checkout", "create order", "place order"},
    "order_to_payment_init": {"order", "payment init", "payment", "pay"},
    "payment_callback_retry_timeout": {"payment callback", "retry", "timeout", "webhook"},
    "merchant_confirm_reject": {"merchant confirm", "merchant reject", "merchant"},
    "admin_tracking": {"admin", "tracking", "monitor"},
    "notification_triggers": {"notification", "notify", "email", "sms", "trigger"},
    "cancellation_invalid_state_transition": {"cancel", "invalid state", "state transition", "lifecycle"},
}

ROLE_KEYWORDS: Dict[str, Set[str]] = {
    "user": {"user", "customer", "buyer"},
    "merchant": {"merchant", "shop owner", "seller"},
    "admin": {"admin", "operator", "ops"},
    "system": {"system", "service", "scheduler", "worker"},
}

RISK_SIGNAL_KEYWORDS: Dict[str, Tuple[float, str]] = {
    "payment": (0.30, "payment_related"),
    "order": (0.25, "order_related"),
    "auth": (0.20, "auth_related"),
    "permission": (0.20, "permission_related"),
    "state transition": (0.15, "state_transition_complexity"),
    "callback": (0.20, "callback_webhook"),
    "webhook": (0.20, "callback_webhook"),
    "retry": (0.10, "retry_path"),
    "timeout": (0.10, "timeout_path"),
    "checkout": (0.10, "critical_user_flow"),
    "login": (0.10, "critical_user_flow"),
    "search": (0.08, "critical_user_flow"),
}

EDGE_CASE_KEYWORDS: Set[str] = {
    "retry",
    "timeout",
    "invalid",
    "error",
    "duplicate",
    "reject",
    "cancel",
    "fail",
    "fallback",
}

STATE_TRANSITION_KEYWORDS: Set[str] = {
    "state",
    "transition",
    "lifecycle",
    "status",
    "confirm",
    "reject",
    "cancel",
}


def normalize_priority(value: str | None) -> str:
    """Normalize priority strings to p0/p1/p2/p3."""

    if not value:
        return "p2"

    text = value.strip().lower()
    aliases = {
        "critical": "p0",
        "high": "p1",
        "medium": "p2",
        "low": "p3",
        "p0": "p0",
        "p1": "p1",
        "p2": "p2",
        "p3": "p3",
    }
    return aliases.get(text, "p2")


def normalize_module_name(value: str | None) -> str | None:
    """Normalize module names to known RankMate module labels when possible."""

    if not value:
        return None

    target = value.strip().lower()
    for module_name in RANKMATE_MODULES:
        if module_name.lower() == target:
            return module_name

    compact = re.sub(r"[^a-z0-9]+", "", target)
    for module_name in RANKMATE_MODULES:
        module_compact = re.sub(r"[^a-z0-9]+", "", module_name.lower())
        if compact == module_compact:
            return module_name

    return value.strip()


def tokenize_text(parts: Sequence[str]) -> str:
    """Join text parts into lowercase searchable content."""

    return " ".join(part for part in parts if part).strip().lower()


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """Deduplicate while preserving order."""

    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


def detect_roles(text: str) -> List[str]:
    """Detect role names from free text."""

    detected: List[str] = []
    for role_name, keywords in ROLE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            detected.append(role_name)
    return dedupe_preserve_order(detected)


def detect_modules(text: str) -> List[str]:
    """Detect RankMate modules from free text."""

    modules: List[str] = []
    for module_name, keywords in MODULE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            modules.append(module_name)
    return dedupe_preserve_order(modules)


def detect_flows(text: str) -> List[str]:
    """Detect related flow family names."""

    flows: List[str] = []
    for flow_name, keywords in FLOW_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            flows.append(flow_name)
    return dedupe_preserve_order(flows)


def determine_risk_level(score: float) -> RiskLevel:
    """Map a numeric risk score to a risk level."""

    if score >= 0.8:
        return RiskLevel.CRITICAL
    if score >= 0.6:
        return RiskLevel.HIGH
    if score >= 0.35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def needs_negative_coverage(text: str) -> bool:
    """Return True when requirement text suggests error-path testing is required."""

    return any(keyword in text for keyword in EDGE_CASE_KEYWORDS)


def needs_state_transition_coverage(text: str) -> bool:
    """Return True when requirement text implies state transition verification."""

    return any(keyword in text for keyword in STATE_TRANSITION_KEYWORDS)


def infer_plan_buckets(priority: str, risk_level: RiskLevel, text: str, has_acceptance: bool, role_count: int, has_dependencies: bool) -> List[PlanBucket]:
    """Infer plan buckets from requirement properties."""

    buckets: List[PlanBucket] = [PlanBucket.REGRESSION]

    if priority in {"p0", "p1"} or risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        buckets.append(PlanBucket.SMOKE)

    if has_acceptance:
        buckets.append(PlanBucket.ACCEPTANCE)

    if role_count > 1 or "permission" in text or "auth" in text or "role" in text:
        buckets.append(PlanBucket.PERMISSION)

    if has_dependencies or "callback" in text or "webhook" in text or "integration" in text:
        buckets.append(PlanBucket.INTEGRATION)

    if needs_negative_coverage(text):
        buckets.append(PlanBucket.EDGE_CASE)

    if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        buckets.append(PlanBucket.HIGH_RISK)

    return list(dict.fromkeys(buckets))


def build_risk_signals(priority: str, changed_area: bool, role_count: int, text: str) -> Tuple[float, List[str]]:
    """Calculate risk score and collect explicit risk signals."""

    score = 0.0
    signals: List[str] = []

    for keyword, (weight, signal) in RISK_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += weight
            signals.append(signal)

    if changed_area:
        score += 0.15
        signals.append("changed_area")

    if role_count > 1:
        score += 0.15
        signals.append("cross_role_dependency")

    if priority == "p0":
        score += 0.10
        signals.append("priority_p0")
    elif priority == "p1":
        score += 0.05
        signals.append("priority_p1")

    return min(score, 1.0), dedupe_preserve_order(signals)
