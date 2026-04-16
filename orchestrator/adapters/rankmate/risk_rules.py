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
    "order_flow_regression": ("order_core",),
    "merchant_flow_regression": ("merchant_handling",),
    "search_store_regression": ("search_discovery",),
    "payment_regression": ("payment_integrity",),
    "release_gate_regression": ("auth_foundation", "order_core", "admin_consistency"),
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
    if any(token in value for token in ("merchant", "terminal mutation", "transition")):
        return "merchant_handling"
    if any(token in value for token in ("payment", "stripe", "webhook")):
        return "payment_integrity"
    if any(token in value for token in ("store", "search", "discovery")):
        return "search_discovery"
    if "auth" in value:
        return "auth_foundation"
    if any(token in value for token in ("order", "lifecycle")):
        return "order_core"
    if any(token in value for token in ("admin", "consistency")):
        return "admin_consistency"
    return None


def map_defect_to_flows(finding_id: str, title: str) -> list[str]:
    text = f"{finding_id} {title}".lower()
    flows: list[str] = []
    if any(token in text for token in ("store", "search", "sto-", "store-api")):
        flows.append("search_discovery")
    if any(token in text for token in ("merchant", "mer-")):
        flows.append("merchant_handling")
    if any(token in text for token in ("payment", "pay-api", "stripe", "momo")):
        flows.append("payment_integrity")
    if any(token in text for token in ("auth", "login", "token")):
        flows.append("auth_foundation")
    if any(token in text for token in ("order", "ord-")):
        flows.append("order_core")
    if any(token in text for token in ("admin", "consistency", "aord-")):
        flows.append("admin_consistency")
    return sorted(set(flows))


def infer_family_flow(family_id: str, title: str) -> str | None:
    mapped = map_defect_to_flows(family_id, title)
    return mapped[0] if mapped else None

