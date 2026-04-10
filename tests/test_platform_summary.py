"""Tests for platform summary generator."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from orchestrator.models import GateResult, ProductType, RunStatus
from orchestrator.platform_summary import PlatformSummaryGenerator
from orchestrator.project_registry import ProjectRegistry
from orchestrator.run_registry import RunRegistry


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registries(temp_storage):
    """Create project and run registries with temp storage."""
    project_registry = ProjectRegistry(temp_storage / "projects")
    run_registry = RunRegistry(temp_storage / "runs")
    return project_registry, run_registry


@pytest.fixture
def generator(registries):
    """Create a platform summary generator."""
    project_registry, run_registry = registries
    return PlatformSummaryGenerator(project_registry, run_registry)


def test_generate_platform_summary_empty(generator):
    """Test generating summary with no projects."""
    summary = generator.generate_platform_summary()
    
    assert summary.total_projects == 0
    assert summary.active_projects == 0
    assert summary.total_runs == 0


def test_generate_platform_summary_with_data(generator, registries):
    """Test generating summary with projects and runs."""
    project_registry, run_registry = registries
    
    # Create a project
    project = project_registry.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    # Create a run
    run = run_registry.create_run(
        project_id=project.project_id,
        output_path=Path("/test/output"),
    )
    run_registry.update_run(run.run_id, status=RunStatus.COMPLETED, gate_result=GateResult.PASS)
    
    summary = generator.generate_platform_summary()
    
    assert summary.total_projects == 1
    assert summary.active_projects == 1
    assert summary.total_runs == 1


def test_generate_project_summary(generator, registries):
    """Test generating summary for a specific project."""
    project_registry, run_registry = registries
    
    project = project_registry.create_project(
        name="Test Project",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest.json"),
    )
    
    # Create some runs
    run1 = run_registry.create_run(project.project_id, Path("/test/output1"))
    run_registry.update_run(run1.run_id, status=RunStatus.COMPLETED, gate_result=GateResult.PASS)
    
    run2 = run_registry.create_run(project.project_id, Path("/test/output2"))
    run_registry.update_run(run2.run_id, status=RunStatus.FAILED)
    
    summary = generator.generate_project_summary(project.project_id)
    
    assert summary is not None
    assert summary.project_id == project.project_id
    assert summary.project_name == "Test Project"
    assert summary.total_runs == 2
    assert summary.passed_runs == 1
    assert summary.failed_runs == 1


def test_generate_project_summary_not_found(generator):
    """Test generating summary for non-existent project."""
    summary = generator.generate_project_summary("nonexistent-id")
    assert summary is None


def test_generate_all_project_summaries(generator, registries):
    """Test generating summaries for all projects."""
    project_registry, run_registry = registries
    
    project1 = project_registry.create_project(
        name="Project 1",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
    )
    
    project2 = project_registry.create_project(
        name="Project 2",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
    )
    
    summaries = generator.generate_all_project_summaries()
    
    assert len(summaries) == 2
    assert any(s.project_name == "Project 1" for s in summaries)
    assert any(s.project_name == "Project 2" for s in summaries)


def test_get_latest_project_status(generator, registries):
    """Test getting latest status for all projects."""
    project_registry, run_registry = registries
    
    project = project_registry.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    run = run_registry.create_run(project.project_id, Path("/test/output"))
    run_registry.update_run(run.run_id, status=RunStatus.COMPLETED)
    
    status_list = generator.get_latest_project_status()
    
    assert len(status_list) == 1
    assert status_list[0]["project_name"] == "Test Project"
    assert status_list[0]["latest_status"] == "completed"


def test_generate_trend_data(generator, registries):
    """Test generating trend data for a project."""
    project_registry, run_registry = registries
    
    project = project_registry.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    # Create multiple runs
    for i in range(3):
        run = run_registry.create_run(project.project_id, Path(f"/test/output{i}"))
        run_registry.update_run(run.run_id, status=RunStatus.COMPLETED)
    
    trends = generator.generate_trend_data(project.project_id)
    
    assert len(trends) == 3
    assert all("run_id" in t for t in trends)
    assert all("timestamp" in t for t in trends)
    assert all("status" in t for t in trends)


def test_get_flaky_projects(generator, registries):
    """Test getting projects with flaky runs."""
    project_registry, run_registry = registries
    
    project1 = project_registry.create_project(
        name="Flaky Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
    )
    
    project2 = project_registry.create_project(
        name="Stable Project",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
    )
    
    # Add flaky run to project1
    run1 = run_registry.create_run(project1.project_id, Path("/test/output1"))
    run_registry.update_run(run1.run_id, status=RunStatus.COMPLETED, flaky=True)
    
    # Add stable run to project2
    run2 = run_registry.create_run(project2.project_id, Path("/test/output2"))
    run_registry.update_run(run2.run_id, status=RunStatus.COMPLETED, flaky=False)
    
    flaky_projects = generator.get_flaky_projects()
    
    assert len(flaky_projects) == 1
    assert flaky_projects[0].project_name == "Flaky Project"


def test_get_failing_projects(generator, registries):
    """Test getting projects with failing runs."""
    project_registry, run_registry = registries
    
    project1 = project_registry.create_project(
        name="Failing Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
    )
    
    project2 = project_registry.create_project(
        name="Passing Project",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
    )
    
    # Add failed run to project1
    run1 = run_registry.create_run(project1.project_id, Path("/test/output1"))
    run_registry.update_run(run1.run_id, status=RunStatus.FAILED)
    
    # Add passing run to project2
    run2 = run_registry.create_run(project2.project_id, Path("/test/output2"))
    run_registry.update_run(run2.run_id, status=RunStatus.COMPLETED, gate_result=GateResult.PASS)
    
    failing_projects = generator.get_failing_projects()
    
    assert len(failing_projects) == 1
    assert failing_projects[0].project_name == "Failing Project"
