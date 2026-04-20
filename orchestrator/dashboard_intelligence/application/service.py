from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from ..domain.aggregations import (
    aggregate_candidate_summary,
    aggregate_decision_summary,
    aggregate_failure_memory_summary,
    aggregate_governance_summary,
    aggregate_release_readiness,
    aggregate_self_healing_summary,
    aggregate_top_recurring_failures,
)
from ..domain.models import (
    CandidateDashboardSummary,
    DashboardQueryFilter,
    DecisionDashboardSummary,
    ExecutiveQASnapshot,
    FailureMemoryDashboardSummary,
    GovernanceDashboardSummary,
    LeaderboardEntry,
    ReleaseReadinessSummary,
    SelfHealingDashboardSummary,
    TrendPoint,
)
from ..domain.trend_utils import bucket_daily, build_trend_points, trend_direction, window_compare
from ..infrastructure.query_repository import DashboardQueryRepository


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class DashboardIntelligenceService:
    def __init__(
        self,
        query_repository: DashboardQueryRepository,
        *,
        intelligence_enabled: Optional[bool] = None,
        trend_window_days: Optional[int] = None,
        executive_top_risks_limit: Optional[int] = None,
        leaderboard_limit: Optional[int] = None,
    ) -> None:
        self.repo = query_repository
        self.intelligence_enabled = _env_bool("DASHBOARD_INTELLIGENCE_ENABLED", True) if intelligence_enabled is None else intelligence_enabled
        self.trend_window_days = _env_int("DASHBOARD_TREND_WINDOW_DAYS", 7) if trend_window_days is None else trend_window_days
        self.executive_top_risks_limit = _env_int("DASHBOARD_EXECUTIVE_TOP_RISKS_LIMIT", 5) if executive_top_risks_limit is None else executive_top_risks_limit
        self.leaderboard_limit = _env_int("DASHBOARD_LEADERBOARD_LIMIT", 10) if leaderboard_limit is None else leaderboard_limit

    def _ensure_enabled(self) -> None:
        if not self.intelligence_enabled:
            raise RuntimeError("Dashboard intelligence is disabled by configuration.")

    def get_release_readiness_summary(self, q: DashboardQueryFilter) -> ReleaseReadinessSummary:
        self._ensure_enabled()
        return aggregate_release_readiness(
            decision_records=self.repo.decision_records(q),
            incident_records=self.repo.incident_candidate_records(q),
            self_healing_records=self.repo.self_healing_records(q),
            release_records=self.repo.release_records(q),
        )

    def get_failure_memory_summary(self, q: DashboardQueryFilter) -> FailureMemoryDashboardSummary:
        self._ensure_enabled()
        return aggregate_failure_memory_summary(
            self.repo.memory_records(q),
            limit=self.leaderboard_limit,
        )

    def get_decision_summary(self, q: DashboardQueryFilter) -> DecisionDashboardSummary:
        self._ensure_enabled()
        return aggregate_decision_summary(self.repo.decision_records(q))

    def get_self_healing_summary(self, q: DashboardQueryFilter) -> SelfHealingDashboardSummary:
        self._ensure_enabled()
        return aggregate_self_healing_summary(
            self.repo.self_healing_records(q),
            limit=self.leaderboard_limit,
        )

    def get_candidate_summary(self, q: DashboardQueryFilter) -> CandidateDashboardSummary:
        self._ensure_enabled()
        return aggregate_candidate_summary(
            self.repo.bug_candidate_records(q),
            self.repo.incident_candidate_records(q),
            self.repo.candidate_suppression_records(q),
            limit=self.leaderboard_limit,
        )

    def get_governance_summary(self, q: DashboardQueryFilter) -> GovernanceDashboardSummary:
        self._ensure_enabled()
        return aggregate_governance_summary(
            self.repo.candidate_suppression_records(q),
            self.repo.decision_records(q),
            self.repo.self_healing_records(q),
        )

    def get_top_recurring_failures(self, q: DashboardQueryFilter, *, limit: Optional[int] = None) -> List[LeaderboardEntry]:
        self._ensure_enabled()
        return aggregate_top_recurring_failures(
            self.repo.memory_records(q),
            limit=limit or self.leaderboard_limit,
        )

    def get_top_bug_candidates(self, q: DashboardQueryFilter, *, limit: Optional[int] = None) -> List[LeaderboardEntry]:
        self._ensure_enabled()
        summary = self.get_candidate_summary(q)
        return summary.top_bug_candidates[: limit or self.leaderboard_limit]

    def get_top_incident_candidates(self, q: DashboardQueryFilter, *, limit: Optional[int] = None) -> List[LeaderboardEntry]:
        self._ensure_enabled()
        summary = self.get_candidate_summary(q)
        return summary.top_incident_candidates[: limit or self.leaderboard_limit]

    def get_trend_series(
        self,
        q: DashboardQueryFilter,
        *,
        metric: str,
        window_days: Optional[int] = None,
    ) -> Dict[str, object]:
        self._ensure_enabled()
        metric_lower = metric.lower()
        days = window_days or self.trend_window_days
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        trend_filter = DashboardQueryFilter(
            adapter_id=q.adapter_id,
            project_id=q.project_id,
            start_date=start if q.start_date is None else q.start_date,
            end_date=q.end_date,
            severity=q.severity,
            candidate_type=q.candidate_type,
            owner=q.owner,
            decision_type=q.decision_type,
        )

        records: List[Dict[str, object]]
        if metric_lower in {"decision_block_release", "block_release"}:
            records = [r for r in self.repo.decision_records(trend_filter) if str(r.get("primary_decision", "")).upper() == "BLOCK_RELEASE"]
        elif metric_lower in {"decision_escalate", "escalate"}:
            records = [r for r in self.repo.decision_records(trend_filter) if str(r.get("primary_decision", "")).upper() in {"ESCALATE", "BLOCK_RELEASE"}]
        elif metric_lower in {"candidate_bug", "bug_candidates"}:
            records = self.repo.bug_candidate_records(trend_filter)
        elif metric_lower in {"candidate_incident", "incident_candidates"}:
            records = self.repo.incident_candidate_records(trend_filter)
        elif metric_lower in {"suppression", "candidate_suppression"}:
            records = self.repo.candidate_suppression_records(trend_filter)
        elif metric_lower in {"rerun", "decision_rerun"}:
            records = [
                r
                for r in self.repo.decision_records(trend_filter)
                if str(r.get("primary_decision", "")).upper() in {"RERUN", "RERUN_WITH_STRATEGY"}
            ]
        else:
            records = self.repo.decision_records(trend_filter)

        daily = bucket_daily(records)
        points = build_trend_points(daily, label_prefix=f"{metric_lower}:")
        compare = window_compare(records, now=now, window_days=days)
        return {
            "metric": metric_lower,
            "window_days": days,
            "direction": trend_direction(points),
            "points": [asdict(p) for p in points],
            "window_compare": compare,
        }

    def get_executive_snapshot(self, q: DashboardQueryFilter) -> ExecutiveQASnapshot:
        self._ensure_enabled()
        readiness = self.get_release_readiness_summary(q)
        top_recurring = self.get_top_recurring_failures(q, limit=self.executive_top_risks_limit)
        top_incidents = self.get_top_incident_candidates(q, limit=self.executive_top_risks_limit)

        top_risks = (top_incidents + top_recurring)[: self.executive_top_risks_limit]
        top_actions: List[str] = []
        if readiness.active_blockers > 0:
            top_actions.append("Resolve active release-blocking failures before promotion.")
        if readiness.active_incident_candidates > 0:
            top_actions.append("Triage unresolved incident candidates and assign owners.")
        if readiness.unresolved_actions > 0:
            top_actions.append("Investigate unresolved self-healing failures and tune strategies.")
        if not top_actions:
            top_actions.append("Continue monitoring trend stability and policy distributions.")

        headline = "healthy"
        if readiness.risk_level == "high":
            headline = "at_risk"
        elif readiness.risk_level == "medium":
            headline = "watch"

        notes = [
            f"Risk level: {readiness.risk_level}",
            f"Active blockers: {readiness.active_blockers}",
            f"Incident candidates: {readiness.active_incident_candidates}",
            f"Escalations: {readiness.escalation_count}",
        ]

        return ExecutiveQASnapshot(
            headline_status=headline,
            release_readiness=readiness,
            top_risks=top_risks,
            top_actions=top_actions,
            strategic_notes=notes,
        )

