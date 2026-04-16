from __future__ import annotations


INTENT_CHOICES: tuple[str, ...] = (
    "full_app_fast_regression",
    "order_flow_regression",
    "merchant_flow_regression",
    "search_store_regression",
    "payment_regression",
    "release_gate_regression",
)

MODE_CHOICES: tuple[str, ...] = ("fast", "balanced", "deep")

DEFAULT_INTENT = "full_app_fast_regression"
DEFAULT_MODE = "fast"

INTENT_FLOW_BASE: dict[str, tuple[str, ...]] = {
    "full_app_fast_regression": (),
    "order_flow_regression": ("order_management",),
    "merchant_flow_regression": ("order_management",),
    "search_store_regression": ("catalog_discovery",),
    "payment_regression": ("payment_integrity",),
    "release_gate_regression": ("auth_foundation", "admin_ops", "catalog_discovery"),
}

RELEASE_SCORING_RULES: dict[str, object] = {
    "phase_weights": {
        "auth": 25,
        "order_core": 25,
        "search_store": 15,
        "lifecycle": 15,
        "admin_consistency": 20,
    },
    "severity_penalties": {
        "P0": -25,
        "P1": -15,
        "P2": -8,
    },
    "env_blocker_penalties": {
        "critical": -10,
        "medium": -5,
    },
    "coverage_gap_penalties": {
        "high": -6,
        "medium": -4,
        "low": -3,
    },
    "thresholds": {
        "release": 85,
        "release_with_caution": 65,
    },
}


def map_risk_text_to_flow(risk_text: str) -> str | None:
    value = (risk_text or "").lower()
    if any(token in value for token in ("auth", "login", "token",)):
        return "auth_foundation"
    if any(token in value for token in ("catalog", "search", "discovery", "product",)):
        return "catalog_discovery"
    if any(token in value for token in ("cart", "checkout", "order",)):
        return "cart_checkout"
    if any(token in value for token in ("order", "fulfillment", "shipment",)):
        return "order_management"
    if any(token in value for token in ("payment", "billing", "transaction", "webhook",)):
        return "payment_integrity"
    if any(token in value for token in ("admin", "ops", "console",)):
        return "admin_ops"
    return None


def map_defect_to_flows(finding_id: str, title: str) -> list[str]:
    text = f"{finding_id} {title}".lower()
    flows: list[str] = []
    if any(token in text for token in ("auth", "foundation", "login", "token",)):
        flows.append("auth_foundation")
    if any(token in text for token in ("catalog", "discovery", "search",)):
        flows.append("catalog_discovery")
    if any(token in text for token in ("cart", "checkout", "order",)):
        flows.append("cart_checkout")
    if any(token in text for token in ("fulfillment", "management", "order", "shipment",)):
        flows.append("order_management")
    if any(token in text for token in ("billing", "integrity", "payment", "transaction",)):
        flows.append("payment_integrity")
    if any(token in text for token in ("admin", "console", "ops",)):
        flows.append("admin_ops")
    return sorted(set(flows))


def infer_family_flow(family_id: str, title: str) -> str | None:
    mapped = map_defect_to_flows(family_id, title)
    return mapped[0] if mapped else None

