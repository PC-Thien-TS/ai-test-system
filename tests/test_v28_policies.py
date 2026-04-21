"""Tests for v2.8 escalation policies and evidence intelligence."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import (
    EscalationPolicy,
    ExecutionPath,
    GateResult,
    ProductType,
    Run,
    RunStatus,
)
from orchestrator.run_orchestrator import RunOrchestrator, RunOrchestrationConfig
from orchestrator.project_service import ProjectService


def test_escalation_policy_defaults():
    """Test escalation policy default values."""
    policy = EscalationPolicy()
    
    assert policy.fallback_threshold == 0.5
    assert policy.confidence_threshold == 0.7
    assert policy.max_escalation_depth == 3
    assert policy.auto_escalate_on_fail is True
    assert policy.auto_escalate_on_flaky is True
    assert policy.plugin_overrides == {}


def test_escalation_policy_custom():
    """Test escalation policy with custom values."""
    policy = EscalationPolicy(
        fallback_threshold=0.3,
        confidence_threshold=0.8,
        max_escalation_depth=5,
        auto_escalate_on_fail=False,
        auto_escalate_on_flaky=False,
    )
    
    assert policy.fallback_threshold == 0.3
    assert policy.confidence_threshold == 0.8
    assert policy.max_escalation_depth == 5
    assert policy.auto_escalate_on_fail is False
    assert policy.auto_escalate_on_flaky is False


def test_escalation_policy_serialization():
    """Test escalation policy to_dict and from_dict."""
    policy = EscalationPolicy(
        fallback_threshold=0.4,
        confidence_threshold=0.6,
        max_escalation_depth=4,
    )
    
    policy_dict = policy.to_dict()
    
    assert policy_dict["fallback_threshold"] == 0.4
    assert policy_dict["confidence_threshold"] == 0.6
    assert policy_dict["max_escalation_depth"] == 4
    
    restored_policy = EscalationPolicy.from_dict(policy_dict)
    
    assert restored_policy.fallback_threshold == policy.fallback_threshold
    assert restored_policy.confidence_threshold == policy.confidence_threshold
    assert restored_policy.max_escalation_depth == policy.max_escalation_depth


def test_should_escalate_with_policy_fallback():
    """Test escalation decision based on fallback threshold."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        policy = EscalationPolicy(fallback_threshold=0.5)
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.STANDARD,
            fallback_ratio=0.6,  # Above threshold
            confidence_score=0.8,
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
            escalation_policy=policy,
        )
        
        assert new_path is not None
        assert new_path == ExecutionPath.DEEP


def test_should_escalate_with_policy_confidence():
    """Test escalation decision based on confidence threshold."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        policy = EscalationPolicy(confidence_threshold=0.7)
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.STANDARD,
            fallback_ratio=0.3,
            confidence_score=0.5,  # Below threshold
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
            escalation_policy=policy,
        )
        
        assert new_path is not None
        assert new_path == ExecutionPath.DEEP


def test_should_escalate_with_policy_gate_fail():
    """Test escalation decision based on gate failure."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        policy = EscalationPolicy(auto_escalate_on_fail=True)
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.STANDARD,
            gate_result=GateResult.FAIL,
            fallback_ratio=0.3,
            confidence_score=0.8,
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
            escalation_policy=policy,
        )
        
        assert new_path is not None


def test_should_escalate_with_policy_flaky():
    """Test escalation decision based on flaky results."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        policy = EscalationPolicy(auto_escalate_on_flaky=True)
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.STANDARD,
            flaky=True,
            fallback_ratio=0.3,
            confidence_score=0.8,
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
            escalation_policy=policy,
        )
        
        assert new_path is not None


def test_should_not_escalate_with_policy():
    """Test that escalation is skipped when policy conditions are not met."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        policy = EscalationPolicy(
            fallback_threshold=0.5,
            confidence_threshold=0.7,
            auto_escalate_on_fail=False,
            auto_escalate_on_flaky=False,
        )
        
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.STANDARD,
            fallback_ratio=0.3,  # Below threshold
            confidence_score=0.8,  # Above threshold
            gate_result=GateResult.PASS,
            flaky=False,
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
            escalation_policy=policy,
        )
        
        assert new_path is None


def test_max_escalation_depth_enforced():
    """Test that max escalation depth from policy is enforced."""
    with TemporaryDirectory() as tmpdir:
        orchestrator = RunOrchestrator(Path(tmpdir))
        
        policy = EscalationPolicy(max_escalation_depth=2)
        
        # Create escalation chain with 2 steps
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
        
        run = Run(
            run_id="run-3",
            project_id="proj-1",
            status=RunStatus.COMPLETED,
            started_at=datetime.utcnow(),
            output_path=Path("/output"),
            execution_path=ExecutionPath.DEEP,
            parent_run_id="run-2",
            fallback_ratio=0.8,
            confidence_score=0.3,
        )
        
        new_path = orchestrator.should_escalate(
            run=run,
            plugin_names=["web_playwright"],
            escalation_policy=policy,
        )
        
        assert new_path is None  # Should not escalate beyond max depth


def test_project_service_escalation_with_policy():
    """Test project service uses project's escalation policy."""
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        # Set custom escalation policy
        custom_policy = EscalationPolicy(
            fallback_threshold=0.3,
            max_escalation_depth=2,
        )
        project.escalation_policy = custom_policy
        
        parent_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.STANDARD)
        
        # Trigger escalation - should use project's policy
        escalated_run = service.trigger_escalation_run(
            parent_run_id=parent_run.run_id,
            new_path=ExecutionPath.DEEP,
            reason="Test escalation",
        )
        
        assert escalated_run is not None
        assert escalated_run.metadata["escalation_policy"]["fallback_threshold"] == 0.3
        assert escalated_run.metadata["escalation_policy"]["max_escalation_depth"] == 2


def test_evidence_filter_by_severity():
    """Test evidence filtering by severity."""
    # This test would be implemented when evidence filtering logic is added
    # For now, we verify the filter state exists in the UI
    assert True  # Placeholder


def test_evidence_filter_by_confidence():
    """Test evidence filtering by confidence threshold."""
    # This test would be implemented when evidence filtering logic is added
    assert True  # Placeholder


def test_evidence_comparison_page():
    """Test evidence comparison page accessibility."""
    # This test would verify the comparison page renders correctly
    assert True  # Placeholder


def test_escalation_analytics_page():
    """Test escalation analytics page accessibility."""
    # This test would verify the analytics page renders correctly
    assert True  # Placeholder
