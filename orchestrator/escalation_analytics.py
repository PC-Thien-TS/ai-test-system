"""Advanced escalation analytics for cross-project patterns and trends."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum


class TrendDirection(Enum):
    """Direction of a trend."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


@dataclass
class CrossProjectPattern:
    """Pattern observed across multiple projects."""
    pattern_id: str
    pattern_type: str
    affected_projects: List[str]
    frequency: int
    description: str
    severity: str
    
    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "affected_projects": self.affected_projects,
            "frequency": self.frequency,
            "description": self.description,
            "severity": self.severity,
        }


@dataclass
class FailureMode:
    """Common failure mode analysis."""
    mode_name: str
    occurrence_count: int
    total_runs: int
    percentage: float
    avg_escalation_depth: float
    time_to_stable_avg: Optional[float]
    
    def to_dict(self) -> dict:
        return {
            "mode_name": self.mode_name,
            "occurrence_count": self.occurrence_count,
            "total_runs": self.total_runs,
            "percentage": self.percentage,
            "avg_escalation_depth": self.avg_escalation_depth,
            "time_to_stable_avg": self.time_to_stable_avg,
        }


@dataclass
class TimeToStableTrend:
    """Time-to-stable analysis trend."""
    period: str
    avg_time_to_stable: float
    trend_direction: TrendDirection
    projects_analyzed: int
    
    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "avg_time_to_stable": self.avg_time_to_stable,
            "trend_direction": self.trend_direction.value,
            "projects_analyzed": self.projects_analyzed,
        }


@dataclass
class EscalationAnalyticsSummary:
    """Summary of escalation analytics."""
    total_runs: int
    total_escalations: int
    escalation_rate: float
    cross_project_patterns: List[CrossProjectPattern]
    top_failure_modes: List[FailureMode]
    time_to_stable_trends: List[TimeToStableTrend]
    
    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "total_escalations": self.total_escalations,
            "escalation_rate": self.escalation_rate,
            "cross_project_patterns": [p.to_dict() for p in self.cross_project_patterns],
            "top_failure_modes": [f.to_dict() for f in self.top_failure_modes],
            "time_to_stable_trends": [t.to_dict() for t in self.time_to_stable_trends],
        }


