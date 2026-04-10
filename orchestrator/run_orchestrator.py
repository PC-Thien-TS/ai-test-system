"""Run Orchestrator for v2.6.0.

This module integrates the execution intelligence layer into the run lifecycle:
- Intelligent path selection for run triggering
- Automatic escalation workflow (SMOKE -> STANDARD -> DEEP -> INTELLIGENT)
- Escalation chain persistence
- Evidence collection integration
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.confidence_scorer import ConfidenceScorer, ConfidenceScore
from orchestrator.evidence_collector import EvidenceCollector, EvidenceSummary
from orchestrator.execution_intelligence import (
    ExecutionIntelligenceEngine,
    ExecutionPath,
    ExecutionStrategy,
)
from orchestrator.models import (
    EscalationChain,
    ExecutionPath as ExecutionPathModel,
    ProductType,
    Run,
    RunStatus,
)


@dataclass
class RunOrchestrationConfig:
    """Configuration for run orchestration."""
    enable_intelligence: bool = True
    enable_escalation: bool = True
    enable_evidence_collection: bool = True
    max_escalation_depth: int = 3  # Maximum escalation attempts
    evidence_persistence_path: Path = field(default_factory=lambda: Path("outputs/evidence"))


class RunOrchestrator:
    """Orchestrates runs with execution intelligence."""

    def __init__(
        self,
        repo_root: Path,
        config: Optional[RunOrchestrationConfig] = None,
    ):
        """
        Initialize the run orchestrator.

        Args:
            repo_root: Repository root path.
            config: Optional orchestration configuration.
        """
        self.repo_root = repo_root
        self.config = config or RunOrchestrationConfig()
        
        # Initialize intelligence components
        self.intelligence_engine = ExecutionIntelligenceEngine()
        self.evidence_collector = EvidenceCollector()
        self.confidence_scorer = ConfidenceScorer()
        
        # Escalation chain storage
        self.escalation_chains: Dict[str, EscalationChain] = {}
        self.escalation_storage_path = self.repo_root / ".platform" / "escalations"
        self.escalation_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing escalation chains
        self._load_escalation_chains()

    def plan_run(
        self,
        project_id: str,
        product_type: ProductType,
        plugin_names: List[str],
        historical_runs: List[Run],
        forced_path: Optional[ExecutionPathModel] = None,
    ) -> ExecutionStrategy:
        """
        Plan a run with intelligent path selection.

        Args:
            project_id: The project ID.
            product_type: The product type.
            plugin_names: List of plugin names to use.
            historical_runs: Historical run data.
            forced_path: Optional forced execution path.

        Returns:
            ExecutionStrategy with chosen path.
        """
        if not self.config.enable_intelligence:
            # Default to standard if intelligence is disabled
            return ExecutionStrategy(
                path=ExecutionPath.STANDARD,
                reason="Intelligence disabled - using standard path",
                confidence_threshold=0.5,
                fallback_threshold=0.3,
                enable_negative_paths=False,
                enable_retry_rollback=False,
                enable_anomaly_detection=False,
                estimated_duration_multiplier=1.0,
            )

        strategy = self.intelligence_engine.choose_execution_path(
            project_id=project_id,
            product_type=product_type,
            plugin_names=plugin_names,
            historical_runs=historical_runs,
            force_path=forced_path,
        )

        return strategy

    def should_escalate(
        self,
        run: Run,
        plugin_names: List[str],
    ) -> Optional[ExecutionPathModel]:
        """
        Determine if a run should be escalated to a deeper path.

        Args:
            run: The completed run.
            plugin_names: Plugin names used.

        Returns:
            New execution path if escalation is needed, None otherwise.
        """
        if not self.config.enable_escalation:
            return None

        # Check if we've exceeded max escalation depth
        if run.parent_run_id:
            chain = self.get_escalation_chain(run.parent_run_id)
            if chain and len(chain.escalation_path) >= self.config.max_escalation_depth:
                return None

        current_path = ExecutionPath(run.execution_path.value)
        new_path = self.intelligence_engine.should_escalate_path(
            current_path=current_path,
            run=run,
            plugin_names=plugin_names,
        )

        return new_path

    def create_escalation_chain(
        self,
        original_run_id: str,
        current_run_id: str,
        path: ExecutionPathModel,
        reason: str,
    ) -> EscalationChain:
        """
        Create or update an escalation chain.

        Args:
            original_run_id: The original run ID.
            current_run_id: The current (escalated) run ID.
            path: The execution path.
            reason: Reason for escalation.

        Returns:
            The escalation chain.
        """
        # Check if chain already exists
        chain = self.escalation_chains.get(original_run_id)
        
        if chain:
            # Add new escalation step
            chain.add_escalation(current_run_id, path, reason)
        else:
            # Create new chain
            chain = EscalationChain(
                original_run_id=original_run_id,
                current_run_id=current_run_id,
                escalation_path=[
                    {
                        "run_id": current_run_id,
                        "path": path.value,
                        "reason": reason,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ],
            )
        
        self.escalation_chains[original_run_id] = chain
        self._save_escalation_chain(original_run_id)
        
        return chain

    def get_escalation_chain(self, run_id: str) -> Optional[EscalationChain]:
        """
        Get the escalation chain for a run.

        Args:
            run_id: The run ID (original or current).

        Returns:
            The escalation chain if found, None otherwise.
        """
        # First check by original run ID
        if run_id in self.escalation_chains:
            return self.escalation_chains[run_id]
        
        # Check if this is a current run ID in any chain
        for chain in self.escalation_chains.values():
            if chain.current_run_id == run_id:
                return chain
        
        return None

    def collect_evidence(
        self,
        run: Run,
        plugin_names: List[str],
        execution_context: Dict,
    ) -> Dict[str, EvidenceSummary]:
        """
        Collect evidence for a run.

        Args:
            run: The run being executed.
            plugin_names: Plugin names used.
            execution_context: Execution context data.

        Returns:
            Dictionary of plugin names to evidence summaries.
        """
        if not self.config.enable_evidence_collection:
            return {}

        evidence_by_plugin = self.evidence_collector.collect_evidence(
            run=run,
            plugin_names=plugin_names,
            output_path=run.output_path,
            execution_context=execution_context,
        )

        summaries = self.evidence_collector.generate_summary(
            run_id=run.run_id,
            evidence_by_plugin=evidence_by_plugin,
        )

        # Persist evidence
        self._persist_evidence(run.run_id, evidence_by_plugin, summaries)

        return summaries

    def calculate_confidence(
        self,
        plugin_names: List[str],
        run: Run,
        evidence_summaries: Dict[str, EvidenceSummary],
        historical_runs: List[Run],
    ) -> Tuple[float, Dict[str, ConfidenceScore]]:
        """
        Calculate confidence scores for a run.

        Args:
            plugin_names: Plugin names used.
            run: The run.
            evidence_summaries: Evidence summaries by plugin.
            historical_runs: Historical runs.

        Returns:
            Tuple of (aggregate_score, plugin_scores_dict).
        """
        aggregate_score, plugin_scores = self.confidence_scorer.calculate_aggregate_confidence(
            plugin_names=plugin_names,
            run=run,
            evidence_summaries=evidence_summaries,
            historical_runs=historical_runs,
        )

        return aggregate_score, plugin_scores

    def _persist_evidence(
        self,
        run_id: str,
        evidence_by_plugin: Dict[str, List],
        summaries: Dict[str, EvidenceSummary],
    ):
        """
        Persist evidence to disk.

        Args:
            run_id: The run ID.
            evidence_by_plugin: Evidence by plugin.
            summaries: Evidence summaries.
        """
        evidence_dir = self.config.evidence_persistence_path / run_id
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Save evidence items
        for plugin_name, evidence_items in evidence_by_plugin.items():
            plugin_dir = evidence_dir / plugin_name
            plugin_dir.mkdir(parents=True, exist_ok=True)
            
            for i, item in enumerate(evidence_items):
                item_file = plugin_dir / f"evidence_{i}.json"
                with open(item_file, "w") as f:
                    json.dump({
                        "evidence_type": item.evidence_type.value,
                        "timestamp": item.timestamp.isoformat(),
                        "plugin_name": item.plugin_name,
                        "source": item.source,
                        "content": item.content,
                        "confidence": item.confidence,
                        "severity": item.severity,
                    }, f, indent=2)

        # Save summaries
        summary_file = evidence_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(
                {
                    plugin: {
                        "run_id": summary.run_id,
                        "plugin_name": summary.plugin_name,
                        "total_evidence_count": summary.total_evidence_count,
                        "evidence_by_type": {
                            k.value: v for k, v in summary.evidence_by_type.items()
                        },
                        "avg_confidence": summary.avg_confidence,
                        "richness_score": summary.richness_score,
                        "critical_findings_count": len(summary.critical_findings),
                        "warnings_count": len(summary.warnings),
                    }
                    for plugin, summary in summaries.items()
                },
                f,
                indent=2,
            )

    def _save_escalation_chain(self, original_run_id: str):
        """
        Save escalation chain to disk.

        Args:
            original_run_id: The original run ID.
        """
        chain = self.escalation_chains.get(original_run_id)
        if chain:
            chain_file = self.escalation_storage_path / f"{original_run_id}.json"
            with open(chain_file, "w") as f:
                json.dump(chain.to_dict(), f, indent=2)

    def _load_escalation_chains(self):
        """Load escalation chains from disk."""
        if self.escalation_storage_path.exists():
            for chain_file in self.escalation_storage_path.glob("*.json"):
                try:
                    with open(chain_file, "r") as f:
                        data = json.load(f)
                        chain = EscalationChain.from_dict(data)
                        self.escalation_chains[chain.original_run_id] = chain
                except Exception:
                    # Skip corrupted files
                    pass
