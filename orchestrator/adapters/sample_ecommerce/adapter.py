from __future__ import annotations

from typing import Any

from orchestrator.adapters.base.adapter_contract import ProjectAdapter
from orchestrator.adapters.base.models import (
    BlockerClassification,
    DefectFamilyDefinition,
    FlowDefinition,
)


class SampleEcommerceAdapter(ProjectAdapter):
    """Minimal reference adapter proving multi-project architecture readiness."""

    _flows: dict[str, FlowDefinition] = {
        "auth": FlowDefinition(
            flow_id="auth",
            title="Auth Flow",
            description="Sample auth baseline flow.",
            suites=("tests/sample/test_auth.py",),
            release_critical=True,
        ),
        "checkout": FlowDefinition(
            flow_id="checkout",
            title="Checkout Flow",
            description="Sample checkout flow.",
            suites=("tests/sample/test_checkout.py",),
            release_critical=True,
        ),
    }

    def get_adapter_id(self) -> str:
        return "sample_ecommerce"

    def get_product_name(self) -> str:
        return "Sample Ecommerce"

    def get_flow_registry(self) -> dict[str, FlowDefinition]:
        return self._flows

    def get_flow_order(self) -> tuple[str, ...]:
        return ("auth", "checkout")

    def get_release_critical_flows(self) -> tuple[str, ...]:
        return ("auth", "checkout")

    def get_core_anchor_flows(self) -> tuple[str, ...]:
        return ("auth", "checkout")

    def get_intent_choices(self) -> tuple[str, ...]:
        return ("full_app_fast_regression",)

    def get_mode_choices(self) -> tuple[str, ...]:
        return ("fast", "balanced", "deep")

    def get_default_intent(self) -> str:
        return "full_app_fast_regression"

    def get_default_mode(self) -> str:
        return "fast"

    def get_intent_flow_base(self) -> dict[str, tuple[str, ...]]:
        return {"full_app_fast_regression": ("auth", "checkout")}

    def map_risk_text_to_flow(self, risk_text: str) -> str | None:
        text = (risk_text or "").lower()
        if "auth" in text:
            return "auth"
        if "checkout" in text or "payment" in text:
            return "checkout"
        return None

    def map_changed_files_to_flows(self, files: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for path in files:
            lowered = path.lower()
            if "auth" in lowered:
                result.setdefault("auth", []).append(path)
            if "checkout" in lowered or "payment" in lowered:
                result.setdefault("checkout", []).append(path)
        return result

    def get_defect_families(self) -> list[DefectFamilyDefinition]:
        return []

    def classify_blocker(self, finding: Any) -> BlockerClassification:
        return BlockerClassification(blocker_type="unknown", reason=f"Unclassified blocker: {finding}")

    def get_risk_rules(self) -> dict[str, Any]:
        return {}

    def get_release_scoring_rules(self) -> dict[str, Any]:
        return {
            "phase_weights": {"auth": 50, "checkout": 50},
            "severity_penalties": {"P0": -25, "P1": -15, "P2": -8},
            "env_blocker_penalties": {"critical": -10, "medium": -5},
            "coverage_gap_penalties": {"high": -6, "medium": -4, "low": -3},
            "thresholds": {"release": 85, "release_with_caution": 65},
        }

    def get_suite_catalog(self) -> dict[str, dict[str, str]]:
        return {
            "auth": {"suite": "tests/sample/test_auth.py", "priority": "P0", "blast_radius": "core-flow"},
            "checkout": {"suite": "tests/sample/test_checkout.py", "priority": "P1", "blast_radius": "release-critical"},
        }

    def map_defect_to_flows(self, finding_id: str, title: str) -> list[str]:
        text = f"{finding_id} {title}".lower()
        if "auth" in text:
            return ["auth"]
        if "checkout" in text or "payment" in text:
            return ["checkout"]
        return []

    def infer_family_flow(self, family_id: str, title: str) -> str | None:
        mapped = self.map_defect_to_flows(family_id, title)
        return mapped[0] if mapped else None

    def build_defect_families(
        self,
        *,
        release_data: dict[str, Any],
        rerun_data: dict[str, Any],
        lastfailed_case_ids: list[str],
        merchant_missing_slots: list[str],
    ) -> list[dict[str, Any]]:
        return []

