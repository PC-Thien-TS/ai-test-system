from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DashboardQueryFilter:
    adapter_id: Optional[str] = None
    project_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    severity: Optional[str] = None
    candidate_type: Optional[str] = None
    owner: Optional[str] = None
    decision_type: Optional[str] = None


@dataclass
class TrendPoint:
    timestamp: str
    value: float
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeaderboardEntry:
    key: str
    label: str
    count: int
    severity: str = ""
    confidence: float = 0.0
    owner: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReleaseReadinessSummary:
    risk_level: str
    active_blockers: int
    active_incident_candidates: int
    escalation_count: int
    unresolved_actions: int
    release_penalty_total: int
    rationale: List[str] = field(default_factory=list)


@dataclass
class FailureMemoryDashboardSummary:
    top_root_causes: List[LeaderboardEntry]
    recurring_failure_count: int
    high_confidence_memory_count: int
    flaky_memory_count: int
    heatmap_data: List[LeaderboardEntry]


@dataclass
class DecisionDashboardSummary:
    decision_counts: Dict[str, int]
    block_release_count: int
    escalate_count: int
    suppress_count: int
    rerun_count: int
    manual_review_count: int
    rationale_buckets: Dict[str, int]


@dataclass
class StrategyEffectiveness:
    strategy: str
    success_count: int
    failure_count: int
    effectiveness_rate: float


@dataclass
class SelfHealingDashboardSummary:
    total_actions: int
    success_rate: float
    avg_attempts: float
    strategy_effectiveness: List[StrategyEffectiveness]
    recovery_rate: float
    top_failed_strategies: List[LeaderboardEntry]


@dataclass
class CandidateDashboardSummary:
    total_bug_candidates: int
    total_incident_candidates: int
    duplicate_suppression_count: int
    top_bug_candidates: List[LeaderboardEntry]
    top_incident_candidates: List[LeaderboardEntry]
    owner_distribution: Dict[str, int]


@dataclass
class GovernanceDashboardSummary:
    suppressed_candidate_count: int
    manual_review_count: int
    critical_path_guardrail_stops: int
    automation_stop_reasons: Dict[str, int]


@dataclass
class ExecutiveQASnapshot:
    headline_status: str
    release_readiness: ReleaseReadinessSummary
    top_risks: List[LeaderboardEntry]
    top_actions: List[str]
    strategic_notes: List[str]

