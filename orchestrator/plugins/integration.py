"""Integration layer for plugin executor with run orchestration."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.models import ExecutionPath, Run, RunStatus
from orchestrator.plugins.base import (
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    PluginExecutionResult,
)
from orchestrator.plugins.executor import PluginExecutor
from orchestrator.plugins.playwright import PlaywrightPlugin
from orchestrator.plugins.api_contract import ApiContractPlugin
from orchestrator.plugins.registry import PluginRegistry, get_plugin_registry


class PluginOrchestrator:
    """Integrates plugin execution with run orchestration."""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """
        Initialize the plugin orchestrator.
        
        Args:
            registry: Optional plugin registry. If not provided, uses global registry.
        """
        self.registry = registry or get_plugin_registry()
        self.executor = PluginExecutor(self.registry)
        
        # Register built-in plugins
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """Register built-in executable plugins."""
        # Register Playwright plugin
        self.registry.register_plugin_class(PlaywrightPlugin)
        # Register API Contract plugin
        self.registry.register_plugin_class(ApiContractPlugin)
    
    async def execute_run_plugins(
        self,
        run: Run,
        plugin_names: List[str],
        config_overrides: Optional[Dict] = None,
        parallel: bool = True,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, PluginExecutionResult]:
        """
        Execute plugins for a run.
        
        Args:
            run: The run being executed.
            plugin_names: List of plugin names to execute.
            config_overrides: Optional configuration overrides per plugin.
            parallel: Whether to execute plugins in parallel.
            timeout_seconds: Optional timeout in seconds per plugin.
            
        Returns:
            Dictionary mapping plugin names to execution results.
        """
        # Create execution context
        context = ExecutionContext(
            run_id=run.run_id,
            project_id=run.project_id,
            execution_path=run.execution_path,
            output_path=run.output_path,
            config=config_overrides or {},
            metadata={"run_metadata": run.metadata},
            timeout_seconds=timeout_seconds,
        )
        
        # Execute plugins
        results = await self.executor.execute_plugins(
            plugin_names=plugin_names,
            context=context,
            parallel=parallel,
            timeout_seconds=timeout_seconds,
        )
        
        return results
    
    def convert_results_to_evidence(
        self,
        results: Dict[str, PluginExecutionResult]
    ) -> Dict[str, List[EvidenceItem]]:
        """
        Convert plugin execution results to evidence format.
        
        Args:
            results: Plugin execution results.
            
        Returns:
            Dictionary mapping plugin names to evidence items.
        """
        evidence_by_plugin = {}
        
        for plugin_name, result in results.items():
            evidence_by_plugin[plugin_name] = result.evidence
        
        return evidence_by_plugin
    
    def calculate_plugin_metrics(
        self,
        results: Dict[str, PluginExecutionResult]
    ) -> Dict[str, Dict]:
        """
        Calculate aggregate metrics from plugin results.
        
        Args:
            results: Plugin execution results.
            
        Returns:
            Dictionary of metrics by plugin.
        """
        metrics_by_plugin = {}
        
        for plugin_name, result in results.items():
            metrics_by_plugin[plugin_name] = {
                "success": result.success,
                "status": result.status.value,
                "duration_seconds": result.duration_seconds,
                "evidence_count": len(result.evidence),
                "metrics": result.metrics,
            }
        
        return metrics_by_plugin
    
    def get_fallback_ratio(
        self,
        results: Dict[str, PluginExecutionResult]
    ) -> float:
        """
        Calculate fallback ratio from plugin results.
        
        Args:
            results: Plugin execution results.
            
        Returns:
            Fallback ratio (0.0 to 1.0).
        """
        if not results:
            return 0.0
        
        total = len(results)
        fallback_count = sum(
            1 for result in results.values()
            if not result.success or result.status.value in ["failed", "timeout"]
        )
        
        return fallback_count / total if total > 0 else 0.0
    
    def get_confidence_score(
        self,
        results: Dict[str, PluginExecutionResult]
    ) -> float:
        """
        Calculate confidence score from plugin results.
        
        Args:
            results: Plugin execution results.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        if not results:
            return 0.5
        
        total = len(results)
        successful = sum(
            1 for result in results.values()
            if result.success
        )
        
        return successful / total if total > 0 else 0.0
    
    def get_real_execution_ratio(
        self,
        results: Dict[str, PluginExecutionResult]
    ) -> float:
        """
        Calculate real execution ratio from plugin results.
        
        Args:
            results: Plugin execution results.
            
        Returns:
            Real execution ratio (0.0 to 1.0).
        """
        if not results:
            return 0.0
        
        total = len(results)
        real_executed = sum(
            1 for result in results.values()
            if result.status.value == "completed" and result.success
        )
        
        return real_executed / total if total > 0 else 0.0


def initialize_plugin_system():
    """
    Initialize the plugin system with built-in plugins.
    
    This should be called during application startup.
    """
    registry = get_plugin_registry()
    
    # Register Playwright plugin
    registry.register_plugin_class(PlaywrightPlugin)
    # Register API Contract plugin
    registry.register_plugin_class(ApiContractPlugin)
    
    return registry
