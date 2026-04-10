"""Tests for API Contract Testing plugin."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, AsyncMock

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.api_contract import ApiContractPlugin
from orchestrator.plugins.executor import PluginExecutor
from orchestrator.plugins.registry import PluginRegistry
from orchestrator.plugins.integration import PluginOrchestrator, initialize_plugin_system


class MockResponse:
    """Mock requests Response object."""
    
    def __init__(self, status_code=200, text='{"result": "ok"}'):
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": "application/json"}
    
    def json(self):
        import json
        return json.loads(self.text)


def test_api_contract_plugin_properties():
    """Test API Contract plugin properties."""
    plugin = ApiContractPlugin()
    
    assert plugin.name == "api_contract"
    assert plugin.version == "3.0.0"
    assert ProductType.API.value in plugin.supported_product_types
    assert ExecutionPath.SMOKE in plugin.supported_execution_paths
    assert ExecutionPath.STANDARD in plugin.supported_execution_paths
    assert ExecutionPath.DEEP in plugin.supported_execution_paths
    assert ExecutionPath.INTELLIGENT in plugin.supported_execution_paths


def test_api_contract_plugin_config_validation():
    """Test API Contract plugin configuration validation."""
    plugin = ApiContractPlugin()
    
    # Valid config
    valid_config = {
        "base_url": "http://localhost:8000",
        "timeout": 30,
        "retry_count": 3,
    }
    is_valid, errors = plugin.validate_config(valid_config)
    assert is_valid is True
    assert len(errors) == 0
    
    # Invalid config - missing base_url
    invalid_config = {"timeout": 30}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Missing required field: base_url" in errors
    
    # Invalid config - negative timeout
    invalid_config = {"base_url": "http://localhost:8000", "timeout": -5}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid timeout" in errors[0]
    
    # Invalid config - negative retry_count
    invalid_config = {"base_url": "http://localhost:8000", "retry_count": -1}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid retry_count" in errors[0]


def test_api_contract_plugin_get_test_endpoints_smoke():
    """Test getting test endpoints for SMOKE execution path."""
    plugin = ApiContractPlugin()
    
    config = {
        "endpoints": {
            "smoke": [
                {"path": "/health", "method": "GET", "expected_status": 200},
            ]
        }
    }
    
    endpoints = plugin._get_test_endpoints(ExecutionPath.SMOKE, config)
    assert len(endpoints) == 1
    assert endpoints[0]["path"] == "/health"
    assert endpoints[0]["method"] == "GET"
    assert endpoints[0]["expected_status"] == 200


def test_api_contract_plugin_get_test_endpoints_standard():
    """Test getting test endpoints for STANDARD execution path."""
    plugin = ApiContractPlugin()
    
    config = {
        "endpoints": {
            "standard": [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "GET", "expected_status": 200},
            ]
        }
    }
    
    endpoints = plugin._get_test_endpoints(ExecutionPath.STANDARD, config)
    assert len(endpoints) == 2
    assert endpoints[0]["path"] == "/health"
    assert endpoints[1]["path"] == "/api/users"


def test_api_contract_plugin_get_test_endpoints_deep():
    """Test getting test endpoints for DEEP execution path."""
    plugin = ApiContractPlugin()
    
    config = {
        "endpoints": {
            "deep": [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "GET", "expected_status": 200},
                {"path": "/api/users/1", "method": "DELETE", "expected_status": 204},
            ]
        }
    }
    
    endpoints = plugin._get_test_endpoints(ExecutionPath.DEEP, config)
    assert len(endpoints) == 3
    assert endpoints[2]["method"] == "DELETE"


def test_api_contract_plugin_get_test_endpoints_intelligent():
    """Test getting test endpoints for INTELLIGENT execution path."""
    plugin = ApiContractPlugin()
    
    config = {
        "endpoints": {
            "intelligent": [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/users/999", "method": "GET", "expected_status": 404},
            ]
        }
    }
    
    endpoints = plugin._get_test_endpoints(ExecutionPath.INTELLIGENT, config)
    assert len(endpoints) == 2
    assert endpoints[1]["expected_status"] == 404


def test_api_contract_plugin_get_test_endpoints_default():
    """Test default test endpoints when not configured."""
    plugin = ApiContractPlugin()
    
    smoke_endpoints = plugin._get_test_endpoints(ExecutionPath.SMOKE, {})
    assert len(smoke_endpoints) == 1
    assert smoke_endpoints[0]["path"] == "/health"
    
    standard_endpoints = plugin._get_test_endpoints(ExecutionPath.STANDARD, {})
    assert len(standard_endpoints) == 3


@pytest.mark.asyncio
async def test_api_contract_plugin_initialize():
    """Test API Contract plugin initialization."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={"auth_token": "test-token"},
        )
        
        result = await plugin.initialize(context)
        assert result is True
        assert plugin._session is not None
        assert plugin._auth_token == "test-token"


