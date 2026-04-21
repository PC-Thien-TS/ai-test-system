"""Tests for run registry."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from orchestrator.models import GateResult, RunStatus
from orchestrator.run_registry import RunRegistry


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_storage):
    """Create a run registry with temp storage."""
    return RunRegistry(temp_storage)


def test_create_run(registry):
    """Test creating a run."""
    run = registry.create_run(
        project_id="test-project-123",
        output_path=Path("/test/output"),
    )
    
    assert run.run_id is not None
    assert run.project_id == "test-project-123"
    assert run.status == RunStatus.PENDING


def test_get_run(registry):
    """Test retrieving a run."""
    created = registry.create_run(
        project_id="test-project-123",
        output_path=Path("/test/output"),
    )
    
    retrieved = registry.get_run(created.run_id)
    
    assert retrieved is not None
    assert retrieved.run_id == created.run_id
    assert retrieved.project_id == created.project_id


def test_list_runs(registry):
    """Test listing runs."""
    registry.create_run(
        project_id="project-1",
        output_path=Path("/test/output1"),
    )
    registry.create_run(
        project_id="project-2",
        output_path=Path("/test/output2"),
    )
    
    runs = registry.list_runs()
    
    assert len(runs) == 2


def test_update_run(registry):
    """Test updating a run."""
    created = registry.create_run(
        project_id="test-project",
        output_path=Path("/test/output"),
    )
    
    updated = registry.update_run(
        created.run_id,
        status=RunStatus.COMPLETED,
        gate_result=GateResult.PASS,
        flaky=False,
    )
    
    assert updated is not None
    assert updated.status == RunStatus.COMPLETED
    assert updated.gate_result == GateResult.PASS


def test_list_runs_by_project(registry):
    """Test listing runs by project."""
    registry.create_run(
        project_id="project-1",
        output_path=Path("/test/output1"),
    )
    registry.create_run(
        project_id="project-1",
        output_path=Path("/test/output2"),
    )
    registry.create_run(
        project_id="project-2",
        output_path=Path("/test/output3"),
    )
    
    project1_runs = registry.list_runs_by_project("project-1")
    
    assert len(project1_runs) == 2
    for run in project1_runs:
        assert run.project_id == "project-1"


def test_get_latest_run(registry):
    """Test getting the latest run for a project."""
    registry.create_run(
        project_id="test-project",
        output_path=Path("/test/output1"),
    )
    latest = registry.create_run(
        project_id="test-project",
        output_path=Path("/test/output2"),
    )
    
    retrieved = registry.get_latest_run("test-project")
    
    assert retrieved is not None
    assert retrieved.run_id == latest.run_id


def test_get_run_statistics(registry):
    """Test getting run statistics."""
    project_id = "test-project"
    
    # Create some runs
    run1 = registry.create_run(project_id, Path("/test/output1"))
    registry.update_run(run1.run_id, status=RunStatus.COMPLETED, gate_result=GateResult.PASS)
    
    run2 = registry.create_run(project_id, Path("/test/output2"))
    registry.update_run(run2.run_id, status=RunStatus.FAILED)
    
    run3 = registry.create_run(project_id, Path("/test/output3"))
    registry.update_run(run3.run_id, status=RunStatus.COMPLETED, gate_result=GateResult.PASS, flaky=True)
    
    stats = registry.get_run_statistics(project_id)
    
    assert stats["total"] == 3
    assert stats["completed"] == 2
    assert stats["failed"] == 1
    assert stats["flaky"] == 1


def test_persistence(registry, temp_storage):
    """Test that data persists across registry instances."""
    created = registry.create_run(
        project_id="test-project",
        output_path=Path("/test/output"),
    )
    
    # Create a new registry instance with same storage
    new_registry = RunRegistry(temp_storage)
    
    retrieved = new_registry.get_run(created.run_id)
    
    assert retrieved is not None
    assert retrieved.project_id == created.project_id
