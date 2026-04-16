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
{{INTENT_FLOW_BASE_ENTRIES}}
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
{{RISK_TEXT_FLOW_IFS}}
    return None


def map_defect_to_flows(finding_id: str, title: str) -> list[str]:
    text = f"{finding_id} {title}".lower()
    flows: list[str] = []
{{DEFECT_FLOW_IFS}}
    return sorted(set(flows))


def infer_family_flow(family_id: str, title: str) -> str | None:
    mapped = map_defect_to_flows(family_id, title)
    return mapped[0] if mapped else None

