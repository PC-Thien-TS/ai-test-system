from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from orchestrator.adapters.base.models import (
    BlockerClassification,
    DefectFamilyDefinition,
    FlowDefinition,
)


class ProjectAdapter(ABC):
    """Contract for project-specific adapter implementations."""

    @abstractmethod
    def get_adapter_id(self) -> str:
        ...

    @abstractmethod
    def get_product_name(self) -> str:
        ...

    @abstractmethod
    def get_flow_registry(self) -> dict[str, FlowDefinition]:
        ...

    @abstractmethod
    def get_flow_order(self) -> tuple[str, ...]:
        ...

    @abstractmethod
    def get_release_critical_flows(self) -> tuple[str, ...]:
        ...

    @abstractmethod
    def get_core_anchor_flows(self) -> tuple[str, ...]:
        ...

    @abstractmethod
    def get_intent_choices(self) -> tuple[str, ...]:
        ...

    @abstractmethod
    def get_mode_choices(self) -> tuple[str, ...]:
        ...

    @abstractmethod
    def get_default_intent(self) -> str:
        ...

    @abstractmethod
    def get_default_mode(self) -> str:
        ...

    @abstractmethod
    def get_intent_flow_base(self) -> dict[str, tuple[str, ...]]:
        ...

    @abstractmethod
    def map_risk_text_to_flow(self, risk_text: str) -> str | None:
        ...

    @abstractmethod
    def map_changed_files_to_flows(self, files: list[str]) -> dict[str, list[str]]:
        """Return flow->reasons mapping for changed files."""
        ...

    @abstractmethod
    def get_defect_families(self) -> list[DefectFamilyDefinition]:
        ...

    @abstractmethod
    def classify_blocker(self, finding: Any) -> BlockerClassification:
        ...

    @abstractmethod
    def get_risk_rules(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_release_scoring_rules(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_suite_catalog(self) -> dict[str, dict[str, str]]:
        """Return suite registry keyed by flow_id."""
        ...

    @abstractmethod
    def map_defect_to_flows(self, finding_id: str, title: str) -> list[str]:
        ...

    @abstractmethod
    def infer_family_flow(self, family_id: str, title: str) -> str | None:
        ...

    @abstractmethod
    def build_defect_families(
        self,
        *,
        release_data: dict[str, Any],
        rerun_data: dict[str, Any],
        lastfailed_case_ids: list[str],
        merchant_missing_slots: list[str],
    ) -> list[dict[str, Any]]:
        ...
