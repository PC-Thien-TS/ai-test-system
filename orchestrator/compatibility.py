"""Plugin compatibility analysis for the Universal Testing Platform."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.models import (
    CompatibilitySummary,
    PluginMetadata,
    ProductType,
    SupportLevel,
)


# Built-in plugin catalog
BUILTIN_PLUGINS: Dict[str, PluginMetadata] = {
    "web_playwright": PluginMetadata(
        name="web_playwright",
        version="2.0.0",
        description="Playwright-based web UI testing with deep execution",
        product_types=[ProductType.WEB],
        capabilities=[
            "login",
            "navigation",
            "form_submit",
            "assertions",
            "multi_step_journeys",
            "negative_path_testing",
            "retry_rollback_validation",
            "threshold_calibration",
        ],
        support_level=SupportLevel.FULL,
        dependencies=["playwright"],
        min_platform_version="2.4.0",
        execution_depth_score=0.85,
        evidence_richness_score=0.90,
        confidence_score=0.88,
    ),
    "api_contract": PluginMetadata(
        name="api_contract",
        version="2.0.0",
        description="API contract and schema validation with deep execution",
        product_types=[ProductType.API],
        capabilities=[
            "contract_validation",
            "schema_check",
            "auth_flow",
            "multi_endpoint_journeys",
            "negative_request_testing",
            "retry_mechanism_validation",
            "schema_evolution_detection",
            "anomaly_heuristics",
        ],
        support_level=SupportLevel.FULL,
        dependencies=["requests", "jsonschema"],
        min_platform_version="2.4.0",
        execution_depth_score=0.90,
        evidence_richness_score=0.92,
        confidence_score=0.91,
    ),
    "model_evaluation": PluginMetadata(
        name="model_evaluation",
        version="2.0.0",
        description="ML model evaluation and metrics with deep execution",
        product_types=[ProductType.MODEL],
        capabilities=[
            "confusion_matrix",
            "threshold_checks",
            "per_class_metrics",
            "dataset_comparison",
            "multi_dataset_evaluation",
            "negative_sample_testing",
            "threshold_calibration",
            "drift_detection",
        ],
        support_level=SupportLevel.FULL,
        dependencies=["scikit-learn", "numpy"],
        min_platform_version="2.4.0",
        execution_depth_score=0.80,
        evidence_richness_score=0.85,
        confidence_score=0.82,
    ),
    "rag_grounding": PluginMetadata(
        name="rag_grounding",
        version="2.0.0",
        description="RAG grounding and citation checks with deep execution",
        product_types=[ProductType.RAG],
        capabilities=[
            "grounding_checks",
            "citation_verification",
            "retrieval_response_consistency",
            "multi_hop_grounding",
            "negative_citation_testing",
            "confidence_threshold_validation",
            "grounding_confidence_scoring",
        ],
        support_level=SupportLevel.FULL,
        dependencies=["sentence-transformers", "faiss"],
        min_platform_version="2.4.0",
        execution_depth_score=0.78,
        evidence_richness_score=0.88,
        confidence_score=0.80,
    ),
    "llm_consistency": PluginMetadata(
        name="llm_consistency",
        version="2.0.0",
        description="LLM output consistency testing with deep execution",
        product_types=[ProductType.LLM_APP],
        capabilities=[
            "consistency_testing",
            "output_structure_validation",
            "safety_policy_checks",
            "multi_turn_consistency",
            "adversarial_input_testing",
            "safety_consistency_validation",
            "output_confidence_scoring",
        ],
        support_level=SupportLevel.USABLE,
        dependencies=["openai"],
        min_platform_version="2.4.0",
        execution_depth_score=0.70,
        evidence_richness_score=0.75,
        confidence_score=0.72,
    ),
    "workflow_validator": PluginMetadata(
        name="workflow_validator",
        version="2.0.0",
        description="Workflow step chain validation with deep execution",
        product_types=[ProductType.WORKFLOW],
        capabilities=[
            "step_chain_validation",
            "state_transition_assertions",
            "multi_workflow_journeys",
            "negative_state_testing",
            "rollback_validation",
            "state_consistency_checks",
        ],
        support_level=SupportLevel.FULL,
        dependencies=[],
        min_platform_version="2.4.0",
        execution_depth_score=0.88,
        evidence_richness_score=0.90,
        confidence_score=0.89,
    ),
    "data_pipeline_validator": PluginMetadata(
        name="data_pipeline_validator",
        version="2.0.0",
        description="Data pipeline validation with deep execution",
        product_types=[ProductType.DATA_PIPELINE],
        capabilities=[
            "transformation_validation",
            "batch_completeness",
            "schema_drift_checks",
            "multi_stage_validation",
            "negative_data_testing",
            "anomaly_detection_heuristics",
            "schema_evolution_tracking",
        ],
        support_level=SupportLevel.USABLE,
        dependencies=["pandas", "great_expectations"],
        min_platform_version="2.4.0",
        execution_depth_score=0.75,
        evidence_richness_score=0.82,
        confidence_score=0.77,
    ),
}


class CompatibilityAnalyzer:
    """Analyzes plugin compatibility with the platform and projects."""

    def __init__(self, platform_version: str = "2.4.0"):
        """
        Initialize the compatibility analyzer.
        
        Args:
            platform_version: Current platform version.
        """
        self.platform_version = platform_version
        self._plugins = BUILTIN_PLUGINS.copy()

    def register_plugin(self, plugin: PluginMetadata) -> None:
        """
        Register a custom plugin.
        
        Args:
            plugin: The plugin metadata to register.
        """
        self._plugins[plugin.name] = plugin

    def get_plugin(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata by name.
        
        Args:
            plugin_name: The plugin name.
            
        Returns:
            PluginMetadata if found, None otherwise.
        """
        return self._plugins.get(plugin_name)

    def list_plugins(
        self,
        product_type: Optional[ProductType] = None,
    ) -> List[PluginMetadata]:
        """
        List all plugins, optionally filtered by product type.
        
        Args:
            product_type: Optional product type filter.
            
        Returns:
            List of matching plugins.
        """
        plugins = list(self._plugins.values())
        
        if product_type:
            plugins = [p for p in plugins if product_type in p.product_types]
        
        return plugins

    def analyze_plugin_compatibility(
        self,
        plugin_name: str,
    ) -> CompatibilitySummary:
        """
        Analyze compatibility of a plugin with the current platform.
        
        Args:
            plugin_name: The plugin name to analyze.
            
        Returns:
            CompatibilitySummary with analysis results.
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            return CompatibilitySummary(
                plugin_name=plugin_name,
                platform_version=self.platform_version,
                compatible=False,
                support_level=SupportLevel.NONE,
                notes=["Plugin not found in catalog"],
                blockers=["Plugin not registered"],
            )
        
        notes = []
        blockers = []
        compatible = True
        support_level = plugin.support_level

        # Check platform version compatibility
        if plugin.min_platform_version:
            if self._version_less_than(self.platform_version, plugin.min_platform_version):
                compatible = False
                blockers.append(
                    f"Platform version {self.platform_version} is less than "
                    f"required minimum {plugin.min_platform_version}"
                )
                notes.append(
                    f"Upgrade platform to at least {plugin.min_platform_version} "
                    f"to use this plugin"
                )

        # Check support level
        if support_level == SupportLevel.FALLBACK:
            notes.append(
                "Plugin operates in fallback mode with limited capabilities"
            )
        elif support_level == SupportLevel.PARTIAL:
            notes.append("Plugin has partial support - some capabilities may be limited")
        elif support_level == SupportLevel.USABLE:
            notes.append("Plugin is usable with full core capabilities")

        return CompatibilitySummary(
            plugin_name=plugin_name,
            platform_version=self.platform_version,
            compatible=compatible,
            support_level=support_level,
            notes=notes,
            blockers=blockers,
        )

    def analyze_project_compatibility(
        self,
        product_type: ProductType,
    ) -> List[CompatibilitySummary]:
        """
        Analyze compatibility of all plugins for a given product type.
        
        Args:
            product_type: The product type to analyze.
            
        Returns:
            List of CompatibilitySummary for matching plugins.
        """
        summaries = []
        
        for plugin in self.list_plugins(product_type=product_type):
            summary = self.analyze_plugin_compatibility(plugin.name)
            summaries.append(summary)
        
        return summaries

    def get_recommended_plugins(
        self,
        product_type: ProductType,
    ) -> List[PluginMetadata]:
        """
        Get recommended plugins for a product type.
        
        Args:
            product_type: The product type.
            
        Returns:
            List of recommended plugins (FULL or USABLE support level).
        """
        return [
            plugin
            for plugin in self.list_plugins(product_type=product_type)
            if plugin.support_level in (SupportLevel.FULL, SupportLevel.USABLE)
        ]

    def _version_less_than(self, version1: str, version2: str) -> bool:
        """
        Compare two version strings.
        
        Args:
            version1: First version string.
            version2: Second version string.
            
        Returns:
            True if version1 < version2.
        """
        try:
            v1_parts = [int(x) for x in version1.lstrip("v").split(".")]
            v2_parts = [int(x) for x in version2.lstrip("v").split(".")]
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return True
                if v1 > v2:
                    return False
            
            return len(v1_parts) < len(v2_parts)
        except (ValueError, AttributeError):
            return False
