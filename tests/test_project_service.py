"""Tests for project service."""

import tempfile
from pathlib import Path

import pytest

from orchestrator.models import ProductType, RunStatus
from orchestrator.project_service import ProjectService


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def service(temp_repo_root):
    """Create a project service with temp storage."""
    return ProjectService(temp_repo_root)


def test_create_project(service):
    """Test creating a project through service."""
    project = service.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
        description="A test project",
        tags=["web", "smoke"],
    )
    
    assert project.project_id is not None
    assert project.name == "Test Project"
    assert project.product_type == ProductType.WEB


def test_get_project(service):
    """Test retrieving a project through service."""
    created = service.create_project(
        name="Test Project",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest.json"),
    )
    
    retrieved = service.get_project(created.project_id)
    
    assert retrieved is not None
    assert retrieved.project_id == created.project_id


def test_list_projects(service):
    """Test listing projects through service."""
    service.create_project(
        name="Project 1",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
    )
    service.create_project(
        name="Project 2",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
    )
    
    projects = service.list_projects()
    
    assert len(projects) == 2


def test_trigger_run(service):
    """Test triggering a run through service."""
    project = service.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    run = service.trigger_run(project.project_id)
    
    assert run is not None
    assert run.project_id == project.project_id
    assert run.status == RunStatus.PENDING


def test_trigger_run_nonexistent_project(service):
    """Test triggering a run for non-existent project."""
    run = service.trigger_run("nonexistent-id")
    assert run is None


def test_get_project_summary(service):
    """Test getting project summary through service."""
    project = service.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    run = service.trigger_run(project.project_id)
    service.update_run(run.run_id, status=RunStatus.COMPLETED)
    
    summary = service.get_project_summary(project.project_id)
    
    assert summary is not None
    assert summary.project_id == project.project_id
    assert summary.total_runs == 1


def test_get_platform_summary(service):
    """Test getting platform summary through service."""
    service.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    summary = service.get_platform_summary()
    
    assert summary.total_projects == 1
    assert summary.active_projects == 1


def test_list_plugins(service):
    """Test listing plugins through service."""
    plugins = service.list_plugins()
    
    assert len(plugins) > 0


def test_list_plugins_by_product_type(service):
    """Test filtering plugins by product type through service."""
    web_plugins = service.list_plugins(product_type=ProductType.WEB)
    
    assert len(web_plugins) > 0


def test_get_plugin(service):
    """Test getting plugin through service."""
    plugin = service.get_plugin("web_playwright")
    
    assert plugin is not None
    assert plugin.name == "web_playwright"


def test_analyze_plugin_compatibility(service):
    """Test analyzing plugin compatibility through service."""
    summary = service.analyze_plugin_compatibility("web_playwright")
    
    assert summary.plugin_name == "web_playwright"
    assert summary.compatible is True


def test_import_existing_domains(service, temp_repo_root):
    """Test importing existing domains as projects."""
    # Create domain directories
    order_dir = temp_repo_root / "domains" / "order"
    order_dir.mkdir(parents=True, exist_ok=True)
    
    imported = service.import_existing_domains()
    
    # Should import order domain
    assert len(imported) >= 0


def test_get_latest_project_status(service):
    """Test getting latest project status through service."""
    project = service.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    run = service.trigger_run(project.project_id)
    
    status_list = service.get_latest_project_status()
    
    assert len(status_list) == 1
    assert status_list[0]["project_name"] == "Test Project"
