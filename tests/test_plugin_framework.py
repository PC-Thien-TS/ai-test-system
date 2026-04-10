"""Tests for plugin execution framework and Playwright plugin."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    BasePlugin,
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.executor import PluginExecutor, PluginExecutionError
from orchestrator.plugins.playwright import PlaywrightPlugin
from orchestrator.plugins.registry import PluginRegistry, get_plugin_registry
from orchestrator.plugins.integration import PluginOrchestrator, initialize_plugin_system


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""
    
    def __init__(self, name="mock_plugin", version="1.0.0"):
        self._plugin_name = name
        self._plugin_version = version
        self._initialized = False
        self._should_fail = False
        self._execution_count = 0
    
    @property
    def name(self) -> str:
        return self._plugin_name
    
    @property
    def version(self) -> str:
        return self._plugin_version
    
    @property
    def supported_product_types(self) -> List[str]:
        return [ProductType.WEB.value]
    
    @property
    def supported_execution_paths(self) -> List[ExecutionPath]:
        return [ExecutionPath.SMOKE, ExecutionPath.STANDARD]
    
    async def initialize(self, context: ExecutionContext) -> bool:
        self._initialized = True
        return not self._should_fail
    
    async def execute(self, context: ExecutionContext) -> PluginExecutionResult:
        self._execution_count += 1
        
        if self._should_fail:
            return PluginExecutionResult(
                plugin_name=self.name,
                status=ExecutionStatus.FAILED,
                success=False,
                error_message="Mock plugin failure",
            )
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={"test_metric": 42},
                severity="info",
            )
        ]
        
        return PluginExecutionResult(
            plugin_name=self.name,
            status=ExecutionStatus.COMPLETED,
            success=True,
            evidence=evidence,
            metrics={"test_count": 1},
        )
    
    async def cleanup(self, context: ExecutionContext) -> bool:
        self._initialized = False
        return True
    
    def set_should_fail(self, should_fail: bool):
        self._should_fail = should_fail


def test_execution_context_creation():
    """Test ExecutionContext creation and serialization."""
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={"test_key": "test_value"},
            timeout_seconds=60,
        )
        
        assert context.run_id == "run-1"
        assert context.project_id == "proj-1"
        assert context.execution_path == ExecutionPath.STANDARD
        assert context.config["test_key"] == "test_value"
        assert context.timeout_seconds == 60
        
        dict_repr = context.to_dict()
        assert dict_repr["run_id"] == "run-1"
        assert dict_repr["execution_path"] == "standard"


def test_evidence_item_creation():
    """Test EvidenceItem creation and serialization."""
    evidence = EvidenceItem(
        evidence_type=EvidenceType.SCREENSHOT,
        content={"path": "/path/to/screenshot.png"},
        severity="high",
        source="test_plugin",
        confidence=0.9,
    )
    
    assert evidence.evidence_type == EvidenceType.SCREENSHOT
    assert evidence.severity == "high"
    assert evidence.confidence == 0.9
    
    dict_repr = evidence.to_dict()
    assert dict_repr["evidence_type"] == "screenshot"
    assert dict_repr["severity"] == "high"


def test_plugin_execution_result_creation():
    """Test PluginExecutionResult creation and serialization."""
    result = PluginExecutionResult(
        plugin_name="test_plugin",
        status=ExecutionStatus.RUNNING,
        success=False,
    )
    
    assert result.plugin_name == "test_plugin"
    assert result.status == ExecutionStatus.RUNNING
    assert result.success is False
    
    result.mark_completed()
    assert result.completed_at is not None
    assert result.duration_seconds >= 0
    
    dict_repr = result.to_dict()
    assert dict_repr["plugin_name"] == "test_plugin"
    assert dict_repr["status"] == "running"


def test_mock_plugin_basic():
    """Test mock plugin basic functionality."""
    plugin = MockPlugin()
    
    assert plugin.name == "mock_plugin"
    assert plugin.version == "1.0.0"
    assert ExecutionPath.SMOKE in plugin.supported_execution_paths
    assert ExecutionPath.STANDARD in plugin.supported_execution_paths


def test_plugin_registry_registration():
    """Test plugin registry registration."""
    registry = PluginRegistry()
    
    registry.register_plugin_class(MockPlugin)
    
    assert registry.is_plugin_executable("mock_plugin")
    
    plugin = registry.get_plugin("mock_plugin")
    assert plugin is not None
    assert plugin.name == "mock_plugin"


def test_plugin_registry_list_plugins():
    """Test listing plugins from registry."""
    registry = PluginRegistry()
    
    registry.register_plugin_class(MockPlugin)
    
    plugins = registry.list_plugins()
    assert len(plugins) > 0
    
    web_plugins = registry.list_plugins(product_type=ProductType.WEB)
    assert len(web_plugins) > 0


def test_plugin_registry_executable_list():
    """Test listing executable plugins."""
    registry = PluginRegistry()
    
    registry.register_plugin_class(MockPlugin)
    
    executable = registry.list_executable_plugins()
    assert "mock_plugin" in executable


def test_plugin_executor_single():
    """Test executing a single plugin."""
    registry = PluginRegistry()
    registry.register_plugin_class(MockPlugin)
    executor = PluginExecutor(registry)
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
        )
        
        result = executor.execute_plugin("mock_plugin", context)
        
        assert result.plugin_name == "mock_plugin"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True


def test_plugin_executor_parallel():
    """Test executing multiple plugins in parallel."""
    registry = PluginRegistry()
    
    # Register multiple mock plugins
    registry.register_plugin_class(MockPlugin)
    registry.register_plugin_class(MockPlugin, metadata=None)
    
    executor = PluginExecutor(registry)
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
        )
        
        results = executor.execute_plugins(
            ["mock_plugin"],
            context,
            parallel=True,
        )
        
        assert "mock_plugin" in results


def test_plugin_executor_retry():
    """Test plugin execution with retry."""
    registry = PluginRegistry()
    plugin = MockPlugin()
    plugin.set_should_fail(True)
    registry.register_plugin_class(MockPlugin)
    
    executor = PluginExecutor(registry)
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
        )
        
        result = executor.execute_plugin_with_retry(
            "mock_plugin",
            context,
            max_retries=2,
            retry_delay_seconds=0.1,
        )
        
        assert result.status == ExecutionStatus.FAILED


def test_playwright_plugin_properties():
    """Test Playwright plugin properties."""
    plugin = PlaywrightPlugin()
    
    assert plugin.name == "web_playwright"
    assert plugin.version == "3.0.0"
    assert ProductType.WEB.value in plugin.supported_product_types
    assert ExecutionPath.SMOKE in plugin.supported_execution_paths
    assert ExecutionPath.STANDARD in plugin.supported_execution_paths
    assert ExecutionPath.DEEP in plugin.supported_execution_paths
    assert ExecutionPath.INTELLIGENT in plugin.supported_execution_paths


def test_playwright_plugin_config_validation():
    """Test Playwright plugin configuration validation."""
    plugin = PlaywrightPlugin()
    
    # Valid config
    valid_config = {
        "base_url": "http://localhost:3000",
        "browser_type": "chromium",
    }
    is_valid, errors = plugin.validate_config(valid_config)
    assert is_valid is True
    assert len(errors) == 0
    
    # Invalid config - missing base_url
    invalid_config = {"browser_type": "chromium"}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert len(errors) > 0
    
    # Invalid config - bad browser type
    invalid_config = {
        "base_url": "http://localhost:3000",
        "browser_type": "invalid_browser",
    }
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False


def test_playwright_plugin_get_test_paths():
    """Test Playwright plugin test path selection."""
    plugin = PlaywrightPlugin()
    
    config = {
        "test_paths": {
            "smoke": ["/"],
            "standard": ["/", "/about"],
            "deep": ["/", "/about", "/contact"],
        }
    }
    
    smoke_paths = plugin._get_test_paths(ExecutionPath.SMOKE, config)
    assert smoke_paths == ["/"]
    
    standard_paths = plugin._get_test_paths(ExecutionPath.STANDARD, config)
    assert standard_paths == ["/", "/about"]
    
    deep_paths = plugin._get_test_paths(ExecutionPath.DEEP, config)
    assert deep_paths == ["/", "/about", "/contact"]


def test_plugin_orchestrator_execute_run_plugins():
    """Test plugin orchestrator executing run plugins."""
    orchestrator = PluginOrchestrator()
    
    from orchestrator.models import Run, RunStatus, GateResult
    
    with TemporaryDirectory() as tmpdir:
        run = Run(
            run_id="run-1",
            project_id="proj-1",
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow(),
            output_path=Path(tmpdir),
            execution_path=ExecutionPath.SMOKE,
        )
        
        results = orchestrator.execute_run_plugins(
            run=run,
            plugin_names=["mock_plugin"],
            parallel=False,
        )
        
        assert "mock_plugin" in results


def test_plugin_orchestrator_convert_results():
    """Test converting plugin results to evidence."""
    orchestrator = PluginOrchestrator()
    
    result = PluginExecutionResult(
        plugin_name="test_plugin",
        status=ExecutionStatus.COMPLETED,
        success=True,
        evidence=[
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={"test": 42},
            )
        ],
    )
    
    evidence = orchestrator.convert_results_to_evidence({"test_plugin": result})
    
    assert "test_plugin" in evidence
    assert len(evidence["test_plugin"]) == 1


def test_plugin_orchestrator_calculate_metrics():
    """Test calculating metrics from plugin results."""
    orchestrator = PluginOrchestrator()
    
    results = {
        "plugin1": PluginExecutionResult(
            plugin_name="plugin1",
            status=ExecutionStatus.COMPLETED,
            success=True,
            duration_seconds=5.0,
            evidence=[],
            metrics={"tests": 10},
        ),
        "plugin2": PluginExecutionResult(
            plugin_name="plugin2",
            status=ExecutionStatus.FAILED,
            success=False,
            duration_seconds=3.0,
            evidence=[],
        ),
    }
    
    metrics = orchestrator.calculate_plugin_metrics(results)
    
    assert metrics["plugin1"]["success"] is True
    assert metrics["plugin2"]["success"] is False
    assert metrics["plugin1"]["duration_seconds"] == 5.0


def test_plugin_orchestrator_fallback_ratio():
    """Test calculating fallback ratio."""
    orchestrator = PluginOrchestrator()
    
    results = {
        "plugin1": PluginExecutionResult(
            plugin_name="plugin1",
            status=ExecutionStatus.COMPLETED,
            success=True,
        ),
        "plugin2": PluginExecutionResult(
            plugin_name="plugin2",
            status=ExecutionStatus.FAILED,
            success=False,
        ),
        "plugin3": PluginExecutionResult(
            plugin_name="plugin3",
            status=ExecutionStatus.COMPLETED,
            success=True,
        ),
    }
    
    fallback_ratio = orchestrator.get_fallback_ratio(results)
    assert fallback_ratio == 1/3  # 1 failed out of 3


def test_plugin_orchestrator_confidence_score():
    """Test calculating confidence score."""
    orchestrator = PluginOrchestrator()
    
    results = {
        "plugin1": PluginExecutionResult(
            plugin_name="plugin1",
            status=ExecutionStatus.COMPLETED,
            success=True,
        ),
        "plugin2": PluginExecutionResult(
            plugin_name="plugin2",
            status=ExecutionStatus.FAILED,
            success=False,
        ),
    }
    
    confidence = orchestrator.get_confidence_score(results)
    assert confidence == 0.5  # 1 success out of 2


def test_global_plugin_registry():
    """Test global plugin registry."""
    registry = get_plugin_registry()
    
    # Should be same instance
    registry2 = get_plugin_registry()
    assert registry is registry2


def test_initialize_plugin_system():
    """Test plugin system initialization."""
    registry = initialize_plugin_system()
    
    # Playwright should be registered
    assert registry.is_plugin_executable("web_playwright")
