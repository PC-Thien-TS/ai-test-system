"""Typed models for requirement-aware generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RequirementSourceType(str, Enum):
    """Supported requirement source types."""

    PRD = "prd"
    SRS = "srs"
    ACCEPTANCE = "acceptance_criteria"
    WORKFLOW = "workflow"
    API_CONTRACT = "api_contract"
    RELEASE_NOTES = "release_notes"
    BUSINESS_RULE = "business_rule"
    FEATURE_INVENTORY = "feature_inventory"
    UNKNOWN = "unknown"


class PlanBucket(str, Enum):
    """Execution buckets for generated test plans."""

    SMOKE = "smoke"
    REGRESSION = "regression"
    EDGE_CASE = "edge_case"
    PERMISSION = "permission"
    INTEGRATION = "integration"
    ACCEPTANCE = "acceptance"
    HIGH_RISK = "high_risk"


class RiskLevel(str, Enum):
    """Risk levels for requirements and test cases."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Requirement:
    """Normalized requirement record."""

    requirement_id: str
    title: str
    description: str
    module: Optional[str] = None
    submodule: Optional[str] = None
    source_type: RequirementSourceType = RequirementSourceType.UNKNOWN
    source_ref: Optional[str] = None
    acceptance_criteria: List[str] = field(default_factory=list)
    business_rules: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: str = "p2"
    risk_hints: List[str] = field(default_factory=list)
    related_flows: List[str] = field(default_factory=list)
    changed_area: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert requirement to a serializable dictionary."""

        return {
            "id": self.requirement_id,
            "title": self.title,
            "description": self.description,
            "module": self.module,
            "submodule": self.submodule,
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
            "acceptance_criteria": self.acceptance_criteria,
            "business_rules": self.business_rules,
            "roles": self.roles,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "risk_hints": self.risk_hints,
            "related_flows": self.related_flows,
            "changed_area": self.changed_area,
            "metadata": self.metadata,
        }


@dataclass
class GeneratedTestPlan:
    """Generated test plan bucket from requirement groups."""

    plan_id: str
    name: str
    bucket: PlanBucket
    module: str
    requirement_ids: List[str]
    rationale: List[str] = field(default_factory=list)
    priority: str = "p2"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to a serializable dictionary."""

        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "bucket": self.bucket.value,
            "module": self.module,
            "requirement_ids": self.requirement_ids,
            "rationale": self.rationale,
            "priority": self.priority,
            "tags": self.tags,
        }


@dataclass
class GeneratedTestCase:
    """Generated deterministic test case."""

    test_case_id: str
    title: str
    module: str
    submodule: Optional[str]
    scenario_type: str
    preconditions: List[str]
    steps: List[str]
    expected_result: str
    priority: str
    risk_level: RiskLevel
    related_requirement_ids: List[str]
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to a serializable dictionary."""

        return {
            "id": self.test_case_id,
            "title": self.title,
            "module": self.module,
            "submodule": self.submodule,
            "scenario_type": self.scenario_type,
            "preconditions": self.preconditions,
            "steps": self.steps,
            "expected_result": self.expected_result,
            "priority": self.priority,
            "risk_level": self.risk_level.value,
            "related_requirement_ids": self.related_requirement_ids,
            "tags": self.tags,
        }


@dataclass
class CoverageGapCandidate:
    """Coverage gap candidate identified during generation."""

    gap_id: str
    requirement_id: str
    gap_type: str
    severity: RiskLevel
    description: str
    suggested_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert coverage gap to a serializable dictionary."""

        return {
            "gap_id": self.gap_id,
            "requirement_id": self.requirement_id,
            "gap_type": self.gap_type,
            "severity": self.severity.value,
            "description": self.description,
            "suggested_actions": self.suggested_actions,
        }


@dataclass
class RequirementRiskMap:
    """Risk mapping output for a requirement."""

    requirement_id: str
    module: str
    risk_level: RiskLevel
    risk_score: float
    risk_signals: List[str] = field(default_factory=list)
    recommended_plan_buckets: List[PlanBucket] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert risk map to a serializable dictionary."""

        return {
            "requirement_id": self.requirement_id,
            "module": self.module,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "risk_signals": self.risk_signals,
            "recommended_plan_buckets": [bucket.value for bucket in self.recommended_plan_buckets],
        }


@dataclass
class RequirementGenerationResult:
    """Aggregate output for the requirement-aware generation pipeline."""

    requirements: List[Requirement]
    test_plans: List[GeneratedTestPlan]
    test_cases: List[GeneratedTestCase]
    coverage_gaps: List[CoverageGapCandidate]
    risk_maps: List[RequirementRiskMap]

    def to_dict(self) -> Dict[str, Any]:
        """Convert generation result to a serializable dictionary."""

        return {
            "requirements": [item.to_dict() for item in self.requirements],
            "test_plans": [item.to_dict() for item in self.test_plans],
            "test_cases": [item.to_dict() for item in self.test_cases],
            "coverage_gaps": [item.to_dict() for item in self.coverage_gaps],
            "risk_maps": [item.to_dict() for item in self.risk_maps],
        }
