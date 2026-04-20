from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FailureCase:
    nodeid: str
    outcome: str
    message: str
    module_path: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureInference:
    category: str
    owner: str
    severity: str
    recommended_action: str
    area: str


@dataclass
class FailureGroup:
    group_id: str
    category: str
    severity: str
    owner: str
    count: int
    examples: List[str]
    message_pattern: str
    recommended_action: str
    signature: str
    most_affected_area: str
    sample_message: str


@dataclass
class FailureAnalysisSummary:
    total_failed: int
    total_groups: int
    highest_severity: str
    critical_group_count: int
    most_affected_area: str
    generated_at_utc: str = field(default_factory=utc_now_iso)


@dataclass
class FailureAnalysisReport:
    summary: FailureAnalysisSummary
    groups: List[FailureGroup]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

