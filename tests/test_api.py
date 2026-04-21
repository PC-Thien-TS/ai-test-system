"""Tests for FastAPI endpoints."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from orchestrator.models import ProductType


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def client(temp_repo_root):
    """Create a test client with temp storage."""
    import sys
    sys.modules['api.deps'].REPO_ROOT = temp_repo_root
    
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.1.0"


def test_list_projects_empty(client):
    """Test listing projects when none exist."""
    response = client.get("/projects/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_create_project(client):
    """Test creating a project."""
    response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "product_type": "web",
            "manifest_path": "/test/manifest.json",
            "description": "A test project",
            "tags": ["web", "smoke"],
        },
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["product_type"] == "web"
    assert data["active"] is True
    assert "project_id" in data


def test_get_project(client):
    """Test getting a specific project."""
    # First create a project
    create_response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "product_type": "api",
            "manifest_path": "/test/manifest.json",
        },
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )
    project_id = create_response.json()["project_id"]
    
    # Then get it
    response = client.get(f"/projects/{project_id}", headers={"X-User-ID": "test-user"})
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["name"] == "Test Project"


def test_get_project_not_found(client):
    """Test getting a non-existent project."""
    response = client.get("/projects/nonexistent-id")
    assert response.status_code == 404


def test_trigger_run(client):
    """Test triggering a run for a project."""
    # First create a project
    create_response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "product_type": "web",
            "manifest_path": "/test/manifest.json",
        },
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )
    project_id = create_response.json()["project_id"]
    
    # Then trigger a run
    response = client.post(f"/projects/{project_id}/run", headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"})
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["status"] == "pending"
    assert "run_id" in data


def test_list_runs_empty(client):
    """Test listing runs for a project with no runs."""
    # Create a project
    create_response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "product_type": "web",
            "manifest_path": "/test/manifest.json",
        },
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )
    project_id = create_response.json()["project_id"]
    
    # List runs
    response = client.get(f"/projects/{project_id}/runs", headers={"X-User-ID": "test-user"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_plugins(client):
    """Test listing plugins."""
    response = client.get("/plugins/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_plugin(client):
    """Test getting a specific plugin."""
    response = client.get("/plugins/web_playwright")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "web_playwright"
    assert "capabilities" in data


def test_get_plugin_not_found(client):
    """Test getting a non-existent plugin."""
    response = client.get("/plugins/nonexistent_plugin")
    assert response.status_code == 404


def test_plugin_compatibility(client):
    """Test getting plugin compatibility."""
    response = client.get("/plugins/web_playwright/compatibility")
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_name"] == "web_playwright"
    assert "compatible" in data
    assert "support_level" in data


def test_platform_summary(client):
    """Test getting platform summary."""
    response = client.get("/platform/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_projects" in data
    assert "active_projects" in data
    assert "total_runs" in data


def test_latest_project_status(client):
    """Test getting latest project status."""
    response = client.get("/platform/projects/latest")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_workspace_filtering(client):
    """Test workspace-based filtering."""
    # Create project in workspace-1
    response1 = client.post(
        "/projects/",
        json={
            "name": "Project 1",
            "product_type": "web",
            "manifest_path": "/test/manifest1.json",
            "workspace_id": "workspace-1",
        },
        headers={"X-User-ID": "user1", "X-Workspace-ID": "workspace-1", "X-User-Role": "maintainer"},
    )
    assert response1.status_code == 201
    
    # Create project in workspace-2
    response2 = client.post(
        "/projects/",
        json={
            "name": "Project 2",
            "product_type": "api",
            "manifest_path": "/test/manifest2.json",
            "workspace_id": "workspace-2",
        },
        headers={"X-User-ID": "user2", "X-Workspace-ID": "workspace-2", "X-User-Role": "maintainer"},
    )
    assert response2.status_code == 201
    
    # List projects for workspace-1
    response = client.get(
        "/projects/",
        headers={"X-User-ID": "user1", "X-Workspace-ID": "workspace-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["workspace_id"] == "workspace-1"