@pytest.mark.asyncio
async def test_api_contract_plugin_initialize_without_auth():
    """Test API Contract plugin initialization without auth token."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={},
        )
        
        result = await plugin.initialize(context)
        assert result is True
        assert plugin._session is not None
        assert plugin._auth_token is None


@pytest.mark.asyncio
async def test_api_contract_plugin_cleanup():
    """Test API Contract plugin cleanup."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={},
        )
        
        await plugin.initialize(context)
        result = await plugin.cleanup(context)
        assert result is True
        assert plugin._session is None


def test_api_contract_plugin_safe_json_parse():
    """Test safe JSON parsing."""
    plugin = ApiContractPlugin()
    
    # Valid JSON
    result = plugin._safe_json_parse('{"key": "value"}')
    assert result == {"key": "value"}
    
    # Invalid JSON
    result = plugin._safe_json_parse('not json')
    assert result == 'not json'


@pytest.mark.asyncio
async def test_api_contract_plugin_execute_with_mock():
    """Test API Contract plugin execution with mocked requests."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "smoke": [
                        {"path": "/health", "method": "GET", "expected_status": 200},
                    ]
                }
            },
        )
        
        # Mock the session and request
        mock_response = MockResponse(status_code=200, text='{"status": "ok"}')
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        assert result.plugin_name == "api_contract"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert len(result.evidence) > 0
        assert result.metrics["endpoints_tested"] == 1
        assert result.metrics["assertions_passed"] > 0


@pytest.mark.asyncio
async def test_api_contract_plugin_execute_with_status_failure():
    """Test API Contract plugin execution with status code failure."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "smoke": [
                        {"path": "/health", "method": "GET", "expected_status": 200},
                    ]
                }
            },
        )
        
        # Mock the session with 500 response
        mock_response = MockResponse(status_code=500, text='{"error": "internal"}')
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is False
        assert result.metrics["assertions_failed"] > 0


@pytest.mark.asyncio
async def test_api_contract_plugin_execute_with_timeout():
    """Test API Contract plugin execution with timeout error."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "smoke": [
                        {"path": "/health", "method": "GET", "expected_status": 200},
                    ]
                }
            },
        )
        
        # Mock the session with timeout exception
        import requests
        mock_session = Mock()
        mock_session.get = Mock(side_effect=requests.exceptions.Timeout())
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is False
        assert result.metrics["assertions_failed"] > 0


@pytest.mark.asyncio
async def test_api_contract_plugin_execute_with_connection_error():
    """Test API Contract plugin execution with connection error."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "smoke": [
                        {"path": "/health", "method": "GET", "expected_status": 200},
                    ]
                }
            },
        )
        
        # Mock the session with connection error
        import requests
        mock_session = Mock()
        mock_session.get = Mock(side_effect=requests.exceptions.ConnectionError())
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is False
        assert result.metrics["assertions_failed"] > 0


