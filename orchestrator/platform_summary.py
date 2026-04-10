"""Platform summary generation for dashboard-ready views."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.compatibility import CompatibilityAnalyzer
from orchestrator.models import (
    GateResult,
    PlatformSummary,
    Project,
    ProjectSummary,
    Run,
    RunStatus,
)
from orchestrator.project_registry import ProjectRegistry
from orchestrator.run_registry import RunRegistry


class PlatformSummaryGenerator:
    """Generates platform-wide summaries for dashboard consumption."""

    def __init__(
        self,
        project_registry: ProjectRegistry,
        run_registry: RunRegistry,
        compatibility_analyzer: Optional[CompatibilityAnalyzer] = None,
    ):
        """
        Initialize the platform summary generator.
        
        Args:
            project_registry: The project registry instance.
            run_registry: The run registry instance.
            compatibility_analyzer: Optional compatibility analyzer.
        """
        self.project_registry = project_registry
        self.run_registry = run_registry
        self.compatibility_analyzer = compatibility_analyzer or CompatibilityAnalyzer()

    def generate_platform_summary(self) -> PlatformSummary:
        """
        Generate a platform-wide summary.
        
        Returns:
            PlatformSummary with aggregate statistics.
        """
        projects = self.project_registry.list_projects(active_only=True)
        all_runs = self.run_registry.list_runs(limit=10000)
        
        # Count active projects
        active_projects = len([p for p in projects if p.active])
        
        # Count failing projects (latest run failed or gate failed)
        failing_projects = 0
        flaky_projects = 0
        gate_overview = Counter()
        
        # Calculate execution depth metrics
        execution_depth_scores = []
        evidence_richness_scores = []
        confidence_scores = []
        fallback_ratios = []
        real_execution_ratios = []
        
        for project in projects:
            latest_run = self.run_registry.get_latest_run(project.project_id)
            if latest_run:
                if latest_run.status == RunStatus.FAILED:
                    failing_projects += 1
                if latest_run.flaky:
                    flaky_projects += 1
                if latest_run.gate_result:
                    gate_overview[latest_run.gate_result] += 1
                
                # Collect execution depth metrics
                fallback_ratios.append(latest_run.fallback_ratio)
                real_execution_ratios.append(latest_run.real_execution_ratio)
        
        # Calculate plugin maturity trend
        plugin_maturity_trend = {}
        for plugin_name, plugin in self.compatibility_analyzer._plugins.items():
            # Maturity score is a composite of execution_depth, evidence_richness, and confidence
            maturity_score = (plugin.execution_depth_score * 0.4 + 
                            plugin.evidence_richness_score * 0.3 + 
                            plugin.confidence_score * 0.3)
            plugin_maturity_trend[plugin_name] = maturity_score
        
        # Calculate platform averages
        avg_execution_depth_score = sum(plugin_maturity_trend.values()) / len(plugin_maturity_trend) if plugin_maturity_trend else 0.0
        avg_evidence_richness_score = sum(p.evidence_richness_score for p in self.compatibility_analyzer._plugins.values()) / len(self.compatibility_analyzer._plugins) if self.compatibility_analyzer._plugins else 0.0
        avg_confidence_score = sum(p.confidence_score for p in self.compatibility_analyzer._plugins.values()) / len(self.compatibility_analyzer._plugins) if self.compatibility_analyzer._plugins else 0.0
        avg_fallback_ratio = sum(fallback_ratios) / len(fallback_ratios) if fallback_ratios else 0.0
        avg_real_execution_ratio = sum(real_execution_ratios) / len(real_execution_ratios) if real_execution_ratios else 0.0
        
        # Count plugin usage
        plugin_usage = Counter()
        for project in projects:
            for tag in project.tags:
                if tag in self.compatibility_analyzer._plugins:
                    plugin_usage[tag] += 1
        
        return PlatformSummary(
            total_projects=len(projects),
            active_projects=active_projects,
            total_runs=len(all_runs),
            failing_projects=failing_projects,
            flaky_projects=flaky_projects,
            gate_overview=dict(gate_overview),
            plugin_usage=dict(plugin_usage),
            generated_at=datetime.utcnow(),
            avg_execution_depth_score=avg_execution_depth_score,
            avg_evidence_richness_score=avg_evidence_richness_score,
            avg_confidence_score=avg_confidence_score,
            avg_fallback_ratio=avg_fallback_ratio,
            avg_real_execution_ratio=avg_real_execution_ratio,
            plugin_maturity_trend=plugin_maturity_trend,
        )

    def generate_project_summary(self, project_id: str) -> Optional[ProjectSummary]:
        """
        Generate a summary for a specific project.
        
        Args:
            project_id: The project ID.
            
        Returns:
            ProjectSummary if project found, None otherwise.
        """
        project = self.project_registry.get_project(project_id)
        if not project:
            return None
        
        runs = self.run_registry.list_runs_by_project(project_id, limit=1000)
        
        latest_run = self.run_registry.get_latest_run(project_id)
        
        passed_runs = len([r for r in runs if r.status == RunStatus.COMPLETED and r.gate_result == GateResult.PASS])
        failed_runs = len([r for r in runs if r.status == RunStatus.FAILED or (r.gate_result == GateResult.FAIL)])
        flaky_runs = len([r for r in runs if r.flaky])
        
        # Calculate execution depth metrics from runs
        fallback_ratios = [r.fallback_ratio for r in runs]
        real_execution_ratios = [r.real_execution_ratio for r in runs]
        
        # Get plugin execution depth scores from project tags
        execution_depth_scores = []
        evidence_richness_scores = []
        confidence_scores = []
        
        for tag in project.tags:
            plugin = self.compatibility_analyzer.get_plugin(tag)
            if plugin:
                execution_depth_scores.append(plugin.execution_depth_score)
                evidence_richness_scores.append(plugin.evidence_richness_score)
                confidence_scores.append(plugin.confidence_score)
        
        # Calculate averages
        avg_execution_depth_score = sum(execution_depth_scores) / len(execution_depth_scores) if execution_depth_scores else 0.0
        avg_evidence_richness_score = sum(evidence_richness_scores) / len(evidence_richness_scores) if evidence_richness_scores else 0.0
        avg_confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        avg_fallback_ratio = sum(fallback_ratios) / len(fallback_ratios) if fallback_ratios else 0.0
        avg_real_execution_ratio = sum(real_execution_ratios) / len(real_execution_ratios) if real_execution_ratios else 0.0
        
        last_updated = None
        if latest_run and latest_run.completed_at:
            last_updated = latest_run.completed_at
        elif latest_run:
            last_updated = latest_run.started_at
        
        return ProjectSummary(
            project_id=project.project_id,
            project_name=project.name,
            product_type=project.product_type,
            latest_run_id=latest_run.run_id if latest_run else None,
            latest_status=latest_run.status if latest_run else None,
            gate_result=latest_run.gate_result if latest_run else None,
            total_runs=len(runs),
            passed_runs=passed_runs,
            failed_runs=failed_runs,
            flaky_runs=flaky_runs,
            last_updated=last_updated,
            avg_execution_depth_score=avg_execution_depth_score,
            avg_evidence_richness_score=avg_evidence_richness_score,
            avg_confidence_score=avg_confidence_score,
            avg_fallback_ratio=avg_fallback_ratio,
            avg_real_execution_ratio=avg_real_execution_ratio,
        )

    def generate_all_project_summaries(self) -> List[ProjectSummary]:
        """
        Generate summaries for all active projects.
        
        Returns:
            List of ProjectSummary for all active projects.
        """
        projects = self.project_registry.list_projects(active_only=True)
        summaries = []
        
        for project in projects:
            summary = self.generate_project_summary(project.project_id)
            if summary:
                summaries.append(summary)
        
        return summaries

    def get_latest_project_status(self) -> List[Dict]:
        """
        Get the latest status for all projects.
        
        Returns:
            List of dictionaries with project ID, name, and latest status.
        """
        summaries = self.generate_all_project_summaries()
        
        return [
            {
                "project_id": s.project_id,
                "project_name": s.project_name,
                "product_type": s.product_type.value,
                "latest_run_id": s.latest_run_id,
                "latest_status": s.latest_status.value if s.latest_status else None,
                "gate_result": s.gate_result.value if s.gate_result else None,
                "last_updated": s.last_updated.isoformat() if s.last_updated else None,
            }
            for s in summaries
        ]

    def generate_trend_data(
        self,
        project_id: str,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Generate trend data for a project.
        
        Args:
            project_id: The project ID.
            limit: Maximum number of runs to include.
            
        Returns:
            List of trend data points.
        """
        runs = self.run_registry.list_runs_by_project(project_id, limit=limit)
        
        trend_data = []
        for run in runs:
            trend_data.append({
                "run_id": run.run_id,
                "timestamp": run.started_at.isoformat(),
                "status": run.status.value,
                "gate_result": run.gate_result.value if run.gate_result else None,
                "flaky": run.flaky,
                "duration": (
                    (run.completed_at - run.started_at).total_seconds()
                    if run.completed_at
                    else None
                ),
            })
        
        return trend_data

    def get_flaky_projects(self) -> List[ProjectSummary]:
        """
        Get projects with flaky test runs.
        
        Returns:
            List of ProjectSummary for flaky projects.
        """
        summaries = self.generate_all_project_summaries()
        return [s for s in summaries if s.flaky_runs > 0]

    def get_failing_projects(self) -> List[ProjectSummary]:
        """
        Get projects with failing test runs.
        
        Returns:
            List of ProjectSummary for failing projects.
        """
        summaries = self.generate_all_project_summaries()
        return [s for s in summaries if s.failed_runs > 0 or (s.latest_status == RunStatus.FAILED)]
