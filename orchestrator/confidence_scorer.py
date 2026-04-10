"""Confidence Scoring Algorithms for v2.5.0.

This module provides plugin-specific confidence scoring strategies:
- Real run result based confidence
- Anomaly-aware confidence
- Plugin-specific confidence strategies
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from orchestrator.compatibility import CompatibilityAnalyzer
from orchestrator.evidence_collector import EvidenceItem, EvidenceSummary
from orchestrator.models import GateResult, Run, RunStatus, SupportLevel


@dataclass
class ConfidenceFactors:
    """Factors that contribute to confidence score."""
    evidence_richness: float = 0.0
    run_stability: float = 0.0
    anomaly_free: float = 0.0
    historical_performance: float = 0.0
    plugin_maturity: float = 0.0
    fallback_penalty: float = 0.0


@dataclass
class ConfidenceScore:
    """Confidence score with detailed breakdown."""
    overall_score: float  # 0.0 to 1.0
    factors: ConfidenceFactors
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: List[str] = field(default_factory=list)


class ConfidenceStrategy(ABC):
    """Base class for plugin-specific confidence strategies."""

    def __init__(self, plugin_name: str):
        """
        Initialize the confidence strategy.

        Args:
            plugin_name: The name of the plugin this strategy is for.
        """
        self.plugin_name = plugin_name

    @abstractmethod
    def calculate_confidence(
        self,
        run: Run,
        evidence_summary: Optional[EvidenceSummary],
        historical_runs: List[Run],
    ) -> ConfidenceScore:
        """
        Calculate confidence score for a plugin execution.

        Args:
            run: The current run.
            evidence_summary: Evidence summary if available.
            historical_runs: Historical run data.

        Returns:
            ConfidenceScore with detailed breakdown.
        """
        pass


class WebPlaywrightConfidenceStrategy(ConfidenceStrategy):
    """Confidence strategy for web_playwright plugin."""

    def calculate_confidence(
        self,
        run: Run,
        evidence_summary: Optional[EvidenceSummary],
        historical_runs: List[Run],
    ) -> ConfidenceScore:
        """Calculate confidence for web testing."""
        factors = ConfidenceFactors()
        notes = []

        # Evidence richness factor
        if evidence_summary:
            factors.evidence_richness = evidence_summary.richness_score
            if evidence_summary.richness_score < 0.5:
                notes.append("Low evidence richness - consider enabling screenshots")
        else:
            factors.evidence_richness = 0.5
            notes.append("No evidence summary available")

        # Run stability factor
        if run.status == RunStatus.COMPLETED and run.gate_result == GateResult.PASS:
            factors.run_stability = 1.0
        elif run.status == RunStatus.COMPLETED:
            factors.run_stability = 0.6
        else:
            factors.run_stability = 0.0
            notes.append("Run did not complete successfully")

        # Anomaly-free factor
        if evidence_summary:
            anomaly_count = len(
                [e for e in evidence_summary.critical_findings if "anomaly" in e.source.lower()]
            )
            factors.anomaly_free = max(0.0, 1.0 - (anomaly_count * 0.2))
            if anomaly_count > 0:
                notes.append(f"Detected {anomaly_count} anomalies")
        else:
            factors.anomaly_free = 0.8

        # Historical performance
        if historical_runs:
            completed_runs = [r for r in historical_runs if r.status == RunStatus.COMPLETED]
            if completed_runs:
                passed_runs = [
                    r for r in completed_runs if r.gate_result == GateResult.PASS
                ]
                factors.historical_performance = len(passed_runs) / len(completed_runs)
            else:
                factors.historical_performance = 0.5
        else:
            factors.historical_performance = 0.5

        # Plugin maturity (from metadata)
        factors.plugin_maturity = 0.85  # web_playwright has high maturity

        # Fallback penalty
        factors.fallback_penalty = run.fallback_ratio * 0.3
        if run.fallback_ratio > 0.3:
            notes.append(f"High fallback ratio: {run.fallback_ratio:.2f}")

        # Calculate overall score (weighted average)
        overall = (
            (factors.evidence_richness * 0.25)
            + (factors.run_stability * 0.30)
            + (factors.anomaly_free * 0.15)
            + (factors.historical_performance * 0.15)
            + (factors.plugin_maturity * 0.10)
            - factors.fallback_penalty
        )

        return ConfidenceScore(
            overall_score=max(0.0, min(1.0, overall)),
            factors=factors,
            notes=notes,
        )


class ApiContractConfidenceStrategy(ConfidenceStrategy):
    """Confidence strategy for api_contract plugin."""

    def calculate_confidence(
        self,
        run: Run,
        evidence_summary: Optional[EvidenceSummary],
        historical_runs: List[Run],
    ) -> ConfidenceScore:
        """Calculate confidence for API contract testing."""
        factors = ConfidenceFactors()
        notes = []

        # Evidence richness factor
        if evidence_summary:
            factors.evidence_richness = evidence_summary.richness_score
            schema_valid = evidence_summary.evidence_by_type.get(
                "schema_validation", 0
            )
            if schema_valid < 3:
                notes.append("Low schema validation coverage")
        else:
            factors.evidence_richness = 0.5

        # Run stability factor
        if run.status == RunStatus.COMPLETED and run.gate_result == GateResult.PASS:
            factors.run_stability = 1.0
        elif run.status == RunStatus.COMPLETED:
            factors.run_stability = 0.7
        else:
            factors.run_stability = 0.0
            notes.append("Run did not complete successfully")

        # Anomaly-free factor (important for API)
        if evidence_summary:
            anomaly_count = len(
                [e for e in evidence_summary.critical_findings if "anomaly" in e.source.lower()]
            )
            factors.anomaly_free = max(0.0, 1.0 - (anomaly_count * 0.3))
            if anomaly_count > 0:
                notes.append(f"Detected {anomaly_count} API anomalies")
        else:
            factors.anomaly_free = 0.7

        # Historical performance
        if historical_runs:
            completed_runs = [r for r in historical_runs if r.status == RunStatus.COMPLETED]
            if completed_runs:
                passed_runs = [
                    r for r in completed_runs if r.gate_result == GateResult.PASS
                ]
                factors.historical_performance = len(passed_runs) / len(completed_runs)
            else:
                factors.historical_performance = 0.5
        else:
            factors.historical_performance = 0.5

        # Plugin maturity
        factors.plugin_maturity = 0.90  # api_contract has very high maturity

        # Fallback penalty
        factors.fallback_penalty = run.fallback_ratio * 0.4
        if run.fallback_ratio > 0.2:
            notes.append(f"High fallback ratio: {run.fallback_ratio:.2f}")

        # Calculate overall score
        overall = (
            (factors.evidence_richness * 0.25)
            + (factors.run_stability * 0.30)
            + (factors.anomaly_free * 0.20)
            + (factors.historical_performance * 0.15)
            + (factors.plugin_maturity * 0.10)
            - factors.fallback_penalty
        )

        return ConfidenceScore(
            overall_score=max(0.0, min(1.0, overall)),
            factors=factors,
            notes=notes,
        )


class RagGroundingConfidenceStrategy(ConfidenceStrategy):
    """Confidence strategy for rag_grounding plugin."""

    def calculate_confidence(
        self,
        run: Run,
        evidence_summary: Optional[EvidenceSummary],
        historical_runs: List[Run],
    ) -> ConfidenceScore:
        """Calculate confidence for RAG grounding testing."""
        factors = ConfidenceFactors()
        notes = []

        # Evidence richness factor (citations are critical for RAG)
        if evidence_summary:
            factors.evidence_richness = evidence_summary.richness_score
            citation_count = evidence_summary.evidence_by_type.get("citation", 0)
            if citation_count < 2:
                notes.append("Low citation count - grounding may be weak")
        else:
            factors.evidence_richness = 0.5

        # Run stability factor
        if run.status == RunStatus.COMPLETED and run.gate_result == GateResult.PASS:
            factors.run_stability = 1.0
        elif run.status == RunStatus.COMPLETED:
            factors.run_stability = 0.6
        else:
            factors.run_stability = 0.0

        # Anomaly-free factor
        if evidence_summary:
            factors.anomaly_free = 0.9  # RAG has fewer traditional anomalies
        else:
            factors.anomaly_free = 0.8

        # Historical performance
        if historical_runs:
            completed_runs = [r for r in historical_runs if r.status == RunStatus.COMPLETED]
            if completed_runs:
                passed_runs = [
                    r for r in completed_runs if r.gate_result == GateResult.PASS
                ]
                factors.historical_performance = len(passed_runs) / len(completed_runs)
            else:
                factors.historical_performance = 0.5
        else:
            factors.historical_performance = 0.5

        # Plugin maturity
        factors.plugin_maturity = 0.78  # rag_grounding has good maturity

        # Fallback penalty
        factors.fallback_penalty = run.fallback_ratio * 0.3

        # Calculate overall score (higher weight on evidence for RAG)
        overall = (
            (factors.evidence_richness * 0.35)
            + (factors.run_stability * 0.25)
            + (factors.anomaly_free * 0.10)
            + (factors.historical_performance * 0.15)
            + (factors.plugin_maturity * 0.10)
            - factors.fallback_penalty
        )

        return ConfidenceScore(
            overall_score=max(0.0, min(1.0, overall)),
            factors=factors,
            notes=notes,
        )


class ConfidenceScorer:
    """Main confidence scorer that coordinates plugin-specific strategies."""

    def __init__(self, compatibility_analyzer: Optional[CompatibilityAnalyzer] = None):
        """
        Initialize the confidence scorer.

        Args:
            compatibility_analyzer: Optional compatibility analyzer.
        """
        self.compatibility_analyzer = compatibility_analyzer or CompatibilityAnalyzer()
        self._strategies: Dict[str, ConfidenceStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register default confidence strategies for built-in plugins."""
        self._strategies["web_playwright"] = WebPlaywrightConfidenceStrategy("web_playwright")
        self._strategies["api_contract"] = ApiContractConfidenceStrategy("api_contract")
        self._strategies["rag_grounding"] = RagGroundingConfidenceStrategy("rag_grounding")

    def register_strategy(self, plugin_name: str, strategy: ConfidenceStrategy):
        """
        Register a custom confidence strategy for a plugin.

        Args:
            plugin_name: The name of the plugin.
            strategy: The confidence strategy instance.
        """
        self._strategies[plugin_name] = strategy

    def calculate_confidence(
        self,
        plugin_name: str,
        run: Run,
        evidence_summary: Optional[EvidenceSummary],
        historical_runs: List[Run],
    ) -> ConfidenceScore:
        """
        Calculate confidence score for a plugin execution.

        Args:
            plugin_name: The name of the plugin.
            run: The current run.
            evidence_summary: Evidence summary if available.
            historical_runs: Historical run data.

        Returns:
            ConfidenceScore with detailed breakdown.
        """
        strategy = self._strategies.get(plugin_name)
        if strategy:
            return strategy.calculate_confidence(run, evidence_summary, historical_runs)
        else:
            # Default generic strategy
            return self._generic_confidence(run, historical_runs)

    def calculate_aggregate_confidence(
        self,
        plugin_names: List[str],
        run: Run,
        evidence_summaries: Dict[str, EvidenceSummary],
        historical_runs: List[Run],
    ) -> Tuple[float, Dict[str, ConfidenceScore]]:
        """
        Calculate aggregate confidence across multiple plugins.

        Args:
            plugin_names: List of plugin names.
            run: The current run.
            evidence_summaries: Dictionary of plugin names to evidence summaries.
            historical_runs: Historical run data.

        Returns:
            Tuple of (aggregate_score, plugin_scores_dict).
        """
        plugin_scores = {}
        total_score = 0.0
        count = 0

        for plugin_name in plugin_names:
            evidence_summary = evidence_summaries.get(plugin_name)
            score = self.calculate_confidence(
                plugin_name, run, evidence_summary, historical_runs
            )
            plugin_scores[plugin_name] = score
            total_score += score.overall_score
            count += 1

        aggregate_score = total_score / count if count > 0 else 0.0
        return aggregate_score, plugin_scores

    def _generic_confidence(
        self, run: Run, historical_runs: List[Run]
    ) -> ConfidenceScore:
        """Calculate generic confidence for plugins without specific strategies."""
        factors = ConfidenceFactors()
        notes = ["Using generic confidence strategy"]

        # Run stability
        if run.status == RunStatus.COMPLETED and run.gate_result == GateResult.PASS:
            factors.run_stability = 1.0
        elif run.status == RunStatus.COMPLETED:
            factors.run_stability = 0.6
        else:
            factors.run_stability = 0.0

        # Historical performance
        if historical_runs:
            completed_runs = [r for r in historical_runs if r.status == RunStatus.COMPLETED]
            if completed_runs:
                passed_runs = [
                    r for r in completed_runs if r.gate_result == GateResult.PASS
                ]
                factors.historical_performance = len(passed_runs) / len(completed_runs)
            else:
                factors.historical_performance = 0.5
        else:
            factors.historical_performance = 0.5

        # Fallback penalty
        factors.fallback_penalty = run.fallback_ratio * 0.3

        # Calculate overall
        overall = (
            (factors.run_stability * 0.5)
            + (factors.historical_performance * 0.3)
            - factors.fallback_penalty
        )

        return ConfidenceScore(
            overall_score=max(0.0, min(1.0, overall)),
            factors=factors,
            notes=notes,
        )
