"""Typed models for risk prioritization and execution queue contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PriorityLevel(str, Enum):
    """Priority bands for execution."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutionDepth(str, Enum):
    """Execution depth recommendation levels."""

    BASIC = "basic"
    STANDARD = "standard"
    DEEP = "deep"


class BlastRadius(str, Enum):
    """Blast radius hints for potential impact."""

    NARROW = "narrow"
    MEDIUM = "medium"
    WIDE = "wide"


@dataclass
class PriorityReason:
    """Auditable reason component contributing to prioritization score."""

    code: str
    description: str
    weight: float

    def to_dict(self) -> Dict[str, object]:
        """Convert reason to serializable form."""

        return {
            "code": self.code,
            "description": self.description,
            "weight": self.weight,
        }


@dataclass
class ExecutionDepthRecommendation:
    """Execution depth recommendation for a prioritized item."""

    depth: ExecutionDepth
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Convert recommendation to serializable form."""

        return {
            "depth": self.depth.value,
            "reasons": self.reasons,
        }


@dataclass
class BlastRadiusHint:
    """Estimated blast radius hint for a prioritized item."""

    level: BlastRadius
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Convert hint to serializable form."""

        return {
            "level": self.level.value,
            "reasons": self.reasons,
        }


@dataclass
class PrioritizedExecutionItem:
    """Execution-ready prioritized item produced by risk prioritization."""

    item_id: str
    source_type: str  # plan | test_case | coverage_gap
    source_id: str
    module: str
    submodule: Optional[str]
    priority_score: float
    priority_level: PriorityLevel
    execution_depth: ExecutionDepthRecommendation
    blast_radius: BlastRadiusHint
    reasons: List[PriorityReason] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    related_requirement_ids: List[str] = field(default_factory=list)
    exploratory_follow_up: bool = False

    def to_dict(self) -> Dict[str, object]:
        """Convert prioritized item to serializable form."""

        return {
            "id": self.item_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "module": self.module,
            "submodule": self.submodule,
            "priority_score": self.priority_score,
            "priority_level": self.priority_level.value,
            "execution_depth": self.execution_depth.depth.value,
            "blast_radius": self.blast_radius.level.value,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "tags": self.tags,
            "related_requirement_ids": self.related_requirement_ids,
            "exploratory_follow_up": self.exploratory_follow_up,
            "execution_depth_details": self.execution_depth.to_dict(),
            "blast_radius_details": self.blast_radius.to_dict(),
        }


@dataclass
class ExecutionQueue:
    """Deterministic execution queue contract for orchestrator consumption."""

    queue_id: str
    items: List[PrioritizedExecutionItem]
    ordering_policy: str

    def to_dict(self) -> Dict[str, object]:
        """Convert queue to serializable form."""

        return {
            "queue_id": self.queue_id,
            "ordering_policy": self.ordering_policy,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class PrioritizationResult:
    """Aggregate result for risk prioritization pipeline."""

    execution_queue: ExecutionQueue
    summary: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """Convert result to serializable form."""

        return {
            "execution_queue": self.execution_queue.to_dict(),
            "summary": self.summary,
        }
