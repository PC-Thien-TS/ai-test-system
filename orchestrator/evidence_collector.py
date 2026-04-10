"""Evidence Collection Framework for v2.5.0.

This module provides evidence collection capabilities for different plugin types:
- Per-plugin evidence adapters
- Dynamic evidence richness score calculation
- Evidence aggregation and reporting
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.compatibility import CompatibilityAnalyzer
from orchestrator.models import ProductType, Run


class EvidenceType(Enum):
    """Types of evidence that can be collected."""
    SCREENSHOT = "screenshot"
    NETWORK_TRACE = "network_trace"
    LOG_ENTRY = "log_entry"
    ASSERTION_RESULT = "assertion_result"
    METRIC_VALUE = "metric_value"
    CITATION = "citation"
    RETRIEVAL_RESULT = "retrieval_result"
    STATE_SNAPSHOT = "state_snapshot"
    SCHEMA_VALIDATION = "schema_validation"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class EvidenceItem:
    """A single piece of evidence collected during execution."""
    evidence_type: EvidenceType
    timestamp: datetime
    plugin_name: str
    source: str  # Where the evidence came from
    content: Dict[str, Any]  # The actual evidence data
    confidence: float  # Confidence in this evidence (0.0-1.0)
    severity: str  # "info", "warning", "error", "critical"


@dataclass
class EvidenceSummary:
    """Summary of evidence collected for a run."""
    run_id: str
    plugin_name: str
    total_evidence_count: int
    evidence_by_type: Dict[EvidenceType, int]
    avg_confidence: float
    richness_score: float  # Calculated evidence richness score (0.0-1.0)
    critical_findings: List[EvidenceItem]
    warnings: List[EvidenceItem]


class EvidenceAdapter(ABC):
    """Base class for plugin-specific evidence adapters."""

    def __init__(self, plugin_name: str):
        """
        Initialize the evidence adapter.

        Args:
            plugin_name: The name of the plugin this adapter is for.
        """
        self.plugin_name = plugin_name

    @abstractmethod
    def collect_evidence(
        self,
        run: Run,
        output_path: Path,
        execution_context: Dict[str, Any],
    ) -> List[EvidenceItem]:
        """
        Collect evidence for a specific plugin execution.

        Args:
            run: The run being executed.
            output_path: Path to the run output directory.
            execution_context: Context about the execution.

        Returns:
            List of evidence items collected.
        """
        pass

    @abstractmethod
    def calculate_richness(self, evidence: List[EvidenceItem]) -> float:
        """
        Calculate evidence richness score for this plugin.

        Args:
            evidence: List of evidence items collected.

        Returns:
            Richness score between 0.0 and 1.0.
        """
        pass


class WebPlaywrightEvidenceAdapter(EvidenceAdapter):
    """Evidence adapter for web_playwright plugin."""

    def collect_evidence(
        self,
        run: Run,
        output_path: Path,
        execution_context: Dict[str, Any],
    ) -> List[EvidenceItem]:
        """Collect evidence from Playwright web testing."""
        evidence = []
        timestamp = datetime.utcnow()

        # Simulate collecting screenshots
        screenshot_count = execution_context.get("screenshot_count", 0)
        for i in range(screenshot_count):
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.SCREENSHOT,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="playwright_screenshot",
                    content={"step": i, "url": execution_context.get("url", "")},
                    confidence=0.95,
                    severity="info",
                )
            )

        # Simulate collecting network traces
        network_requests = execution_context.get("network_requests", [])
        for req in network_requests[:10]:  # Limit to 10 for example
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.NETWORK_TRACE,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="playwright_network",
                    content={"url": req.get("url"), "status": req.get("status")},
                    confidence=0.9,
                    severity="info",
                )
            )

        # Simulate assertion results
        assertions = execution_context.get("assertions", [])
        for assertion in assertions:
            severity = "error" if not assertion.get("passed", True) else "info"
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.ASSERTION_RESULT,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="playwright_assertion",
                    content=assertion,
                    confidence=1.0,
                    severity=severity,
                )
            )

        return evidence

    def calculate_richness(self, evidence: List[EvidenceItem]) -> float:
        """Calculate richness for web testing evidence."""
        if not evidence:
            return 0.0

        # Richness factors: diversity of evidence types, confidence, critical findings
        type_diversity = len(set(e.evidence_type for e in evidence))
        type_score = min(1.0, type_diversity / 4.0)  # Up to 4 types considered diverse

        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)
        confidence_score = avg_confidence

        # Bonus for having screenshots and network traces
        has_screenshots = any(e.evidence_type == EvidenceType.SCREENSHOT for e in evidence)
        has_network = any(e.evidence_type == EvidenceType.NETWORK_TRACE for e in evidence)
        bonus_score = 0.2 if has_screenshots and has_network else 0.0

        richness = (type_score * 0.4) + (confidence_score * 0.4) + bonus_score
        return min(1.0, richness)


class ApiContractEvidenceAdapter(EvidenceAdapter):
    """Evidence adapter for api_contract plugin."""

    def collect_evidence(
        self,
        run: Run,
        output_path: Path,
        execution_context: Dict[str, Any],
    ) -> List[EvidenceItem]:
        """Collect evidence from API contract testing."""
        evidence = []
        timestamp = datetime.utcnow()

        # Collect schema validation results
        schema_validations = execution_context.get("schema_validations", [])
        for validation in schema_validations:
            severity = "error" if not validation.get("valid", True) else "info"
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.SCHEMA_VALIDATION,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="jsonschema_validation",
                    content=validation,
                    confidence=0.95,
                    severity=severity,
                )
            )

        # Collect network traces for API calls
        api_calls = execution_context.get("api_calls", [])
        for call in api_calls:
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.NETWORK_TRACE,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="http_request",
                    content={
                        "method": call.get("method"),
                        "url": call.get("url"),
                        "status_code": call.get("status_code"),
                    },
                    confidence=1.0,
                    severity="info",
                )
            )

        # Detect anomalies in response patterns
        anomalies = execution_context.get("anomalies", [])
        for anomaly in anomalies:
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.ANOMALY_DETECTED,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="anomaly_detection",
                    content=anomaly,
                    confidence=0.8,
                    severity="warning",
                )
            )

        return evidence

    def calculate_richness(self, evidence: List[EvidenceItem]) -> float:
        """Calculate richness for API contract evidence."""
        if not evidence:
            return 0.0

        # Richness factors: schema coverage, anomaly detection, network diversity
        has_schema = any(e.evidence_type == EvidenceType.SCHEMA_VALIDATION for e in evidence)
        has_anomaly = any(e.evidence_type == EvidenceType.ANOMALY_DETECTED for e in evidence)
        has_network = any(e.evidence_type == EvidenceType.NETWORK_TRACE for e in evidence)

        type_diversity = len(set(e.evidence_type for e in evidence))
        type_score = min(1.0, type_diversity / 3.0)

        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)
        confidence_score = avg_confidence

        bonus_score = 0.2 if has_schema and has_anomaly else 0.0
        bonus_score += 0.1 if has_network else 0.0

        richness = (type_score * 0.4) + (confidence_score * 0.4) + bonus_score
        return min(1.0, richness)


class RagGroundingEvidenceAdapter(EvidenceAdapter):
    """Evidence adapter for rag_grounding plugin."""

    def collect_evidence(
        self,
        run: Run,
        output_path: Path,
        execution_context: Dict[str, Any],
    ) -> List[EvidenceItem]:
        """Collect evidence from RAG grounding testing."""
        evidence = []
        timestamp = datetime.utcnow()

        # Collect retrieval results
        retrievals = execution_context.get("retrievals", [])
        for retrieval in retrievals:
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.RETRIEVAL_RESULT,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="vector_retrieval",
                    content={
                        "query": retrieval.get("query"),
                        "doc_id": retrieval.get("doc_id"),
                        "score": retrieval.get("score"),
                    },
                    confidence=retrieval.get("score", 0.5),
                    severity="info",
                )
            )

        # Collect citation verifications
        citations = execution_context.get("citations", [])
        for citation in citations:
            severity = "warning" if not citation.get("verified", True) else "info"
            evidence.append(
                EvidenceItem(
                    evidence_type=EvidenceType.CITATION,
                    timestamp=timestamp,
                    plugin_name=self.plugin_name,
                    source="citation_checker",
                    content=citation,
                    confidence=0.85,
                    severity=severity,
                )
            )

        return evidence

    def calculate_richness(self, evidence: List[EvidenceItem]) -> float:
        """Calculate richness for RAG grounding evidence."""
        if not evidence:
            return 0.0

        # Richness factors: retrieval diversity, citation verification
        has_retrieval = any(e.evidence_type == EvidenceType.RETRIEVAL_RESULT for e in evidence)
        has_citation = any(e.evidence_type == EvidenceType.CITATION for e in evidence)

        type_diversity = len(set(e.evidence_type for e in evidence))
        type_score = min(1.0, type_diversity / 2.0)

        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)
        confidence_score = avg_confidence

        bonus_score = 0.3 if has_retrieval and has_citation else 0.0

        richness = (type_score * 0.4) + (confidence_score * 0.3) + bonus_score
        return min(1.0, richness)


class EvidenceCollector:
    """Main evidence collector that coordinates plugin-specific adapters."""

    def __init__(self, compatibility_analyzer: Optional[CompatibilityAnalyzer] = None):
        """
        Initialize the evidence collector.

        Args:
            compatibility_analyzer: Optional compatibility analyzer.
        """
        self.compatibility_analyzer = compatibility_analyzer or CompatibilityAnalyzer()
        self._adapters: Dict[str, EvidenceAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        """Register default evidence adapters for built-in plugins."""
        self._adapters["web_playwright"] = WebPlaywrightEvidenceAdapter("web_playwright")
        self._adapters["api_contract"] = ApiContractEvidenceAdapter("api_contract")
        self._adapters["rag_grounding"] = RagGroundingEvidenceAdapter("rag_grounding")

    def register_adapter(self, plugin_name: str, adapter: EvidenceAdapter):
        """
        Register a custom evidence adapter for a plugin.

        Args:
            plugin_name: The name of the plugin.
            adapter: The evidence adapter instance.
        """
        self._adapters[plugin_name] = adapter

    def collect_evidence(
        self,
        run: Run,
        plugin_names: List[str],
        output_path: Path,
        execution_context: Dict[str, Any],
    ) -> Dict[str, List[EvidenceItem]]:
        """
        Collect evidence for all specified plugins.

        Args:
            run: The run being executed.
            plugin_names: List of plugin names to collect evidence for.
            output_path: Path to the run output directory.
            execution_context: Context about the execution.

        Returns:
            Dictionary mapping plugin names to their evidence lists.
        """
        evidence_by_plugin: Dict[str, List[EvidenceItem]] = {}

        for plugin_name in plugin_names:
            adapter = self._adapters.get(plugin_name)
            if adapter:
                evidence = adapter.collect_evidence(run, output_path, execution_context)
                evidence_by_plugin[plugin_name] = evidence
            else:
                evidence_by_plugin[plugin_name] = []

        return evidence_by_plugin

    def calculate_richness_scores(
        self,
        evidence_by_plugin: Dict[str, List[EvidenceItem]],
    ) -> Dict[str, float]:
        """
        Calculate evidence richness scores for all plugins.

        Args:
            evidence_by_plugin: Dictionary mapping plugin names to evidence lists.

        Returns:
            Dictionary mapping plugin names to richness scores.
        """
        richness_scores = {}

        for plugin_name, evidence in evidence_by_plugin.items():
            adapter = self._adapters.get(plugin_name)
            if adapter:
                richness_scores[plugin_name] = adapter.calculate_richness(evidence)
            else:
                richness_scores[plugin_name] = 0.0

        return richness_scores

    def generate_summary(
        self,
        run_id: str,
        evidence_by_plugin: Dict[str, List[EvidenceItem]],
    ) -> Dict[str, EvidenceSummary]:
        """
        Generate evidence summaries for all plugins.

        Args:
            run_id: The run ID.
            evidence_by_plugin: Dictionary mapping plugin names to evidence lists.

        Returns:
            Dictionary mapping plugin names to evidence summaries.
        """
        summaries = {}

        for plugin_name, evidence in evidence_by_plugin.items():
            evidence_by_type = {}
            for e in evidence:
                evidence_by_type[e.evidence_type] = evidence_by_type.get(e.evidence_type, 0) + 1

            avg_confidence = (
                sum(e.confidence for e in evidence) / len(evidence) if evidence else 0.0
            )

            critical_findings = [e for e in evidence if e.severity in ("error", "critical")]
            warnings = [e for e in evidence if e.severity == "warning"]

            adapter = self._adapters.get(plugin_name)
            richness_score = adapter.calculate_richness(evidence) if adapter else 0.0

            summaries[plugin_name] = EvidenceSummary(
                run_id=run_id,
                plugin_name=plugin_name,
                total_evidence_count=len(evidence),
                evidence_by_type=evidence_by_type,
                avg_confidence=avg_confidence,
                richness_score=richness_score,
                critical_findings=critical_findings,
                warnings=warnings,
            )

        return summaries
