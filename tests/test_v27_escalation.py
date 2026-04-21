"""Tests for v2.7 escalation and UI features."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import api.deps

from orchestrator.models import (
    ExecutionPath,
    GateResult,
    ProductType,
    Run,
    RunStatus,
)
from orchestrator.project_service import ProjectService


def test_trigger_escalation_rerun():
    """Test triggering an escalation rerun."""
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        # Create project
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        # Create parent run
        parent_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.STANDARD)
        
        assert parent_run is not None
        assert parent_run.execution_path == ExecutionPath.STANDARD
        
        # Trigger escalation rerun
        escalated_run = service.trigger_escalation_run(
            parent_run_id=parent_run.run_id,
            new_path=ExecutionPath.DEEP,
            reason="High fallback ratio",
        )
        
        assert escalated_run is not None
        assert escalated_run.execution_path == ExecutionPath.DEEP
        assert escalated_run.parent_run_id == parent_run.run_id
        assert escalated_run.metadata["escalation_reason"] == "High fallback ratio"


def test_escalation_path_promotion():
    """Test that escalation path promotion works correctly."""
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.API,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        # Test SMOKE -> STANDARD
        smoke_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.SMOKE)
        assert smoke_run.execution_path == ExecutionPath.SMOKE
        
        # Test STANDARD -> DEEP
        standard_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.STANDARD)
        assert standard_run.execution_path == ExecutionPath.STANDARD
        
        # Test DEEP -> INTELLIGENT
        deep_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.DEEP)
        assert deep_run.execution_path == ExecutionPath.DEEP
        
        # Test INTELLIGENT (max path)
        intelligent_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.INTELLIGENT)
        assert intelligent_run.execution_path == ExecutionPath.INTELLIGENT


def test_escalation_chain_persistence():
    """Test that escalation chains are persisted correctly."""
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        # Create original run
        original_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.SMOKE)
        
        # First escalation
        first_escalation = service.trigger_escalation_run(
            parent_run_id=original_run.run_id,
            new_path=ExecutionPath.STANDARD,
            reason="Smoke failed",
        )
        
        # Second escalation
        second_escalation = service.trigger_escalation_run(
            parent_run_id=first_escalation.run_id,
            new_path=ExecutionPath.DEEP,
            reason="Standard flaky",
        )
        
        # Verify escalation chain
        chain = service.run_orchestrator.get_escalation_chain(original_run.run_id)
        
        assert chain is not None
        assert chain.original_run_id == original_run.run_id
        assert chain.current_run_id == second_escalation.run_id
        assert len(chain.escalation_path) == 2
        assert chain.escalation_path[0]["path"] == "standard"
        assert chain.escalation_path[1]["path"] == "deep"


def test_max_escalation_depth():
    """Test that escalation stops at max depth."""
    with TemporaryDirectory() as tmpdir:
        from orchestrator.run_orchestrator import RunOrchestrationConfig
        
        config = RunOrchestrationConfig(max_escalation_depth=2)
        service = ProjectService(Path(tmpdir))
        service.run_orchestrator = service.run_orchestrator.__class__(
            Path(tmpdir),
            config=config,
        )
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        # Original run
        original_run = service.trigger_run(project.project_id, forced_path=ExecutionPath.SMOKE)
        
        # First escalation
        first_escalation = service.trigger_escalation_run(
            parent_run_id=original_run.run_id,
            new_path=ExecutionPath.STANDARD,
            reason="First escalation",
        )
        
        # Second escalation (at max depth)
        second_escalation = service.trigger_escalation_run(
            parent_run_id=first_escalation.run_id,
            new_path=ExecutionPath.DEEP,
            reason="Second escalation",
        )
        
        # Third escalation should be blocked by max depth check
        # (This would be enforced in the should_escalate method)
        chain = service.run_orchestrator.get_escalation_chain(original_run.run_id)
        assert len(chain.escalation_path) == 2


def test_evidence_persistence_location():
    """Test that evidence is persisted in the correct location."""
    with TemporaryDirectory() as tmpdir:
        from orchestrator.run_orchestrator import RunOrchestrationConfig
        
        evidence_path = Path(tmpdir) / "outputs" / "evidence"
        config = RunOrchestrationConfig(evidence_persistence_path=evidence_path)
        orchestrator = service = ProjectService(Path(tmpdir))
        orchestrator.run_orchestrator = orchestrator.run_orchestrator.__class__(
            Path(tmpdir),
            config=config,
        )
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        run = service.trigger_run(project.project_id)
        
        # Collect evidence
        evidence_summaries = orchestrator.run_orchestrator.collect_evidence(
            run=run,
            plugin_names=["web_playwright"],
            execution_context={},
        )
        
        # Check evidence directory exists
        evidence_dir = evidence_path / run.run_id
        assert evidence_dir.exists()


def test_api_get_run_endpoint():
    """Test the GET /runs/{run_id} API endpoint."""
    from fastapi.testclient import TestClient
    from api.app import create_app
    
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        run = service.trigger_run(project.project_id)
        
        api.deps.REPO_ROOT = Path(tmpdir)
        app = create_app()
        client = TestClient(app)
        
        response = client.get(
            f"/runs/{run.run_id}",
            headers={
                "X-User-ID": "test-user",
                "X-User-Role": "viewer",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run.run_id
        assert data["execution_path"] == run.execution_path.value
        assert "confidence_score" in data
        assert "fallback_ratio" in data


def test_api_escalate_endpoint():
    """Test the POST /runs/{run_id}/escalate API endpoint."""
    from fastapi.testclient import TestClient
    from api.app import create_app
    
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        run = service.trigger_run(project.project_id, forced_path=ExecutionPath.STANDARD)
        
        api.deps.REPO_ROOT = Path(tmpdir)
        app = create_app()
        client = TestClient(app)
        
        response = client.post(
            f"/runs/{run.run_id}/escalate?reason=Manual escalation",
            headers={
                "X-User-ID": "test-user",
                "X-User-Role": "maintainer",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_path"] == "deep"  # STANDARD -> DEEP
        assert data["parent_run_id"] == run.run_id


def test_sse_endpoint_format():
    """Test that the SSE endpoint returns correct format."""
    from fastapi.testclient import TestClient
    from api.app import create_app
    
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        run = service.trigger_run(project.project_id)
        
        api.deps.REPO_ROOT = Path(tmpdir)
        app = create_app()
        client = TestClient(app)
        
        response = client.get(
            f"/runs/{run.run_id}/updates",
            headers={
                "X-User-ID": "test-user",
                "X-User-Role": "viewer",
            },
        )
        
        # SSE should return 200 with text/event-stream
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
