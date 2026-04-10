"""Execution Intelligence Engine for v2.5.0.

This module provides intelligent execution path selection based on:
- Plugin execution depth scores
- Support levels
- Historical run performance
- Fallback escalation logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from orchestrator.compatibility import CompatibilityAnalyzer
from orchestrator.models import ProductType, Run, RunStatus, SupportLevel


class ExecutionPath(Enum):
    """Execution path types."""
    SMOKE = "smoke"  # Fast, shallow validation
    STANDARD = "standard"  # Normal validation
    DEEP = "deep"  # Full validation with negative paths
    INTELLIGENT = "intelligent"  # Adaptive based on context


@dataclass
class ExecutionStrategy:
    """Execution strategy for a run."""
    path: ExecutionPath
    reason: str
    confidence_threshold: float
    fallback_threshold: float
    enable_negative_paths: bool
    enable_retry_rollback: bool
    enable_anomaly_detection: bool
    estimated_duration_multiplier: float  # Multiplier relative to standard


@dataclass
class EscalationReason:
    """Reason for execution path escalation."""
    timestamp: datetime
    from_path: ExecutionPath
    to_path: ExecutionPath
    reason: str
    metrics_snapshot: Dict[str, float]


class ExecutionIntelligenceEngine:
    """Intelligent execution engine for adaptive validation."""

    def __init__(
        self,
        compatibility_analyzer: Optional[CompatibilityAnalyzer] = None,
    ):
        """
        Initialize the execution intelligence engine.

        Args:
            compatibility_analyzer: Optional compatibility analyzer.
        """
        self.compatibility_analyzer = compatibility_analyzer or CompatibilityAnalyzer()
        self._escalation_history: List[EscalationReason] = []

    def choose_execution_path(
        self,
        project_id: str,
        product_type: ProductType,
        plugin_names: List[str],
        historical_runs: List[Run],
        force_path: Optional[ExecutionPath] = None,
    ) -> ExecutionStrategy:
        """
        Choose the optimal execution path based on context.

        Args:
            project_id: The project ID.
            product_type: The product type.
            plugin_names: List of plugin names to use.
            historical_runs: Historical run data for the project.
            force_path: Optional forced execution path.

        Returns:
            ExecutionStrategy with chosen path and configuration.
        """
        if force_path:
            return self._create_strategy(
                force_path,
                reason="Forced by user configuration",
                confidence_threshold=0.5,
                fallback_threshold=0.3,
            )

        # Calculate project health score
        health_score = self._calculate_project_health(historical_runs)

        # Calculate plugin aggregate depth
        avg_depth_score = self._calculate_plugin_depth_score(plugin_names)

        # Determine path based on health and depth
        if health_score < 0.5 and avg_depth_score < 0.6:
            # Project is unhealthy and plugins have low depth - start with smoke
            return self._create_strategy(
                ExecutionPath.SMOKE,
                reason="Low project health and plugin depth - starting with smoke validation",
                confidence_threshold=0.3,
                fallback_threshold=0.2,
            )
        elif health_score < 0.7:
            # Project is somewhat unhealthy - use standard
            return self._create_strategy(
                ExecutionPath.STANDARD,
                reason="Moderate project health - using standard validation",
                confidence_threshold=0.5,
                fallback_threshold=0.3,
            )
        elif avg_depth_score >= 0.8:
            # High depth plugins available - use deep validation
            return self._create_strategy(
                ExecutionPath.DEEP,
                reason=f"High plugin depth ({avg_depth_score:.2f}) - using deep validation",
                confidence_threshold=0.7,
                fallback_threshold=0.1,
                enable_negative_paths=True,
                enable_retry_rollback=True,
                enable_anomaly_detection=True,
                estimated_duration_multiplier=2.5,
            )
        else:
            # Default to intelligent adaptive path
            return self._create_strategy(
                ExecutionPath.INTELLIGENT,
                reason="Adaptive path based on plugin capabilities",
                confidence_threshold=0.6,
                fallback_threshold=0.2,
                enable_anomaly_detection=True,
                estimated_duration_multiplier=1.5,
            )

    def should_escalate_path(
        self,
        current_path: ExecutionPath,
        run: Run,
        plugin_names: List[str],
    ) -> Optional[ExecutionPath]:
        """
        Determine if execution path should be escalated based on run results.

        Args:
            current_path: Current execution path.
            run: The current run.
            plugin_names: List of plugin names used.

        Returns:
            New execution path if escalation is needed, None otherwise.
        """
        escalation_reason = None

        # Check for excessive fallback usage
        if run.fallback_ratio > 0.5:
            escalation_reason = (
                f"High fallback ratio ({run.fallback_ratio:.2f}) - escalating to deep validation"
            )
            escalation = self._record_escalation(
                current_path,
                ExecutionPath.DEEP,
                escalation_reason,
                {"fallback_ratio": run.fallback_ratio},
            )
            # Persist escalation reason in run metadata
            run.metadata["escalation_reason"] = escalation_reason
            run.metadata["escalation_from"] = current_path.value
            run.metadata["escalation_to"] = ExecutionPath.DEEP.value
            return escalation

        # Check for low real execution
        if run.real_execution_ratio < 0.3:
            escalation_reason = (
                f"Low real execution ratio ({run.real_execution_ratio:.2f}) - escalating to deep validation"
            )
            escalation = self._record_escalation(
                current_path,
                ExecutionPath.DEEP,
                escalation_reason,
                {"real_execution_ratio": run.real_execution_ratio},
            )
            run.metadata["escalation_reason"] = escalation_reason
            run.metadata["escalation_from"] = current_path.value
            run.metadata["escalation_to"] = ExecutionPath.DEEP.value
            return escalation

        # Check if smoke path failed
        if current_path == ExecutionPath.SMOKE and run.status == RunStatus.FAILED:
            escalation_reason = "Smoke validation failed - escalating to standard validation"
            escalation = self._record_escalation(
                current_path,
                ExecutionPath.STANDARD,
                escalation_reason,
                {"status": run.status.value},
            )
            run.metadata["escalation_reason"] = escalation_reason
            run.metadata["escalation_from"] = current_path.value
            run.metadata["escalation_to"] = ExecutionPath.STANDARD.value
            return escalation

        # Check if standard path had high flakiness
        if current_path == ExecutionPath.STANDARD and run.flaky:
            escalation_reason = "Standard validation was flaky - escalating to deep validation"
            escalation = self._record_escalation(
                current_path,
                ExecutionPath.DEEP,
                escalation_reason,
                {"flaky": run.flaky},
            )
            run.metadata["escalation_reason"] = escalation_reason
            run.metadata["escalation_from"] = current_path.value
            run.metadata["escalation_to"] = ExecutionPath.DEEP.value
            return escalation

        return None

    def get_escalation_history(self) -> List[EscalationReason]:
        """Get the escalation history."""
        return self._escalation_history.copy()

    def _calculate_project_health(self, historical_runs: List[Run]) -> float:
        """
        Calculate project health score based on historical runs.

        Args:
            historical_runs: List of historical runs.

        Returns:
            Health score between 0.0 and 1.0.
        """
        if not historical_runs:
            return 0.5  # Neutral score for new projects

        # Calculate pass rate
        completed_runs = [r for r in historical_runs if r.status == RunStatus.COMPLETED]
        if not completed_runs:
            return 0.3  # Low score if no completed runs

        from orchestrator.models import GateResult

        passed_runs = [
            r for r in completed_runs if r.gate_result == GateResult.PASS
        ]
        pass_rate = len(passed_runs) / len(completed_runs)

        # Calculate flakiness penalty
        flaky_runs = [r for r in historical_runs if r.flaky]
        flakiness_penalty = len(flaky_runs) / len(historical_runs) * 0.3

        # Calculate fallback penalty
        avg_fallback = sum(r.fallback_ratio for r in historical_runs) / len(historical_runs)
        fallback_penalty = avg_fallback * 0.2

        health_score = pass_rate - flakiness_penalty - fallback_penalty
        return max(0.0, min(1.0, health_score))

    def _calculate_plugin_depth_score(self, plugin_names: List[str]) -> float:
        """
        Calculate aggregate plugin depth score.

        Args:
            plugin_names: List of plugin names.

        Returns:
            Average depth score between 0.0 and 1.0.
        """
        if not plugin_names:
            return 0.0

        depth_scores = []
        for plugin_name in plugin_names:
            plugin = self.compatibility_analyzer.get_plugin(plugin_name)
            if plugin:
                depth_scores.append(plugin.execution_depth_score)

        if not depth_scores:
            return 0.0

        return sum(depth_scores) / len(depth_scores)

    def _create_strategy(
        self,
        path: ExecutionPath,
        reason: str,
        confidence_threshold: float,
        fallback_threshold: float,
        enable_negative_paths: bool = False,
        enable_retry_rollback: bool = False,
        enable_anomaly_detection: bool = False,
        estimated_duration_multiplier: float = 1.0,
    ) -> ExecutionStrategy:
        """Create an execution strategy."""
        return ExecutionStrategy(
            path=path,
            reason=reason,
            confidence_threshold=confidence_threshold,
            fallback_threshold=fallback_threshold,
            enable_negative_paths=enable_negative_paths,
            enable_retry_rollback=enable_retry_rollback,
            enable_anomaly_detection=enable_anomaly_detection,
            estimated_duration_multiplier=estimated_duration_multiplier,
        )

    def _record_escalation(
        self,
        from_path: ExecutionPath,
        to_path: ExecutionPath,
        reason: str,
        metrics_snapshot: Dict[str, float],
    ) -> ExecutionPath:
        """Record an escalation event and return the new path."""
        escalation = EscalationReason(
            timestamp=datetime.utcnow(),
            from_path=from_path,
            to_path=to_path,
            reason=reason,
            metrics_snapshot=metrics_snapshot,
        )
        self._escalation_history.append(escalation)
        return to_path
