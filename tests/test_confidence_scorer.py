"""Tests for confidence scorer."""

import pytest
from datetime import datetime
from pathlib import Path

from orchestrator.confidence_scorer import (
    ApiContractConfidenceStrategy,
    ConfidenceFactors,
    ConfidenceScore,
    ConfidenceScorer,
    RagGroundingConfidenceStrategy,
    WebPlaywrightConfidenceStrategy,
)
from orchestrator.evidence_collector import EvidenceSummary, EvidenceType
from orchestrator.models import GateResult, Run, RunStatus


def test_web_playwright_confidence_strategy():
    """Test confidence calculation for web_playwright."""
    strategy = WebPlaywrightConfidenceStrategy("web_playwright")
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        fallback_ratio=0.1,
        real_execution_ratio=0.9,
    )
    
    evidence_summary = EvidenceSummary(
        run_id="run-1",
        plugin_name="web_playwright",
        total_evidence_count=10,
        evidence_by_type={
            EvidenceType.SCREENSHOT: 3,
            EvidenceType.NETWORK_TRACE: 5,
            EvidenceType.ASSERTION_RESULT: 2,
        },
        avg_confidence=0.9,
        richness_score=0.85,
        critical_findings=[],
        warnings=[],
    )
    
    historical_runs = [
        Run(
            run_id="run-0",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            gate_result=GateResult.PASS,
            fallback_ratio=0.0,
            real_execution_ratio=1.0,
        )
    ]
    
    score = strategy.calculate_confidence(run, evidence_summary, historical_runs)
    
    assert 0.0 <= score.overall_score <= 1.0
    assert score.overall_score > 0.7  # Should have high confidence
    assert score.factors.run_stability == 1.0
    assert score.factors.evidence_richness > 0.5


def test_api_contract_confidence_strategy():
    """Test confidence calculation for api_contract."""
    strategy = ApiContractConfidenceStrategy("api_contract")
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        fallback_ratio=0.05,
        real_execution_ratio=0.95,
    )
    
    evidence_summary = EvidenceSummary(
        run_id="run-1",
        plugin_name="api_contract",
        total_evidence_count=8,
        evidence_by_type={
            EvidenceType.SCHEMA_VALIDATION: 4,
            EvidenceType.NETWORK_TRACE: 4,
        },
        avg_confidence=0.95,
        richness_score=0.9,
        critical_findings=[],
        warnings=[],
    )
    
    historical_runs = []
    
    score = strategy.calculate_confidence(run, evidence_summary, historical_runs)
    
    assert 0.0 <= score.overall_score <= 1.0
    assert score.factors.plugin_maturity == 0.9  # api_contract has high maturity


def test_rag_grounding_confidence_strategy():
    """Test confidence calculation for rag_grounding."""
    strategy = RagGroundingConfidenceStrategy("rag_grounding")
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        fallback_ratio=0.2,
        real_execution_ratio=0.8,
    )
    
    evidence_summary = EvidenceSummary(
        run_id="run-1",
        plugin_name="rag_grounding",
        total_evidence_count=6,
        evidence_by_type={
            EvidenceType.RETRIEVAL_RESULT: 3,
            EvidenceType.CITATION: 3,
        },
        avg_confidence=0.85,
        richness_score=0.8,
        critical_findings=[],
        warnings=[],
    )
    
    historical_runs = []
    
    score = strategy.calculate_confidence(run, evidence_summary, historical_runs)
    
    assert 0.0 <= score.overall_score <= 1.0
    assert score.factors.plugin_maturity == 0.78  # rag_grounding maturity


def test_confidence_sorer_calculate_confidence():
    """Test confidence scorer with specific plugin."""
    scorer = ConfidenceScorer()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        fallback_ratio=0.1,
        real_execution_ratio=0.9,
    )
    
    score = scorer.calculate_confidence("web_playwright", run, None, [])
    
    assert isinstance(score, ConfidenceScore)
    assert 0.0 <= score.overall_score <= 1.0
    assert isinstance(score.factors, ConfidenceFactors)


def test_confidence_sorer_aggregate_confidence():
    """Test aggregate confidence across multiple plugins."""
    scorer = ConfidenceScorer()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        fallback_ratio=0.1,
        real_execution_ratio=0.9,
    )
    
    evidence_summaries = {
        "web_playwright": EvidenceSummary(
            run_id="run-1",
            plugin_name="web_playwright",
            total_evidence_count=10,
            evidence_by_type={},
            avg_confidence=0.9,
            richness_score=0.85,
            critical_findings=[],
            warnings=[],
        ),
        "api_contract": EvidenceSummary(
            run_id="run-1",
            plugin_name="api_contract",
            total_evidence_count=8,
            evidence_by_type={},
            avg_confidence=0.95,
            richness_score=0.9,
            critical_findings=[],
            warnings=[],
        ),
    }
    
    aggregate_score, plugin_scores = scorer.calculate_aggregate_confidence(
        ["web_playwright", "api_contract"],
        run,
        evidence_summaries,
        [],
    )
    
    assert 0.0 <= aggregate_score <= 1.0
    assert "web_playwright" in plugin_scores
    assert "api_contract" in plugin_scores
    assert len(plugin_scores) == 2


def test_confidence_sorer_generic_strategy():
    """Test generic confidence strategy for plugins without specific strategy."""
    scorer = ConfidenceScorer()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        fallback_ratio=0.1,
        real_execution_ratio=0.9,
    )
    
    score = scorer.calculate_confidence("nonexistent_plugin", run, None, [])
    
    assert isinstance(score, ConfidenceScore)
    assert 0.0 <= score.overall_score <= 1.0
    assert "Using generic confidence strategy" in score.notes


def test_confidence_factors_defaults():
    """Test that confidence factors have sensible defaults."""
    factors = ConfidenceFactors()
    
    assert factors.evidence_richness == 0.0
    assert factors.run_stability == 0.0
    assert factors.anomaly_free == 0.0
    assert factors.historical_performance == 0.0
    assert factors.plugin_maturity == 0.0
    assert factors.fallback_penalty == 0.0
