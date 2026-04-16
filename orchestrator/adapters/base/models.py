from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FlowDefinition:
    flow_id: str
    title: str
    description: str
    suites: tuple[str, ...]
    release_critical: bool = False


@dataclass(frozen=True)
class DefectFamilyDefinition:
    family_id: str
    title: str
    family_type: str  # product_defect | env_blocker | coverage_gap | unknown
    severity: str
    release_impact: str
    member_cases: tuple[str, ...] = field(default_factory=tuple)
    recommended_next_action: str = ""


@dataclass(frozen=True)
class BlockerClassification:
    blocker_type: str  # env_blocker | product_defect | coverage_gap | unknown
    reason: str


@dataclass(frozen=True)
class AdapterMetadata:
    adapter_id: str
    product_name: str
    version: str
    notes: str = ""


AdapterJson = dict[str, Any]
