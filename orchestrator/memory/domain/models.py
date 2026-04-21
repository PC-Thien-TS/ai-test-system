from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from orchestrator.storage.domain.models import FailureMemoryRecord


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryResolutionType(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    SIMILAR_MATCH = "SIMILAR_MATCH"
    NEW_MEMORY = "NEW_MEMORY"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"


@dataclass(slots=True)
class IncomingFailureRecord:
    adapter_id: str
    project_id: Optional[str]
    plugin: Optional[str]
    error_type: str
    endpoint: Optional[str]
    stack_trace: Optional[str]
    message: str
    severity_hint: str = "unknown"
    triage_root_cause: Optional[str] = None
    triage_confidence: float = 0.5
    recommended_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    component: Optional[str] = None
    fingerprint: Optional[str] = None


@dataclass(slots=True)
class FailureActionRecord:
    action_type: str
    strategy: str
    timestamp: datetime
    result: str
    notes: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "strategy": self.strategy,
            "timestamp": self.timestamp.isoformat(),
            "result": self.result,
            "notes": self.notes,
            "source": self.source,
        }


@dataclass(slots=True)
class ActionEffectiveness:
    action_type: str
    success_count: int = 0
    failure_count: int = 0
    effectiveness_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "effectiveness_score": self.effectiveness_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionEffectiveness":
        return cls(
            action_type=str(data.get("action_type") or ""),
            success_count=int(data.get("success_count") or 0),
            failure_count=int(data.get("failure_count") or 0),
            effectiveness_score=float(data.get("effectiveness_score") or 0.0),
        )


@dataclass(slots=True)
class MemoryResolutionResult:
    resolution_type: MemoryResolutionType
    resolved_memory_id: Optional[str]
    similarity: float
    confidence: float
    matched_record: Optional[FailureMemoryRecord]
    candidate_matches: list[dict[str, Any]]
    recommended_actions: list[str]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution_type": self.resolution_type.value,
            "resolved_memory_id": self.resolved_memory_id,
            "similarity": self.similarity,
            "confidence": self.confidence,
            "matched_record": self.matched_record.to_dict() if self.matched_record else None,
            "candidate_matches": self.candidate_matches,
            "recommended_actions": self.recommended_actions,
            "notes": self.notes,
        }


@dataclass(slots=True)
class MemoryEngineConfig:
    exact_match_enabled: bool = True
    semantic_match_enabled: bool = True
    similarity_threshold: float = 0.85
    auto_merge_threshold: float = 0.93
    ambiguous_threshold: float = 0.75
    confidence_boost_exact: float = 0.05
    confidence_boost_similar: float = 0.03
    confidence_decay_contradiction: float = 0.08
    confidence_min: float = 0.05
    confidence_max: float = 0.99
    ambiguous_gap_threshold: float = 0.03

    @classmethod
    def from_env(cls) -> "MemoryEngineConfig":
        def _as_bool(key: str, default: bool) -> bool:
            raw = os.getenv(key, str(default)).strip().lower()
            return raw in {"1", "true", "yes", "y", "on"}

        def _as_float(key: str, default: float) -> float:
            raw = os.getenv(key, "").strip()
            if not raw:
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        return cls(
            exact_match_enabled=_as_bool("MEMORY_EXACT_MATCH_ENABLED", True),
            semantic_match_enabled=_as_bool("MEMORY_SEMANTIC_MATCH_ENABLED", True),
            similarity_threshold=_as_float("MEMORY_SIMILARITY_THRESHOLD", 0.85),
            auto_merge_threshold=_as_float("MEMORY_AUTO_MERGE_THRESHOLD", 0.93),
            ambiguous_threshold=_as_float("MEMORY_AMBIGUOUS_THRESHOLD", 0.75),
            confidence_boost_exact=_as_float("MEMORY_CONFIDENCE_BOOST_EXACT", 0.05),
            confidence_boost_similar=_as_float("MEMORY_CONFIDENCE_BOOST_SIMILAR", 0.03),
            confidence_decay_contradiction=_as_float("MEMORY_CONFIDENCE_DECAY_CONTRADICTION", 0.08),
            confidence_min=_as_float("MEMORY_CONFIDENCE_MIN", 0.05),
            confidence_max=_as_float("MEMORY_CONFIDENCE_MAX", 0.99),
            ambiguous_gap_threshold=_as_float("MEMORY_AMBIGUOUS_GAP_THRESHOLD", 0.03),
        )
