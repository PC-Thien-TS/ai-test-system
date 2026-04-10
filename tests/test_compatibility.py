"""Tests for compatibility analyzer."""

import pytest

from orchestrator.compatibility import CompatibilityAnalyzer
from orchestrator.models import ProductType, SupportLevel


def test_list_plugins():
    """Test listing all plugins."""
    analyzer = CompatibilityAnalyzer()
    plugins = analyzer.list_plugins()
    
    assert len(plugins) > 0
    assert any(p.name == "web_playwright" for p in plugins)


def test_list_plugins_by_product_type():
    """Test filtering plugins by product type."""
    analyzer = CompatibilityAnalyzer()
    
    web_plugins = analyzer.list_plugins(product_type=ProductType.WEB)
    api_plugins = analyzer.list_plugins(product_type=ProductType.API)
    
    assert len(web_plugins) > 0
    assert len(api_plugins) > 0
    
    # Check that web_playwright is in web plugins
    assert any(p.name == "web_playwright" for p in web_plugins)


def test_get_plugin():
    """Test getting a specific plugin."""
    analyzer = CompatibilityAnalyzer()
    plugin = analyzer.get_plugin("web_playwright")
    
    assert plugin is not None
    assert plugin.name == "web_playwright"
    assert ProductType.WEB in plugin.product_types


def test_get_plugin_not_found():
    """Test getting a non-existent plugin."""
    analyzer = CompatibilityAnalyzer()
    plugin = analyzer.get_plugin("nonexistent_plugin")
    
    assert plugin is None


def test_analyze_plugin_compatibility():
    """Test analyzing plugin compatibility."""
    analyzer = CompatibilityAnalyzer()
    summary = analyzer.analyze_plugin_compatibility("web_playwright")
    
    assert summary.plugin_name == "web_playwright"
    assert summary.compatible is True
    assert summary.support_level in (SupportLevel.FULL, SupportLevel.USABLE)


def test_analyze_nonexistent_plugin():
    """Test analyzing a non-existent plugin."""
    analyzer = CompatibilityAnalyzer()
    summary = analyzer.analyze_plugin_compatibility("nonexistent")
    
    assert summary.compatible is False
    assert summary.support_level == SupportLevel.NONE
    assert len(summary.blockers) > 0


def test_get_recommended_plugins():
    """Test getting recommended plugins for a product type."""
    analyzer = CompatibilityAnalyzer()
    recommended = analyzer.get_recommended_plugins(ProductType.WEB)
    
    assert len(recommended) > 0
    for plugin in recommended:
        assert plugin.support_level in (SupportLevel.FULL, SupportLevel.USABLE)
        assert ProductType.WEB in plugin.product_types


def test_register_custom_plugin():
    """Test registering a custom plugin."""
    analyzer = CompatibilityAnalyzer()
    
    from orchestrator.models import PluginMetadata
    
    custom_plugin = PluginMetadata(
        name="custom_test",
        version="1.0.0",
        description="Custom test plugin",
        product_types=[ProductType.WEB],
        capabilities=["custom_test"],
        support_level=SupportLevel.FULL,
        min_platform_version="2.0.0",
        execution_depth_score=0.5,
        evidence_richness_score=0.6,
        confidence_score=0.55,
    )
    
    analyzer.register_plugin(custom_plugin)
    
    retrieved = analyzer.get_plugin("custom_test")
    assert retrieved is not None
    assert retrieved.name == "custom_test"
    assert retrieved.execution_depth_score == 0.5
    assert retrieved.evidence_richness_score == 0.6
    assert retrieved.confidence_score == 0.55


def test_version_comparison():
    """Test version comparison logic."""
    analyzer = CompatibilityAnalyzer()
    
    # Test that version comparison works
    assert not analyzer._version_less_than("2.1.0", "2.0.0")
    assert analyzer._version_less_than("2.0.0", "2.1.0")
    assert not analyzer._version_less_than("2.0.0", "2.0.0")


def test_plugin_execution_depth_metrics():
    """Test that plugins have execution depth metrics."""
    analyzer = CompatibilityAnalyzer()
    
    # Check that all built-in plugins have execution depth metrics
    plugins = analyzer.list_plugins()
    for plugin in plugins:
        assert 0.0 <= plugin.execution_depth_score <= 1.0
        assert 0.0 <= plugin.evidence_richness_score <= 1.0
        assert 0.0 <= plugin.confidence_score <= 1.0


def test_web_playwright_deep_capabilities():
    """Test that web_playwright has deep execution capabilities."""
    analyzer = CompatibilityAnalyzer()
    plugin = analyzer.get_plugin("web_playwright")
    
    assert plugin is not None
    assert "multi_step_journeys" in plugin.capabilities
    assert "negative_path_testing" in plugin.capabilities
    assert "retry_rollback_validation" in plugin.capabilities
    assert plugin.execution_depth_score >= 0.8  # Should have high execution depth


def test_api_contract_deep_capabilities():
    """Test that api_contract has deep execution capabilities."""
    analyzer = CompatibilityAnalyzer()
    plugin = analyzer.get_plugin("api_contract")
    
    assert plugin is not None
    assert "multi_endpoint_journeys" in plugin.capabilities
    assert "negative_request_testing" in plugin.capabilities
    assert "schema_evolution_detection" in plugin.capabilities
    assert plugin.execution_depth_score >= 0.85  # Should have high execution depth


def test_plugin_maturity_scoring():
    """Test that plugin maturity scores are calculated correctly."""
    analyzer = CompatibilityAnalyzer()
    
    # Check that plugins with higher support level have better execution depth
    web_plugin = analyzer.get_plugin("web_playwright")
    llm_plugin = analyzer.get_plugin("llm_consistency")
    
    assert web_plugin is not None
    assert llm_plugin is not None
    
    # web_playwright should have higher execution depth than llm_consistency
    assert web_plugin.execution_depth_score > llm_plugin.execution_depth_score
