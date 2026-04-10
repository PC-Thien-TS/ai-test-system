"""Tests for project registry."""

import tempfile
from pathlib import Path

import pytest

from orchestrator.models import ProductType
from orchestrator.project_registry import ProjectRegistry


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_storage):
    """Create a project registry with temp storage."""
    return ProjectRegistry(temp_storage)


def test_create_project(registry):
    """Test creating a project."""
    project = registry.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
        description="A test project",
        tags=["web", "smoke"],
    )
    
    assert project.project_id is not None
    assert project.name == "Test Project"
    assert project.product_type == ProductType.WEB
    assert project.active is True


def test_get_project(registry):
    """Test retrieving a project."""
    created = registry.create_project(
        name="Test Project",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest.json"),
    )
    
    retrieved = registry.get_project(created.project_id)
    
    assert retrieved is not None
    assert retrieved.project_id == created.project_id
    assert retrieved.name == created.name


def test_list_projects(registry):
    """Test listing projects."""
    registry.create_project(
        name="Project 1",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
    )
    registry.create_project(
        name="Project 2",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
    )
    
    projects = registry.list_projects()
    
    assert len(projects) == 2


def test_update_project(registry):
    """Test updating a project."""
    created = registry.create_project(
        name="Original Name",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    updated = registry.update_project(
        created.project_id,
        name="Updated Name",
        description="Updated description",
    )
    
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"


def test_delete_project(registry):
    """Test soft-deleting a project."""
    created = registry.create_project(
        name="Test Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    result = registry.delete_project(created.project_id)
    assert result is True
    
    project = registry.get_project(created.project_id)
    assert project is not None
    assert project.active is False


def test_list_projects_active_only(registry):
    """Test listing only active projects."""
    registry.create_project(
        name="Active Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
    )
    deleted = registry.create_project(
        name="Inactive Project",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
    )
    registry.delete_project(deleted.project_id)
    
    active_projects = registry.list_projects(active_only=True)
    all_projects = registry.list_projects(active_only=False)
    
    assert len(active_projects) == 1
    assert len(all_projects) == 2


def test_workspace_filtering(registry):
    """Test filtering by workspace ID."""
    registry.create_project(
        name="Project 1",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest1.json"),
        workspace_id="workspace-1",
    )
    registry.create_project(
        name="Project 2",
        product_type=ProductType.API,
        manifest_path=Path("/test/manifest2.json"),
        workspace_id="workspace-2",
    )
    
    workspace1_projects = registry.list_projects(workspace_id="workspace-1")
    
    assert len(workspace1_projects) == 1
    assert workspace1_projects[0].workspace_id == "workspace-1"


def test_persistence(registry, temp_storage):
    """Test that data persists across registry instances."""
    created = registry.create_project(
        name="Persistent Project",
        product_type=ProductType.WEB,
        manifest_path=Path("/test/manifest.json"),
    )
    
    # Create a new registry instance with same storage
    new_registry = ProjectRegistry(temp_storage)
    
    retrieved = new_registry.get_project(created.project_id)
    
    assert retrieved is not None
    assert retrieved.name == "Persistent Project"
