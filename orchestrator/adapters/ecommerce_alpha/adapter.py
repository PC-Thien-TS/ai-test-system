from __future__ import annotations

from typing import Any

from orchestrator.adapters.base.adapter_contract import ProjectAdapter
from orchestrator.adapters.base.models import (
    BlockerClassification,
    DefectFamilyDefinition,
    FlowDefinition,
)
from orchestrator.adapters.ecommerce_alpha.blocker_rules import classify_blocker
from orchestrator.adapters.ecommerce_alpha.change_mapping import map_changed_files_to_flows
from orchestrator.adapters.ecommerce_alpha.defect_registry import DEFECT_FAMILIES
from orchestrator.adapters.ecommerce_alpha.flow_registry import (
    CORE_ANCHOR_FLOWS,
    FLOW_ORDER,
    FLOW_REGISTRY,
    RELEASE_CRITICAL_FLOWS,
)
from orchestrator.adapters.ecommerce_alpha.risk_rules import (
    DEFAULT_INTENT,
    DEFAULT_MODE,
    INTENT_CHOICES,
    INTENT_FLOW_BASE,
    MODE_CHOICES,
    RELEASE_SCORING_RULES,
    infer_family_flow,
    map_defect_to_flows,
    map_risk_text_to_flow,
)
from orchestrator.adapters.ecommerce_alpha.suite_registry import SUITE_CATALOG


class EcommerceAlphaAdapter(ProjectAdapter):
    def get_adapter_id(self) -> str:
        return "ecommerce_alpha"

    def get_product_name(self) -> str:
        return "EcommerceAlpha"

    def get_flow_registry(self) -> dict[str, FlowDefinition]:
        return FLOW_REGISTRY

    def get_flow_order(self) -> tuple[str, ...]:
        return FLOW_ORDER

    def get_release_critical_flows(self) -> tuple[str, ...]:
        return RELEASE_CRITICAL_FLOWS

    def get_core_anchor_flows(self) -> tuple[str, ...]:
        return CORE_ANCHOR_FLOWS

    def get_intent_choices(self) -> tuple[str, ...]:
        return INTENT_CHOICES

    def get_mode_choices(self) -> tuple[str, ...]:
        return MODE_CHOICES

    def get_default_intent(self) -> str:
        return DEFAULT_INTENT

    def get_default_mode(self) -> str:
        return DEFAULT_MODE

    def get_intent_flow_base(self) -> dict[str, tuple[str, ...]]:
        return INTENT_FLOW_BASE

    def map_risk_text_to_flow(self, risk_text: str) -> str | None:
        return map_risk_text_to_flow(risk_text)

    def map_changed_files_to_flows(self, files: list[str]) -> dict[str, list[str]]:
        return map_changed_files_to_flows(files)

    def get_defect_families(self) -> list[DefectFamilyDefinition]:
        return list(DEFECT_FAMILIES)

    def classify_blocker(self, finding: Any) -> BlockerClassification:
        return classify_blocker(finding)

    def get_risk_rules(self) -> dict[str, Any]:
        return {
            "intent_choices": INTENT_CHOICES,
            "mode_choices": MODE_CHOICES,
            "intent_flow_base": INTENT_FLOW_BASE,
        }

    def get_release_scoring_rules(self) -> dict[str, Any]:
        return RELEASE_SCORING_RULES

    def get_suite_catalog(self) -> dict[str, dict[str, str]]:
        return SUITE_CATALOG

    def map_defect_to_flows(self, finding_id: str, title: str) -> list[str]:
        return map_defect_to_flows(finding_id, title)

    def infer_family_flow(self, family_id: str, title: str) -> str | None:
        return infer_family_flow(family_id, title)

    def build_defect_families(
        self,
        *,
        release_data: dict[str, Any],
        rerun_data: dict[str, Any],
        lastfailed_case_ids: list[str],
        merchant_missing_slots: list[str],
    ) -> list[dict[str, Any]]:
        # TODO: Replace this with project-specific family clustering logic.
        return []

