from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


SEVERITY_RANK: Dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def max_severity(left: str, right: str) -> str:
    return left if SEVERITY_RANK.get(left, 0) >= SEVERITY_RANK.get(right, 0) else right


@dataclass(slots=True)
class FailureCase:
    nodeid: str
    outcome: str
    message: str
    longrepr: str = ""
    module_family: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FailureInference:
    category: str
    owner: str
    severity: str
    recommended_action: str
    message_pattern: str
    matched_rule: str


@dataclass(slots=True)
class FailureGroup:
    group_id: str
    category: str
    severity: str
    owner: str
    count: int
    examples: List[str]
    message_pattern: str
    module_family: str
    recommended_action: str
    signature: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FailureAnalysisSummary:
    total_failed: int
    total_groups: int
    highest_severity: str
    critical_group_count: int
    most_affected_area: str
    top_categories: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class FailureAnalysisReport:
    generated_at_utc: str
    source_report_path: str
    summary: FailureAnalysisSummary
    groups: List[FailureGroup]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

