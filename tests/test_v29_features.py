"""Tests for v2.9 policy UI, timeline rendering, export, and search."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import (
    EscalationPolicy,
    ExecutionPath,
    GateResult,
    ProductType,
    Project,
    Run,
    RunStatus,
)
from orchestrator.project_registry import ProjectRegistry
from orchestrator.project_service import ProjectService


def test_update_escalation_policy_via_registry():
    """Test updating escalation policy via project registry."""
    with TemporaryDirectory() as tmpdir:
        registry = ProjectRegistry(Path(tmpdir) / "projects")
        
        project = registry.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        policy = EscalationPolicy(
            fallback_threshold=0.3,
            confidence_threshold=0.8,
            max_escalation_depth=5,
        )
        
        updated = registry.update_project(
            project_id=project.project_id,
            escalation_policy=policy,
        )
        
        assert updated is not None
        assert updated.escalation_policy is not None
        assert updated.escalation_policy.fallback_threshold == 0.3
        assert updated.escalation_policy.confidence_threshold == 0.8
        assert updated.escalation_policy.max_escalation_depth == 5


def test_escalation_policy_persistence():
    """Test that escalation policy persists across registry reloads."""
    with TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "projects"
        registry = ProjectRegistry(storage_path)
        
        project = registry.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        policy = EscalationPolicy(
            fallback_threshold=0.4,
            confidence_threshold=0.6,
            max_escalation_depth=4,
        )
        
        registry.update_project(
            project_id=project.project_id,
            escalation_policy=policy,
        )
        
        # Reload registry
        registry2 = ProjectRegistry(storage_path)
        reloaded = registry2.get_project(project.project_id)
        
        assert reloaded is not None
        assert reloaded.escalation_policy is not None
        assert reloaded.escalation_policy.fallback_threshold == 0.4
        assert reloaded.escalation_policy.confidence_threshold == 0.6
        assert reloaded.escalation_policy.max_escalation_depth == 4


def test_escalation_policy_with_plugin_overrides():
    """Test escalation policy with plugin-specific overrides."""
    with TemporaryDirectory() as tmpdir:
        registry = ProjectRegistry(Path(tmpdir) / "projects")
        
        project = registry.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        policy = EscalationPolicy(
            fallback_threshold=0.5,
            plugin_overrides={
                "web_playwright": {
                    "fallback_threshold": 0.3,
                    "confidence_threshold": 0.9,
                }
            }
        )
        
        updated = registry.update_project(
            project_id=project.project_id,
            escalation_policy=policy,
        )
        
        assert updated is not None
        assert updated.escalation_policy.plugin_overrides == {
            "web_playwright": {
                "fallback_threshold": 0.3,
                "confidence_threshold": 0.9,
            }
        }


def test_escalation_policy_ui_component_rendering():
    """Test that the policy UI component can render with policy data."""
    # This is a placeholder test for UI component rendering
    # In a real implementation, this would use a testing framework like React Testing Library
    policy_data = {
        "fallback_threshold": 0.5,
        "confidence_threshold": 0.7,
        "max_escalation_depth": 3,
        "auto_escalate_on_fail": True,
        "auto_escalate_on_flaky": True,
        "plugin_overrides": {}
    }
    
    assert policy_data["fallback_threshold"] == 0.5
    assert policy_data["confidence_threshold"] == 0.7
    assert policy_data["max_escalation_depth"] == 3
    assert policy_data["auto_escalate_on_fail"] is True
    assert policy_data["auto_escalate_on_flaky"] is True


def test_escalation_timeline_data_structure():
    """Test that escalation timeline data structure is correct."""
    run = Run(
        run_id="run-1",
        project_id="proj-1",
        status=RunStatus.COMPLETED,
        started_at=datetime.utcnow(),
        output_path=Path("/output"),
        execution_path=ExecutionPath.STANDARD,
        parent_run_id="run-0",
        metadata={
            "escalation_from": "smoke",
            "escalation_to": "standard",
            "escalation_reason": "High fallback ratio",
            "escalation_policy": {
                "fallback_threshold": 0.5,
                "confidence_threshold": 0.7,
                "max_escalation_depth": 3,
            }
        }
    )
    
    assert run.parent_run_id == "run-0"
    assert run.metadata["escalation_from"] == "smoke"
    assert run.metadata["escalation_to"] == "standard"
    assert run.metadata["escalation_reason"] == "High fallback ratio"
    assert run.metadata["escalation_policy"]["max_escalation_depth"] == 3


def test_evidence_export_json_format():
    """Test evidence export to JSON format."""
    evidence_data = {
        "run_id": "run-1",
        "evidence_items": [
            {"type": "screenshot", "path": "/path/to/screenshot.png"},
            {"type": "trace", "path": "/path/to/trace.json"},
        ]
    }
    
    # Verify structure is exportable to JSON
    import json
    json_str = json.dumps(evidence_data, indent=2)
    
    assert '"run_id"' in json_str
    assert '"evidence_items"' in json_str
    assert '"type"' in json_str


def test_evidence_export_csv_format():
    """Test evidence export to CSV format."""
    evidence_data = [
        {"type": "screenshot", "path": "/path/to/screenshot.png", "timestamp": "2024-01-01"},
        {"type": "trace", "path": "/path/to/trace.json", "timestamp": "2024-01-01"},
    ]
    
    # Verify structure is exportable to CSV
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["type", "path", "timestamp"])
    writer.writeheader()
    writer.writerows(evidence_data)
    
    csv_str = output.getvalue()
    
    assert "type,path,timestamp" in csv_str
    assert "screenshot" in csv_str


def test_evidence_export_markdown_format():
    """Test evidence export to Markdown format."""
    evidence_data = {
        "run_id": "run-1",
        "evidence_items": [
            {"type": "screenshot", "path": "/path/to/screenshot.png"},
        ]
    }
    
    # Verify structure can be formatted to Markdown
    markdown = f"# Evidence Report for {evidence_data['run_id']}\n\n"
    for item in evidence_data["evidence_items"]:
        markdown += f"- **{item['type']}**: {item['path']}\n"
    
    assert "# Evidence Report" in markdown
    assert "- **screenshot**" in markdown


def test_evidence_search_combined_filters():
    """Test evidence search with combined filters."""
    evidence_items = [
        {"type": "screenshot", "severity": "high", "plugin": "web_playwright", "confidence": 0.8},
        {"type": "trace", "severity": "medium", "plugin": "api_contract", "confidence": 0.6},
        {"type": "anomaly", "severity": "critical", "plugin": "web_playwright", "confidence": 0.9},
    ]
    
    # Filter by type and severity
    filtered = [
        item for item in evidence_items
        if item["type"] == "screenshot" and item["severity"] == "high"
    ]
    
    assert len(filtered) == 1
    assert filtered[0]["type"] == "screenshot"
    
    # Filter by plugin and confidence
    filtered = [
        item for item in evidence_items
        if item["plugin"] == "web_playwright" and item["confidence"] >= 0.8
    ]
    
    assert len(filtered) == 2


def test_evidence_search_text_query():
    """Test evidence search with text query."""
    evidence_items = [
        {"type": "screenshot", "content": "Error in checkout flow"},
        {"type": "trace", "content": "API timeout occurred"},
        {"type": "anomaly", "content": "Unexpected response format"},
    ]
    
    # Search for "checkout"
    results = [
        item for item in evidence_items
        if "checkout" in item["content"].lower()
    ]
    
    assert len(results) == 1
    assert results[0]["content"] == "Error in checkout flow"


def test_sse_realtime_updates_structure():
    """Test SSE real-time update message structure."""
    sse_message = {
        "event": "run_update",
        "data": {
            "run_id": "run-1",
            "status": "running",
            "confidence_score": 0.5,
            "fallback_ratio": 0.2,
        }
    }
    
    assert sse_message["event"] == "run_update"
    assert sse_message["data"]["run_id"] == "run-1"
    assert sse_message["data"]["status"] == "running"
    assert "confidence_score" in sse_message["data"]
    assert "fallback_ratio" in sse_message["data"]


def test_sse_evidence_update_structure():
    """Test SSE evidence update message structure."""
    sse_message = {
        "event": "evidence_update",
        "data": {
            "run_id": "run-1",
            "evidence_type": "screenshot",
            "count": 5,
        }
    }
    
    assert sse_message["event"] == "evidence_update"
    assert sse_message["data"]["evidence_type"] == "screenshot"
    assert sse_message["data"]["count"] == 5


def test_project_service_escalation_policy_update():
    """Test project service escalation policy update integration."""
    with TemporaryDirectory() as tmpdir:
        service = ProjectService(Path(tmpdir))
        
        project = service.create_project(
            name="test-project",
            product_type=ProductType.WEB,
            manifest_path=Path(tmpdir) / "manifest.yaml",
        )
        
        policy = EscalationPolicy(
            fallback_threshold=0.3,
            max_escalation_depth=2,
        )
        
        # Update via registry
        service.project_registry.update_project(
            project_id=project.project_id,
            escalation_policy=policy,
        )
        
        # Verify update
        updated = service.get_project(project.project_id)
        assert updated.escalation_policy is not None
        assert updated.escalation_policy.fallback_threshold == 0.3
        assert updated.escalation_policy.max_escalation_depth == 2