class EscalationAnalytics:
    """Analytics engine for escalation patterns and trends."""

    def analyze_cross_project_patterns(
        self,
        project_runs: Dict[str, List[dict]],
    ) -> List[CrossProjectPattern]:
        """
        Analyze escalation patterns across multiple projects.

        Args:
            project_runs: Dictionary mapping project IDs to their run data.

        Returns:
            List of cross-project patterns detected.
        """
        patterns = []

        # Analyze common escalation reasons
        escalation_reasons = defaultdict(list)
        for project_id, runs in project_runs.items():
            for run in runs:
                reason = run.get("metadata", {}).get("escalation_reason", "unknown")
                if reason != "unknown":
                    escalation_reasons[reason].append(project_id)

        for reason, projects in escalation_reasons.items():
            if len(set(projects)) >= 2:  # At least 2 projects
                patterns.append(CrossProjectPattern(
                    pattern_id=f"reason_{hash(reason)}",
                    pattern_type="escalation_reason",
                    affected_projects=list(set(projects)),
                    frequency=len(projects),
                    description=f"Common escalation reason: {reason}",
                    severity=self._determine_reason_severity(reason),
                ))

        # Analyze execution path escalation patterns
        path_transitions = defaultdict(list)
        for project_id, runs in project_runs.items():
            for run in runs:
                from_path = run.get("metadata", {}).get("escalation_from")
                to_path = run.get("metadata", {}).get("escalation_to")
                if from_path and to_path:
                    transition = f"{from_path} -> {to_path}"
                    path_transitions[transition].append(project_id)

        for transition, projects in path_transitions.items():
            if len(set(projects)) >= 2:
                patterns.append(CrossProjectPattern(
                    pattern_id=f"path_{hash(transition)}",
                    pattern_type="path_transition",
                    affected_projects=list(set(projects)),
                    frequency=len(projects),
                    description=f"Common path transition: {transition}",
                    severity="medium",
                ))

        # Analyze plugin-specific patterns
        plugin_failures = defaultdict(list)
        for project_id, runs in project_runs.items():
            for run in runs:
                plugin = run.get("metadata", {}).get("failed_plugin")
                if plugin:
                    plugin_failures[plugin].append(project_id)

        for plugin, projects in plugin_failures.items():
            if len(set(projects)) >= 2:
                patterns.append(CrossProjectPattern(
                    pattern_id=f"plugin_{hash(plugin)}",
                    pattern_type="plugin_failure",
                    affected_projects=list(set(projects)),
                    frequency=len(projects),
                    description=f"Common plugin failure: {plugin}",
                    severity="high",
                ))

        return patterns

    def analyze_failure_modes(
        self,
        runs: List[dict],
    ) -> List[FailureMode]:
        """
        Analyze common failure modes across runs.

        Args:
            runs: List of run data.

        Returns:
            List of failure modes ranked by occurrence.
        """
        failure_modes = defaultdict(lambda: {
            "count": 0,
            "escalation_depths": [],
            "time_to_stable": [],
        })

        for run in runs:
            gate_result = run.get("gate_result")
            if gate_result == "fail":
                # Determine failure mode from metadata
                failure_type = run.get("metadata", {}).get("failure_type", "unknown")
                failure_modes[failure_type]["count"] += 1
                failure_modes[failure_type]["escalation_depths"].append(
                    run.get("metadata", {}).get("escalation_depth", 0)
                )
                
                # Calculate time to stable if available
                if run.get("completed_at") and run.get("started_at"):
                    duration = (
                        datetime.fromisoformat(run["completed_at"]) - 
                        datetime.fromisoformat(run["started_at"])
                    ).total_seconds()
                    failure_modes[failure_type]["time_to_stable"].append(duration)

        total_runs = len(runs)
        modes = []

        for mode_name, data in failure_modes.items():
            avg_depth = sum(data["escalation_depths"]) / len(data["escalation_depths"]) if data["escalation_depths"] else 0
            avg_time = sum(data["time_to_stable"]) / len(data["time_to_stable"]) if data["time_to_stable"] else None

            modes.append(FailureMode(
                mode_name=mode_name,
                occurrence_count=data["count"],
                total_runs=total_runs,
                percentage=(data["count"] / total_runs) * 100 if total_runs > 0 else 0,
                avg_escalation_depth=avg_depth,
                time_to_stable_avg=avg_time,
            ))

        # Sort by occurrence count
        modes.sort(key=lambda m: m.occurrence_count, reverse=True)
        return modes[:10]  # Return top 10

    def analyze_time_to_stable_trends(
        self,
        runs: List[dict],
        period_days: int = 30,
    ) -> List[TimeToStableTrend]:
        """
        Analyze time-to-stable trends over time periods.

        Args:
            runs: List of run data.
            period_days: Number of days per period for trend analysis.

        Returns:
            List of time-to-stable trends by period.
        """
        if not runs:
            return []

        # Sort runs by start time
        sorted_runs = sorted(
            [r for r in runs if r.get("started_at") and r.get("completed_at")],
            key=lambda r: r["started_at"]
        )

        if not sorted_runs:
            return []

        start_date = datetime.fromisoformat(sorted_runs[0]["started_at"])
        end_date = datetime.fromisoformat(sorted_runs[-1]["started_at"])

        trends = []
        current_period_start = start_date

        while current_period_start < end_date:
            current_period_end = current_period_start + timedelta(days=period_days)
            
            # Get runs in this period
            period_runs = [
                r for r in sorted_runs
                if current_period_start <= datetime.fromisoformat(r["started_at"]) < current_period_end
            ]

            if period_runs:
                # Calculate average time to stable (completion time)
                times = []
                for run in period_runs:
                    duration = (
                        datetime.fromisoformat(run["completed_at"]) - 
                        datetime.fromisoformat(run["started_at"])
                    ).total_seconds()
                    times.append(duration)

                avg_time = sum(times) / len(times) if times else 0

                # Determine trend direction
                if trends:
                    prev_avg = trends[-1].avg_time_to_stable
                    if avg_time > prev_avg * 1.1:
                        direction = TrendDirection.INCREASING
                    elif avg_time < prev_avg * 0.9:
                        direction = TrendDirection.DECREASING
                    else:
                        direction = TrendDirection.STABLE
                else:
                    direction = TrendDirection.STABLE

                trends.append(TimeToStableTrend(
                    period=f"{current_period_start.strftime('%Y-%m-%d')} to {current_period_end.strftime('%Y-%m-%d')}",
                    avg_time_to_stable=avg_time,
                    trend_direction=direction,
                    projects_analyzed=len(set(r.get("project_id") for r in period_runs)),
                ))

            current_period_start = current_period_end

        return trends

    def generate_analytics_summary(
        self,
        project_runs: Dict[str, List[dict]],
    ) -> EscalationAnalyticsSummary:
        """
        Generate a comprehensive analytics summary.

        Args:
            project_runs: Dictionary mapping project IDs to their run data.

        Returns:
            Comprehensive analytics summary.
        """
        # Flatten all runs
        all_runs = []
        for runs in project_runs.values():
            all_runs.extend(runs)

        total_runs = len(all_runs)
        total_escalations = sum(
            1 for run in all_runs
            if run.get("parent_run_id") or run.get("metadata", {}).get("escalation_from")
        )
        escalation_rate = (total_escalations / total_runs) if total_runs > 0 else 0

        cross_project_patterns = self.analyze_cross_project_patterns(project_runs)
        top_failure_modes = self.analyze_failure_modes(all_runs)
        time_to_stable_trends = self.analyze_time_to_stable_trends(all_runs)

        return EscalationAnalyticsSummary(
            total_runs=total_runs,
            total_escalations=total_escalations,
            escalation_rate=escalation_rate,
            cross_project_patterns=cross_project_patterns,
            top_failure_modes=top_failure_modes,
            time_to_stable_trends=time_to_stable_trends,
        )

    def _determine_reason_severity(self, reason: str) -> str:
        """Determine severity level for an escalation reason."""
        reason_lower = reason.lower()
        
        if any(keyword in reason_lower for keyword in ["critical", "error", "failure", "timeout"]):
            return "critical"
        elif any(keyword in reason_lower for keyword in ["high", "low confidence", "fallback"]):
            return "high"
        elif any(keyword in reason_lower for keyword in ["flaky", "inconsistent"]):
            return "medium"
        else:
            return "low"

    def get_project_health_score(
        self,
        project_runs: List[dict],
    ) -> Dict[str, any]:
        """
        Calculate a health score for a project based on escalation patterns.

        Args:
            project_runs: List of run data for a project.

        Returns:
            Dictionary with health score and contributing factors.
        """
        if not project_runs:
            return {
                "health_score": 0.5,
                "factors": {
                    "escalation_rate": 0,
                    "avg_escalation_depth": 0,
                    "flaky_rate": 0,
                    "time_to_stable": 0,
                },
            }

        total_runs = len(project_runs)
        escalated_runs = [r for r in project_runs if r.get("parent_run_id")]
        flaky_runs = [r for r in project_runs if r.get("flaky", False)]

        escalation_rate = len(escalated_runs) / total_runs if total_runs > 0 else 0
        flaky_rate = len(flaky_runs) / total_runs if total_runs > 0 else 0

        avg_escalation_depth = 0
        if escalated_runs:
            depths = [r.get("metadata", {}).get("escalation_depth", 0) for r in escalated_runs]
            avg_escalation_depth = sum(depths) / len(depths)

        # Calculate average time to completion
        avg_time = 0
        completed_runs = [r for r in project_runs if r.get("completed_at") and r.get("started_at")]
        if completed_runs:
            times = []
            for run in completed_runs:
                duration = (
                    datetime.fromisoformat(run["completed_at"]) - 
                    datetime.fromisoformat(run["started_at"])
                ).total_seconds()
                times.append(duration)
            avg_time = sum(times) / len(times)

        # Normalize factors to 0-1 scale
        escalation_factor = max(0, 1 - escalation_rate * 2)  # Lower escalation is better
        depth_factor = max(0, 1 - avg_escalation_depth / 5)  # Lower depth is better
        flaky_factor = max(0, 1 - flaky_rate * 2)  # Lower flaky is better
        time_factor = max(0, 1 - min(avg_time / 3600, 1))  # Lower time is better (1 hour max)

        # Calculate weighted health score
        health_score = (
            escalation_factor * 0.4 +
            depth_factor * 0.2 +
            flaky_factor * 0.2 +
            time_factor * 0.2
        )

        return {
            "health_score": health_score,
            "factors": {
                "escalation_rate": escalation_factor,
                "avg_escalation_depth": depth_factor,
                "flaky_rate": flaky_factor,
                "time_to_stable": time_factor,
            },
            "metrics": {
                "escalation_rate": escalation_rate,
                "avg_escalation_depth": avg_escalation_depth,
                "flaky_rate": flaky_rate,
                "avg_time_to_stable": avg_time,
            },
        }
