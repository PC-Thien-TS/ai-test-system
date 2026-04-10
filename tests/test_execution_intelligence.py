"""Tests for execution intelligence engine."""

import pytest
from datetime import datetime
from pathlib import Path

from orchestrator.execution_intelligence import (
    EscalationReason,
    ExecutionIntelligenceEngine,
    ExecutionPath,
    ExecutionStrategy,
)
from orchestrator.models import ProductType, Run, RunStatus, SupportLevel


def test_choose_execution_path_smoke():
    """Test choosing smoke execution path for unhealthy projects."""
    engine = ExecutionIntelligenceEngine()
    
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
    
    strategy = engine.choose_execution_path(
        project_id="proj-1",
        product_type=ProductType.WEB,
        plugin_names=["web_playwright"],
        historical_runs=historical_runs,
    )
    
    assert strategy.path == ExecutionPath.SMOKE
    assert strategy.confidence_threshold == 0.3


def test_choose_execution_path_deep():
    """Test choosing deep execution path for high-depth plugins."""
    engine = ExecutionIntelligenceEngine()
    
    # Create healthy historical runs
    historical_runs = [
        Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            fallback_ratio=0.1,
            real_execution_ratio=0.9,
        )
    ]
    
    strategy = engine.choose_execution_path(
        project_id="proj-1",
        product_type=ProductType.API,
        plugin_names=["api_contract"],  # High depth plugin
        historical_runs=historical_runs,
    )
    
    assert strategy.path == ExecutionPath.DEEP
    assert strategy.enable_negative_paths is True
    assert strategy.enable_retry_rollback is True


def test_choose_execution_path_forced():
    """Test forcing a specific execution path."""
    engine = ExecutionIntelligenceEngine()
    
    strategy = engine.choose_execution_path(
        project_id="proj-1",
        product_type=ProductType.WEB,
        plugin_names=["web_playwright"],
        historical_runs=[],
        force_path=ExecutionPath.STANDARD,
    )
    
    assert strategy.path == ExecutionPath.STANDARD
    assert "Forced by user configuration" in strategy.reason


def test_should_escalate_high_fallback():
    """Test escalation due to high fallback ratio."""
    engine = ExecutionIntelligenceEngine()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        fallback_ratio=0.7,
        real_execution_ratio=0.3,
    )
    
    new_path = engine.should_escalate_path(
        current_path=ExecutionPath.STANDARD,
        run=run,
        plugin_names=["web_playwright"],
    )
    
    assert new_path == ExecutionPath.DEEP
    assert "escalation_reason" in run.metadata
    assert run.metadata["escalation_from"] == "standard"
    assert run.metadata["escalation_to"] == "deep"


def test_should_escalate_low_real_execution():
    """Test escalation due to low real execution ratio."""
    engine = ExecutionIntelligenceEngine()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        fallback_ratio=0.1,
        real_execution_ratio=0.2,
    )
    
    new_path = engine.should_escalate_path(
        current_path=ExecutionPath.STANDARD,
        run=run,
        plugin_names=["web_playwright"],
    )
    
    assert new_path == ExecutionPath.DEEP


def test_should_escalate_smoke_failure():
    """Test escalation from smoke to standard on failure."""
    engine = ExecutionIntelligenceEngine()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.FAILED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        fallback_ratio=0.0,
        real_execution_ratio=1.0,
    )
    
    new_path = engine.should_escalate_path(
        current_path=ExecutionPath.SMOKE,
        run=run,
        plugin_names=["web_playwright"],
    )
    
    assert new_path == ExecutionPath.STANDARD


def test_should_escalate_flaky_standard():
    """Test escalation from standard to deep on flakiness."""
    engine = ExecutionIntelligenceEngine()
    
    from orchestrator.models import GateResult
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        flaky=True,
        fallback_ratio=0.0,
        real_execution_ratio=1.0,
    )
    
    new_path = engine.should_escalate_path(
        current_path=ExecutionPath.STANDARD,
        run=run,
        plugin_names=["web_playwright"],
    )
    
    assert new_path == ExecutionPath.DEEP


def test_should_not_escalate_healthy():
    """Test that healthy runs don't escalate."""
    engine = ExecutionIntelligenceEngine()
    
    from orchestrator.models import GateResult
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        gate_result=GateResult.PASS,
        flaky=False,
        fallback_ratio=0.1,
        real_execution_ratio=0.9,
    )
    
    new_path = engine.should_escalate_path(
        current_path=ExecutionPath.STANDARD,
        run=run,
        plugin_names=["web_playwright"],
    )
    
    assert new_path is None


def test_escalation_history():
    """Test that escalation history is tracked."""
    engine = ExecutionIntelligenceEngine()
    
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        fallback_ratio=0.7,
        real_execution_ratio=0.3,
    )
    
    engine.should_escalate_path(
        current_path=ExecutionPath.STANDARD,
        run=run,
        plugin_names=["web_playwright"],
    )
    
    history = engine.get_escalation_history()
    assert len(history) == 1
    assert history[0].from_path == ExecutionPath.STANDARD
    assert history[0].to_path == ExecutionPath.DEEP
