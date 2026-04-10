"""Tests for orchestrator models."""

from datetime import datetime
from pathlib import Path

import pytest

from orchestrator.models import (
    CompatibilitySummary,
    GateResult,
    PluginMetadata,
    ProductType,
    Project,
    ProjectSummary,
    Run,
    RunStatus,
    SupportLevel,
)


def test_project_serialization():
    """Test Project to_dict and from_dict."""
    project = Project(
        project_id="test-123",
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
        description="A test project",
        tags=["web", "smoke"],
    )
    
    data = project.to_dict()
    assert data["project_id"] == "test-123"
    assert data["name"] == "Test Project"
    assert data["product_type"] == "web"
    assert data["tags"] == ["web", "smoke"]
    
    restored = Project.from_dict(data)
    assert restored.project_id == project.project_id
    assert restored.name == project.name
    assert restored.product_type == project.product_type


def test_run_serialization():
    """Test Run to_dict and from_dict."""
    run = Run(
        run_id="run-456",
        project_id="test-123",
        status=RunStatus.RUNNING,
        started_at=datetime.utcnow(),
        output_path=Path("/test/output"),
        gate_result=GateResult.PASS,
        flaky=False,
    )
    
    data = run.to_dict()
    assert data["run_id"] == "run-456"
    assert data["status"] == "running"
    assert data["gate_result"] == "pass"
    
    restored = Run.from_dict(data)
    assert restored.run_id == run.run_id
    assert restored.status == run.status
    assert restored.gate_result == run.gate_result


def test_project_summary():
    """Test ProjectSummary."""
    summary = ProjectSummary(
        project_id="test-123",
        project_name="Test Project",
        product_type=ProductType.API,
        latest_run_id="run-456",
        latest_status=RunStatus.COMPLETED,
        gate_result=GateResult.PASS,
        total_runs=10,
        passed_runs=8,
        failed_runs=2,
        flaky_runs=1,
    )
    
    data = summary.to_dict()
    assert data["project_id"] == "test-123"
    assert data["total_runs"] == 10
    assert data["passed_runs"] == 8
    assert data["failed_runs"] == 2


def test_compatibility_summary():
    """Test CompatibilitySummary."""
    summary = CompatibilitySummary(
        plugin_name="web_playwright",
        platform_version="2.1.0",
        compatible=True,
        support_level=SupportLevel.FULL,
        notes=["All dependencies available"],
        blockers=[],
    )
    
    data = summary.to_dict()
    assert data["plugin_name"] == "web_playwright"
    assert data["compatible"] is True
    assert data["support_level"] == "full"


def test_plugin_metadata():
    """Test PluginMetadata."""
    plugin = PluginMetadata(
        name="test_plugin",
        version="1.0.0",
        description="Test plugin",
        product_types=[ProductType.WEB, ProductType.API],
        capabilities=["test", "validate"],
        support_level=SupportLevel.USABLE,
        dependencies=["pytest"],
        min_platform_version="2.0.0",
        execution_depth_score=0.75,
        evidence_richness_score=0.8,
        confidence_score=0.77,
    )
    
    assert plugin.name == "test_plugin"
    assert ProductType.WEB in plugin.product_types
    assert "test" in plugin.capabilities
    assert plugin.execution_depth_score == 0.75
    assert plugin.evidence_richness_score == 0.8
    assert plugin.confidence_score == 0.77


def test_run_execution_depth_metrics():
    """Test Run execution depth metrics."""
    run = Run(
        run_id="run-456",
        project_id="test-123",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/test/output"),
        gate_result=GateResult.PASS,
        flaky=False,
        fallback_ratio=0.1,
        real_execution_ratio=0.9,
    )
    
    assert 0.0 <= run.fallback_ratio <= 1.0
    assert 0.0 <= run.real_execution_ratio <= 1.0
    assert run.fallback_ratio + run.real_execution_ratio <= 1.0
    
    data = run.to_dict()
    assert "fallback_ratio" in data
    assert "real_execution_ratio" in data
    assert data["fallback_ratio"] == 0.1
    assert data["real_execution_ratio"] == 0.9


def test_project_summary_execution_depth_metrics():
    """Test ProjectSummary execution depth metrics."""
    summary = ProjectSummary(
        project_id="test-123",
        project_name="Test Project",
        product_type=ProductType.API,
        latest_run_id="run-456",
        latest_status=RunStatus.COMPLETED,
        gate_result=GateResult.PASS,
        total_runs=10,
        passed_runs=8,
        failed_runs=2,
        flaky_runs=1,
        avg_execution_depth_score=0.85,
        avg_evidence_richness_score=0.88,
        avg_confidence_score=0.86,
        avg_fallback_ratio=0.15,
        avg_real_execution_ratio=0.85,
    )
    
    data = summary.to_dict()
    assert "avg_execution_depth_score" in data
    assert "avg_evidence_richness_score" in data
    assert "avg_confidence_score" in data
    assert "avg_fallback_ratio" in data
    assert "avg_real_execution_ratio" in data
