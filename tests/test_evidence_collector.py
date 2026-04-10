"""Tests for evidence collector."""

import pytest
from datetime import datetime
from pathlib import Path

from orchestrator.evidence_collector import (
    ApiContractEvidenceAdapter,
    EvidenceCollector,
    EvidenceItem,
    EvidenceSummary,
    EvidenceType,
    RagGroundingEvidenceAdapter,
    WebPlaywrightEvidenceAdapter,
)
from orchestrator.models import Run, RunStatus


def test_web_playwright_adapter_collect_evidence():
    """Test collecting evidence from web_playwright adapter."""
    adapter = WebPlaywrightEvidenceAdapter("web_playwright")
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
    )
    
    execution_context = {
        "screenshot_count": 3,
        "url": "https://example.com",
        "network_requests": [
            {"url": "https://api.example.com/data", "status": 200},
            {"url": "https://api.example.com/user", "status": 200},
        ],
        "assertions": [
            {"name": "title_check", "passed": True},
            {"name": "button_click", "passed": False},
        ],
    }
    
    evidence = adapter.collect_evidence(run, Path("/output"), execution_context)
    
    assert len(evidence) > 0
    assert any(e.evidence_type == EvidenceType.SCREENSHOT for e in evidence)
    assert any(e.evidence_type == EvidenceType.NETWORK_TRACE for e in evidence)
    assert any(e.evidence_type == EvidenceType.ASSERTION_RESULT for e in evidence)


def test_web_playwright_adapter_richness():
    """Test calculating richness for web_playwright evidence."""
    adapter = WebPlaywrightEvidenceAdapter("web_playwright")
    
    evidence = [
        EvidenceItem(
            evidence_type=EvidenceType.SCREENSHOT,
            timestamp=datetime.utcnow(),
            plugin_name="web_playwright",
            source="playwright_screenshot",
            content={"step": 0},
            confidence=0.95,
            severity="info",
        ),
        EvidenceItem(
            evidence_type=EvidenceType.NETWORK_TRACE,
            timestamp=datetime.utcnow(),
            plugin_name="web_playwright",
            source="playwright_network",
            content={"url": "https://example.com"},
            confidence=0.9,
            severity="info",
        ),
    ]
    
    richness = adapter.calculate_richness(evidence)
    assert 0.0 <= richness <= 1.0
    assert richness > 0.5  # Should have good richness with screenshots and network traces


def test_api_contract_adapter_collect_evidence():
    """Test collecting evidence from api_contract adapter."""
    adapter = ApiContractEvidenceAdapter("api_contract")
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
    )
    
    execution_context = {
        "schema_validations": [
            {"endpoint": "/api/users", "valid": True},
            {"endpoint": "/api/posts", "valid": False},
        ],
        "api_calls": [
            {"method": "GET", "url": "/api/users", "status_code": 200},
            {"method": "POST", "url": "/api/posts", "status_code": 201},
        ],
        "anomalies": [
            {"type": "response_time_spike", "value": 5000},
        ],
    }
    
    evidence = adapter.collect_evidence(run, Path("/output"), execution_context)
    
    assert len(evidence) > 0
    assert any(e.evidence_type == EvidenceType.SCHEMA_VALIDATION for e in evidence)
    assert any(e.evidence_type == EvidenceType.NETWORK_TRACE for e in evidence)
    assert any(e.evidence_type == EvidenceType.ANOMALY_DETECTED for e in evidence)


def test_rag_grounding_adapter_collect_evidence():
    """Test collecting evidence from rag_grounding adapter."""
    adapter = RagGroundingEvidenceAdapter("rag_grounding")
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
    )
    
    execution_context = {
        "retrievals": [
            {"query": "What is AI?", "doc_id": "doc-1", "score": 0.95},
            {"query": "How does RAG work?", "doc_id": "doc-2", "score": 0.87},
        ],
        "citations": [
            {"claim": "AI is machine learning", "verified": True},
            {"claim": "RAG is free", "verified": False},
        ],
    }
    
    evidence = adapter.collect_evidence(run, Path("/output"), execution_context)
    
    assert len(evidence) > 0
    assert any(e.evidence_type == EvidenceType.RETRIEVAL_RESULT for e in evidence)
    assert any(e.evidence_type == EvidenceType.CITATION for e in evidence)


def test_evidence_collector_collect_all():
    """Test collecting evidence for multiple plugins."""
    collector = EvidenceCollector()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
    )
    
    execution_context = {
        "screenshot_count": 2,
        "url": "https://example.com",
        "network_requests": [],
        "assertions": [],
    }
    
    evidence_by_plugin = collector.collect_evidence(
        run,
        plugin_names=["web_playwright", "api_contract"],
        output_path=Path("/output"),
        execution_context=execution_context,
    )
    
    assert "web_playwright" in evidence_by_plugin
    assert "api_contract" in evidence_by_plugin
    assert len(evidence_by_plugin["web_playwright"]) > 0


def test_evidence_collector_richness_scores():
    """Test calculating richness scores for multiple plugins."""
    collector = EvidenceCollector()
    
    evidence_by_plugin = {
        "web_playwright": [
            EvidenceItem(
                evidence_type=EvidenceType.SCREENSHOT,
                timestamp=datetime.utcnow(),
                plugin_name="web_playwright",
                source="playwright",
                content={},
                confidence=0.9,
                severity="info",
            ),
        ],
        "api_contract": [],
    }
    
    richness_scores = collector.calculate_richness_scores(evidence_by_plugin)
    
    assert "web_playwright" in richness_scores
    assert "api_contract" in richness_scores
    assert richness_scores["web_playwright"] > 0
    assert richness_scores["api_contract"] == 0


def test_evidence_collector_generate_summary():
    """Test generating evidence summaries."""
    collector = EvidenceCollector()
    
    evidence_by_plugin = {
        "web_playwright": [
            EvidenceItem(
                evidence_type=EvidenceType.SCREENSHOT,
                timestamp=datetime.utcnow(),
                plugin_name="web_playwright",
                source="playwright",
                content={},
                confidence=0.9,
                severity="info",
            ),
            EvidenceItem(
                evidence_type=EvidenceType.ASSERTION_RESULT,
                timestamp=datetime.utcnow(),
                plugin_name="web_playwright",
                source="playwright",
                content={},
                confidence=1.0,
                severity="error",
            ),
        ],
    }
    
    summaries = collector.generate_summary("run-1", evidence_by_plugin)
    
    assert "web_playwright" in summaries
    summary = summaries["web_playwright"]
    assert summary.run_id == "run-1"
    assert summary.total_evidence_count == 2
    assert len(summary.critical_findings) == 1
