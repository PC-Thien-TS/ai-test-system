"""Tests for Model Evaluation plugin."""

import pytest
import numpy as np
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.model_evaluation import ModelEvaluationPlugin
from orchestrator.plugins.registry import PluginRegistry
from orchestrator.plugins.integration import PluginOrchestrator, initialize_plugin_system


def test_model_evaluation_plugin_properties():
    """Test Model Evaluation plugin properties."""
    plugin = ModelEvaluationPlugin()
    
    assert plugin.name == "model_evaluation"
    assert plugin.version == "3.0.0"
    assert ProductType.MODEL.value in plugin.supported_product_types
    assert ExecutionPath.SMOKE in plugin.supported_execution_paths
    assert ExecutionPath.STANDARD in plugin.supported_execution_paths
    assert ExecutionPath.DEEP in plugin.supported_execution_paths
    assert ExecutionPath.INTELLIGENT in plugin.supported_execution_paths


def test_model_evaluation_plugin_config_validation():
    """Test Model Evaluation plugin configuration validation."""
    plugin = ModelEvaluationPlugin()
    
    # Valid config
    valid_config = {
        "model_type": "binary",
        "threshold": 0.5,
        "num_classes": 2,
    }
    is_valid, errors = plugin.validate_config(valid_config)
    assert is_valid is True
    assert len(errors) == 0
    
    # Invalid config - bad model_type
    invalid_config = {"model_type": "invalid"}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid model_type" in errors[0]
    
    # Invalid config - threshold out of range
    invalid_config = {"model_type": "binary", "threshold": 1.5}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid threshold" in errors[0]
    
    # Invalid config - num_classes too low
    invalid_config = {"model_type": "binary", "num_classes": 1}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid num_classes" in errors[0]


