"""Tests for run orchestrator integration."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import (
    ExecutionPath,
    GateResult,
    ProductType,
    Run,
    RunStatus,
)
from orchestrator.run_orchestrator import RunOrchestrator, RunOrchestrationConfig


def test_plan_run_with_intelligence():
    """Test planning a run with intelligent path selection."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        # Create historical runs
        historical_runs = [
            Run(
                run_id="run-1",
                project_id="proj-1",
                status=RunStatus.FAILED,
                started_at=datetime.utcnow(),
                output_path=Path("/output"),
                fallback_ratio=0.8,
                real_execution_ratio=0.2,
            )
        ]
        
        strategy = orchestrator.plan_run(
            project_id="proj-1",
            product_type=ProductType.WEB,
            plugin_names=["web_playwright"],
            historical_runs=historical_runs,
        )
        
        assert strategy.path.value in ["smoke", "standard", "deep", "intelligent"]
        assert strategy.confidence_threshold >= 0.0
        assert strategy.confidence_threshold <= 1.0


def test_plan_run_forced_path():
    """Test planning a run with forced execution path."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        strategy = orchestrator.plan_run(
            project_id="proj-1",
            product_type=ProductType.API,
            plugin_names=["api_contract"],
            historical_runs=[],
            forced_path=ExecutionPath.DEEP,
        )
        
        assert strategy.path.value == "deep"


def test_should_escalate_high_fallback():
    """Test escalation detection for high fallback ratio."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.STANDARD,
            fallback_ratio=0.7,
            real_execution_ratio=0.3,
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
        )
        
        assert new_path == ExecutionPath.DEEP


def test_should_escalate_max_depth():
    """Test that escalation stops at max depth."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(
            Path(tmpdir),
            config=RunOrchestrationConfig(max_escalation_depth=2),
        )
        
        # Create escalation chain with max depth
        run = Run(
            run_id="run-3",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.DEEP,
            parent_run_id="run-2",
            fallback_ratio=0.7,
            real_execution_ratio=0.3,
        )
        
        orchestrator.create_escalation_chain(
            original_run_id="run-1",
            current_run_id="run-2",
            path=ExecutionPath.STANDARD,
            reason="First escalation",
        )
        orchestrator.create_escalation_chain(
            original_run_id="run-1",
            current_run_id="run-3",
            path=ExecutionPath.DEEP,
            reason="Second escalation",
        )
        
        # Should not escalate further
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
        )
        
        assert new_path is None


def test_create_escalation_chain():
    """Test creating and tracking escalation chains."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        chain = orchestrator.create_escalation_chain(
            original_run_id="run-1",
            current_run_id="run-2",
            path=ExecutionPath.STANDARD,
            reason="Smoke failed",
        )
        
        assert chain.original_run_id == "run-1"
        assert chain.current_run_id == "run-2"
        assert len(chain.escalation_path) == 1
        assert chain.escalation_path[0]["path"] == "standard"


def test_get_escalation_chain():
    """Test retrieving escalation chains."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        orchestrator.create_escalation_chain(
            original_run_id="run-1",
            current_run_id="run-2",
            path=ExecutionPath.STANDARD,
            reason="First escalation",
        )
        
        chain = orchestrator.get_escalation_chain("run-1")
        
        assert chain is not None
        assert chain.original_run_id == "run-1"
        
        # Also test retrieval by current run ID
        chain_by_current = orchestrator.get_escalation_chain("run-2")
        assert chain_by_current is not None


def test_collect_evidence():
    """Test evidence collection."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path(tmpdir),
        )
        
        execution_context = {
            "screenshot_count": 2,
            "url": "https://example.com",
            "network_requests": [],
            "assertions": [],
        }
        
        summaries = orchestrator.collect_evidence(
            run=run,
            plugin_names=["web_playwright"],
            execution_context=execution_context,
        )
        
        assert "web_playwright" in summaries


def test_persist_evidence():
    """Test evidence persistence to disk."""
    with TemporaryDirectory() as tmpdir:
        config = RunOrchestrationConfig(evidence_persistence_path=Path(tmpdir) / "evidence")
        orchestrator = RunOrchestrator(Path(tmpdir), config=config)
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path(tmpdir),
        )
        
        evidence_by_plugin = {
            "web_playwright": [],
        }
        summaries = {}
        
        orchestrator._persist_evidence(run.run_id, evidence_by_plugin, summaries)
        
        # Check that evidence directory was created
        evidence_dir = Path(tmpdir) / "evidence" / "run-1"
        assert evidence_dir.exists()


def test_calculate_confidence():
    """Test confidence score calculation."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path(tmpdir),
            gate_result=GateResult.PASS,
            fallback_ratio=0.1,
            real_execution_ratio=0.9,
        )
        
        aggregate_score, plugin_scores = orchestrator.calculate_confidence(
            plugin_names=["web_playwright"],
            run=run,
            evidence_summaries={},
            historical_runs=[],
        )
        
        assert 0.0 <= aggregate_score <= 1.0
        assert "web_playwright" in plugin_scores


def test_escalation_chain_persistence():
    """Test that escalation chains persist across orchestrator instances."""
    with TemporaryDirectory() as tmpdir:
        # Create first orchestrator and add chain
        orchestrator1 = RunOrchestrator(Path(tmpdir))
        orchestrator1.create_escalation_chain(
            original_run_id="run-1",
            current_run_id="run-2",
            path=ExecutionPath.STANDARD,
            reason="Test escalation",
        )
        
        # Create second orchestrator (should load existing chains)
        orchestrator2 = RunOrchestrator(Path(tmpdir))
        chain = orchestrator2.get_escalation_chain("run-1")
        
        assert chain is not None
        assert chain.original_run_id == "run-1"
