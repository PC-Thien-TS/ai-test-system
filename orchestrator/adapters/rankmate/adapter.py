from __future__ import annotations

from typing import Any

from orchestrator.adapters.base.adapter_contract import ProjectAdapter
from orchestrator.adapters.base.models import (
    BlockerClassification,
    DefectFamilyDefinition,
    FlowDefinition,
)
from orchestrator.adapters.rankmate.blocker_rules import classify_blocker
from orchestrator.adapters.rankmate.change_mapping import map_changed_files_to_flows
from orchestrator.adapters.rankmate.defect_registry import DEFECT_FAMILIES
from orchestrator.adapters.rankmate.flow_registry import (
    CORE_ANCHOR_FLOWS,
    FLOW_ORDER,
    FLOW_REGISTRY,
    RELEASE_CRITICAL_FLOWS,
)
from orchestrator.adapters.rankmate.risk_rules import (
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
from orchestrator.adapters.rankmate.suite_registry import SUITE_CATALOG


class RankMateAdapter(ProjectAdapter):
    def get_adapter_id(self) -> str:
        return "rankmate"

    def get_product_name(self) -> str:
        return "RankMate / Didaunao"

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
        families: list[dict[str, Any]] = []
        product_penalties = release_data.get("product_defect_penalties", [])
        product_ids = []
        if isinstance(product_penalties, list):
            product_ids = [str(item.get("id", "")).upper() for item in product_penalties if isinstance(item, dict)]

        store_members = sorted(
            {
                cid
                for cid in (product_ids + lastfailed_case_ids)
                if cid in {"STORE-API-004", "STO-011", "STO-009"}
            }
        )
        if store_members:
            families.append(
                {
                    "family_id": "DF-STORE-NEGATIVE-500",
                    "title": "Store invalid lookup negative-path returns 500",
                    "member_cases": store_members,
                    "type": "product_defect",
                    "severity_suggestion": "P2",
                    "release_impact": "release-critical",
                    "recommended_next_action": "Fix store invalid-id/unique-id handler to return controlled 400/404 envelopes.",
                    "evidence": ["release_decision.json", ".pytest_cache/v/cache/lastfailed"],
                }
            )

        if "MER-API-021" in lastfailed_case_ids:
            families.append(
                {
                    "family_id": "DF-MERCHANT-STALE-TERMINAL-MUTATION",
                    "title": "Merchant stale/double complete mutation safety defect",
                    "member_cases": ["MER-API-021"],
                    "type": "product_defect",
                    "severity_suggestion": "P1",
                    "release_impact": "release-critical",
                    "recommended_next_action": "Enforce terminal transition guards for stale/double complete and return controlled 4xx.",
                    "evidence": [
                        ".pytest_cache/v/cache/lastfailed",
                        "tests/rankmate_wave1/test_merchant_transition_api.py",
                    ],
                }
            )

        joined_text = " ".join(
            str(item)
            for item in (release_data.get("env_blockers", []) + rerun_data.get("blockers", []))
        ).lower()
        if "stripe" in joined_text and "secret" in joined_text:
            families.append(
                {
                    "family_id": "DF-STRIPE-WEBHOOK-ENV-BLOCKER",
                    "title": "Stripe webhook realism blocked by runtime secret/signature mismatch",
                    "member_cases": ["PAY-API-003", "PAY-API-004", "PAY-API-007", "PAY-API-008", "PAY-API-011"],
                    "type": "env_blocker",
                    "severity_suggestion": "blocker/env",
                    "release_impact": "partial-surface",
                    "recommended_next_action": "Align deployed Stripe webhook secret/signing contract with QA environment.",
                    "evidence": ["release_decision.json", "autonomous_rerun_plan.json"],
                }
            )

        if merchant_missing_slots:
            families.append(
                {
                    "family_id": "DF-MERCHANT-SEED-COVERAGE-GAP",
                    "title": "Merchant transition seed coverage gaps",
                    "member_cases": merchant_missing_slots,
                    "type": "coverage_gap",
                    "severity_suggestion": "coverage-gap",
                    "release_impact": "partial-surface",
                    "recommended_next_action": "Extend merchant seed builder and/or create targeted state-producing flows.",
                    "evidence": ["merchant_state_seeds.json"],
                }
            )

        return families