@pytest.mark.asyncio
async def test_api_contract_plugin_schema_validation():
    """Test API Contract plugin with schema validation."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "standard": [
                        {
                            "path": "/api/users",
                            "method": "GET",
                            "expected_status": 200,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "users": {"type": "array"},
                                },
                            },
                        }
                    ]
                }
            },
        )
        
        # Mock the session with valid schema response
        mock_response = MockResponse(status_code=200, text='{"users": []}')
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert result.metrics["schema_validations_passed"] > 0


@pytest.mark.asyncio
async def test_api_contract_plugin_schema_validation_failure():
    """Test API Contract plugin with schema validation failure."""
    plugin = ApiContractPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "standard": [
                        {
                            "path": "/api/users",
                            "method": "GET",
                            "expected_status": 200,
                            "schema": {
                                "type": "object",
                                "required": ["users"],
                            },
                        }
                    ]
                }
            },
        )
        
        # Mock the session with invalid schema response
        mock_response = MockResponse(status_code=200, text='{"data": []}')
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is False
        assert result.metrics["schema_validations_failed"] > 0


def test_api_contract_plugin_registry_registration():
    """Test API Contract plugin registration in registry."""
    registry = PluginRegistry()
    registry.register_plugin_class(ApiContractPlugin)
    
    assert registry.is_plugin_executable("api_contract")
    
    plugin = registry.get_plugin("api_contract")
    assert plugin is not None
    assert plugin.name == "api_contract"


def test_api_contract_plugin_orchestrator_integration():
    """Test API Contract plugin integration with PluginOrchestrator."""
    orchestrator = PluginOrchestrator()
    
    # Check that API Contract plugin is registered
    assert orchestrator.registry.is_plugin_executable("api_contract")


def test_api_contract_plugin_initialize_system():
    """Test API Contract plugin in system initialization."""
    registry = initialize_plugin_system()
    
    assert registry.is_plugin_executable("api_contract")


@pytest.mark.asyncio
async def test_api_contract_plugin_evidence_types():
    """Test evidence types collected by API Contract plugin."""
    plugin = ApiContractPlugin()
    
    # Check that the plugin can create various evidence types
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "base_url": "http://localhost:8000",
                "endpoints": {
                    "smoke": [
                        {"path": "/health", "method": "GET", "expected_status": 200},
                    ]
                }
            },
        )
        
        # Mock the session
        mock_response = MockResponse(status_code=200, text='{"status": "ok"}')
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.headers = {}
        mock_session.timeout = 30
        
        plugin._session = mock_session
        
        result = await plugin.execute(context)
        
        # Check for TRACE evidence
        trace_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.TRACE]
        assert len(trace_evidence) > 0
        
        # Check for METRIC evidence
        metric_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.METRIC]
        assert len(metric_evidence) > 0


def test_api_contract_plugin_metrics_integration():
    """Test API Contract plugin metrics integration with PluginOrchestrator."""
    orchestrator = PluginOrchestrator()
    
    # Create a mock result
    result = PluginExecutionResult(
        plugin_name="api_contract",
        status=ExecutionStatus.COMPLETED,
        success=True,
        metrics={
            "assertions_passed": 10,
            "assertions_failed": 0,
            "endpoints_tested": 5,
            "avg_latency_ms": 150.5,
            "schema_validations_passed": 3,
            "schema_validations_failed": 0,
        },
    )
    
    # Test metrics calculation
    metrics = orchestrator.calculate_plugin_metrics({"api_contract": result})
    
    assert metrics["api_contract"]["success"] is True
    assert metrics["api_contract"]["metrics"]["assertions_passed"] == 10
    assert metrics["api_contract"]["metrics"]["avg_latency_ms"] == 150.5


def test_api_contract_plugin_metadata_compatibility():
    """Test API Contract plugin metadata compatibility with existing metadata."""
    from orchestrator.compatibility import BUILTIN_PLUGINS
    
    # Check that api_contract metadata exists
    assert "api_contract" in BUILTIN_PLUGINS
    
    metadata = BUILTIN_PLUGINS["api_contract"]
    assert metadata.name == "api_contract"
    assert metadata.version == "2.0.0"  # Existing metadata version
    assert metadata.execution_depth_score == 0.90
    assert metadata.evidence_richness_score == 0.92
    assert metadata.confidence_score == 0.91
