"""Requirement-aware generation package for advanced QA capabilities."""

from orchestrator.advanced_qa.requirement_generator import RequirementAwareGenerator
from orchestrator.advanced_qa.requirement_models import (
    CoverageGapCandidate,
    GeneratedTestCase,
    GeneratedTestPlan,
    PlanBucket,
    Requirement,
    RequirementGenerationResult,
    RequirementRiskMap,
    RequirementSourceType,
    RiskLevel,
)
from orchestrator.advanced_qa.requirement_parser import RequirementParser
from orchestrator.advanced_qa.requirement_mapper import RequirementMapper
from orchestrator.advanced_qa.requirement_outputs import RequirementOutputBuilder
from orchestrator.advanced_qa.risk_models import (
    BlastRadius,
    BlastRadiusHint,
    ExecutionDepth,
    ExecutionDepthRecommendation,
    ExecutionQueue,
    PrioritizedExecutionItem,
    PrioritizationResult,
    PriorityLevel,
    PriorityReason,
)
from orchestrator.advanced_qa.risk_prioritizer import RiskPrioritizer

__all__ = [
    "RequirementAwareGenerator",
    "RequirementParser",
    "RequirementMapper",
    "RequirementOutputBuilder",
    "Requirement",
    "GeneratedTestPlan",
    "GeneratedTestCase",
    "CoverageGapCandidate",
    "RequirementRiskMap",
    "RequirementGenerationResult",
    "RequirementSourceType",
    "PlanBucket",
    "RiskLevel",
    "RiskPrioritizer",
    "PriorityReason",
    "ExecutionDepthRecommendation",
    "BlastRadiusHint",
    "PrioritizedExecutionItem",
    "ExecutionQueue",
    "PrioritizationResult",
    "PriorityLevel",
    "ExecutionDepth",
    "BlastRadius",
]