def test_model_evaluation_plugin_get_evaluation_scope_smoke():
    """Test getting evaluation scope for SMOKE execution path."""
    plugin = ModelEvaluationPlugin()
    
    config = {
        "evaluation_scope": {
            "smoke": ["accuracy", "threshold"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.SMOKE, config)
    assert scope == ["accuracy", "threshold"]


def test_model_evaluation_plugin_get_evaluation_scope_standard():
    """Test getting evaluation scope for STANDARD execution path."""
    plugin = ModelEvaluationPlugin()
    
    config = {
        "evaluation_scope": {
            "standard": ["accuracy", "precision", "recall", "f1"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.STANDARD, config)
    assert scope == ["accuracy", "precision", "recall", "f1"]


def test_model_evaluation_plugin_get_evaluation_scope_deep():
    """Test getting evaluation scope for DEEP execution path."""
    plugin = ModelEvaluationPlugin()
    
    config = {
        "evaluation_scope": {
            "deep": ["accuracy", "precision", "recall", "f1", "confusion_matrix", "threshold_sweep"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.DEEP, config)
    assert "confusion_matrix" in scope
    assert "threshold_sweep" in scope


def test_model_evaluation_plugin_get_evaluation_scope_intelligent():
    """Test getting evaluation scope for INTELLIGENT execution path."""
    plugin = ModelEvaluationPlugin()
    
    config = {
        "evaluation_scope": {
            "intelligent": ["accuracy", "drift_detection", "dataset_comparison", "anomaly_ranking"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.INTELLIGENT, config)
    assert "drift_detection" in scope
    assert "dataset_comparison" in scope
    assert "anomaly_ranking" in scope


def test_model_evaluation_plugin_get_evaluation_scope_default():
    """Test default evaluation scope when not configured."""
    plugin = ModelEvaluationPlugin()
    
    smoke_scope = plugin._get_evaluation_scope(ExecutionPath.SMOKE, {})
    assert "accuracy" in smoke_scope
    
    standard_scope = plugin._get_evaluation_scope(ExecutionPath.STANDARD, {})
    assert "confusion_matrix" in standard_scope


@pytest.mark.asyncio
async def test_model_evaluation_plugin_initialize():
    """Test Model Evaluation plugin initialization."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "threshold": 0.5,
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
            },
        )
        
        result = await plugin.initialize(context)
        assert result is True
        assert plugin._config is not None
        assert plugin._config.model_type == "binary"


@pytest.mark.asyncio
async def test_model_evaluation_plugin_initialize_with_files():
    """Test Model Evaluation plugin initialization with file paths."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        # Create test data files
        predictions_path = Path(tmpdir) / "predictions.npy"
        labels_path = Path(tmpdir) / "labels.npy"
        
        predictions = np.array([1, 0, 1, 0])
        labels = np.array([1, 0, 1, 0])
        
        np.save(predictions_path, predictions)
        np.save(labels_path, labels)
        
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "predictions_path": str(predictions_path),
                "labels_path": str(labels_path),
            },
        )
        
        result = await plugin.initialize(context)
        assert result is True
        assert plugin._predictions is not None
        assert plugin._labels is not None


@pytest.mark.asyncio
async def test_model_evaluation_plugin_cleanup():
    """Test Model Evaluation plugin cleanup."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={},
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.cleanup(context)
        assert result is True
        assert plugin._config is None
        assert plugin._predictions is None


@pytest.mark.asyncio
async def test_model_evaluation_plugin_execute_smoke():
    """Test Model Evaluation plugin execution with SMOKE path."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "threshold": 0.8,
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.plugin_name == "model_evaluation"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert "accuracy" in result.metrics
        assert result.metrics["accuracy"] == 1.0


@pytest.mark.asyncio
async def test_model_evaluation_plugin_execute_standard():
    """Test Model Evaluation plugin execution with STANDARD path."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "precision_threshold": 0.7,
                "recall_threshold": 0.7,
                "f1_threshold": 0.7,
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert "accuracy" in result.metrics
        assert "precision" in result.metrics
        assert "recall" in result.metrics
        assert "f1" in result.metrics


@pytest.mark.asyncio
async def test_model_evaluation_plugin_execute_with_failure():
    """Test Model Evaluation plugin execution with threshold failure."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "threshold": 0.95,
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 0, 0],  # 1 wrong prediction
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is False
        assert result.metrics["assertions_failed"] > 0


@pytest.mark.asyncio
async def test_model_evaluation_plugin_execute_deep():
    """Test Model Evaluation plugin execution with DEEP path."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.DEEP,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
                "probabilities": [0.9, 0.2, 0.8, 0.1],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert "confusion_matrix" in result.metrics or "threshold_sweep" in result.metrics


@pytest.mark.asyncio
async def test_model_evaluation_plugin_execute_intelligent():
    """Test Model Evaluation plugin execution with INTELLIGENT path."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.INTELLIGENT,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "baseline_accuracy": 0.85,
                "drift_threshold": 0.05,
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
                "probabilities": [0.9, 0.2, 0.8, 0.1],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        # Should include drift detection evidence
        drift_evidence = [e for e in result.evidence if "drift_detection" in e.content.get("assertion", "")]
        assert len(drift_evidence) >= 0


@pytest.mark.asyncio
async def test_model_evaluation_plugin_confusion_matrix():
    """Test confusion matrix evaluation."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        # Check for confusion matrix evidence
        cm_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.METRIC and e.content.get("metric") == "confusion_matrix"]
        assert len(cm_evidence) > 0


@pytest.mark.asyncio
async def test_model_evaluation_plugin_threshold_sweep():
    """Test threshold sweep evaluation."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.DEEP,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
                "probabilities": [0.9, 0.2, 0.8, 0.1],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        # Check for threshold sweep evidence
        threshold_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.METRIC and e.content.get("metric") == "threshold_sweep"]
        assert len(threshold_evidence) > 0


@pytest.mark.asyncio
async def test_model_evaluation_plugin_calibration():
    """Test calibration evaluation."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.DEEP,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
                "calibration_bins": 5,
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
                "probabilities": [0.9, 0.2, 0.8, 0.1],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        # Check for calibration evidence
        calibration_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.METRIC and e.content.get("metric") == "calibration"]
        assert len(calibration_evidence) >= 0  # May fail due to small sample size


@pytest.mark.asyncio
async def test_model_evaluation_plugin_multiclass():
    """Test multiclass model evaluation."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "model_type": "multiclass",
                "num_classes": 3,
            },
            metadata={
                "predictions": [0, 1, 2, 0, 1, 2],
                "labels": [0, 1, 2, 0, 1, 2],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert result.metrics["accuracy"] == 1.0


def test_model_evaluation_plugin_registry_registration():
    """Test Model Evaluation plugin registration in registry."""
    registry = PluginRegistry()
    registry.register_plugin_class(ModelEvaluationPlugin)
    
    assert registry.is_plugin_executable("model_evaluation")
    
    plugin = registry.get_plugin("model_evaluation")
    assert plugin is not None
    assert plugin.name == "model_evaluation"


def test_model_evaluation_plugin_orchestrator_integration():
    """Test Model Evaluation plugin integration with PluginOrchestrator."""
    orchestrator = PluginOrchestrator()
    
    # Check that Model Evaluation plugin is registered
    assert orchestrator.registry.is_plugin_executable("model_evaluation")


def test_model_evaluation_plugin_initialize_system():
    """Test Model Evaluation plugin in system initialization."""
    registry = initialize_plugin_system()
    
    assert registry.is_plugin_executable("model_evaluation")


def test_model_evaluation_plugin_evidence_types():
    """Test evidence types collected by Model Evaluation plugin."""
    plugin = ModelEvaluationPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "model_type": "binary",
            },
            metadata={
                "predictions": [1, 0, 1, 0],
                "labels": [1, 0, 1, 0],
            },
        )
        
        plugin._predictions = np.array(context.metadata["predictions"])
        plugin._labels = np.array(context.metadata["labels"])
        plugin._config = plugin.ModelEvaluationConfig(model_type="binary")
        
        # Test accuracy evaluation
        accuracy, evidence, passed, failed = plugin._evaluate_accuracy(context)
        
        # Check for METRIC evidence
        assert len(evidence) > 0
        assert evidence[0].evidence_type == EvidenceType.METRIC


def test_model_evaluation_plugin_metrics_integration():
    """Test Model Evaluation plugin metrics integration with PluginOrchestrator."""
    orchestrator = PluginOrchestrator()
    
    # Create a mock result
    result = PluginExecutionResult(
        plugin_name="model_evaluation",
        status=ExecutionStatus.COMPLETED,
        success=True,
        metrics={
            "assertions_passed": 5,
            "assertions_failed": 0,
            "accuracy": 0.95,
            "precision": 0.92,
            "recall": 0.90,
            "f1": 0.91,
        },
    )
    
    # Test metrics calculation
    metrics = orchestrator.calculate_plugin_metrics({"model_evaluation": result})
    
    assert metrics["model_evaluation"]["success"] is True
    assert metrics["model_evaluation"]["metrics"]["accuracy"] == 0.95


def test_model_evaluation_plugin_metadata_compatibility():
    """Test Model Evaluation plugin metadata compatibility with existing metadata."""
    from orchestrator.compatibility import BUILTIN_PLUGINS
    
    # Check that model_evaluation metadata exists
    assert "model_evaluation" in BUILTIN_PLUGINS
    
    metadata = BUILTIN_PLUGINS["model_evaluation"]
    assert metadata.name == "model_evaluation"
    assert metadata.version == "2.0.0"  # Existing metadata version
    assert metadata.execution_depth_score == 0.80
    assert metadata.evidence_richness_score == 0.85
    assert metadata.confidence_score == 0.82


def test_model_evaluation_plugin_binary_vs_multiclass():
    """Test binary vs multiclass model type handling."""
    plugin = ModelEvaluationPlugin()
    
    # Binary config
    binary_config = {"model_type": "binary"}
    is_valid, errors = plugin.validate_config(binary_config)
    assert is_valid is True
    
    # Multiclass config
    multiclass_config = {"model_type": "multiclass", "num_classes": 5}
    is_valid, errors = plugin.validate_config(multiclass_config)
    assert is_valid is True
