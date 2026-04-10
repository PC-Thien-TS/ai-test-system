"""Plugin executor layer for running plugins with orchestration."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from orchestrator.models import ExecutionPath, Run
from orchestrator.plugins.base import (
    BasePlugin,
    ExecutionContext,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.registry import PluginRegistry


class PluginExecutionError(Exception):
    """Exception raised when plugin execution fails."""
    pass


class PluginExecutor:
    """Executes plugins with orchestration and error handling."""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """
        Initialize the plugin executor.
        
        Args:
            registry: Optional plugin registry. If not provided, uses global registry.
        """
        self.registry = registry or PluginRegistry()
        self._active_executions: Dict[str, asyncio.Task] = {}
    
    async def execute_plugin(
        self,
        plugin_name: str,
        context: ExecutionContext,
        timeout_seconds: Optional[int] = None,
    ) -> PluginExecutionResult:
        """
        Execute a single plugin.
        
        Args:
            plugin_name: The plugin name to execute.
            context: Execution context.
            timeout_seconds: Optional timeout in seconds.
            
        Returns:
            PluginExecutionResult with execution results.
            
        Raises:
            PluginExecutionError: If plugin execution fails critically.
        """
        plugin = self.registry.get_plugin(plugin_name)
        
        if not plugin:
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=ExecutionStatus.FAILED,
                success=False,
                error_message=f"Plugin {plugin_name} not found or not executable",
                error_details={"reason": "plugin_not_found"},
            )
        
        # Validate plugin supports execution path
        if not plugin.supports_execution_path(context.execution_path):
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=ExecutionStatus.SKIPPED,
                success=False,
                error_message=f"Plugin {plugin_name} does not support execution path {context.execution_path.value}",
                error_details={"reason": "unsupported_execution_path"},
            )
        
        # Validate configuration
        is_valid, errors = await plugin.validate_config(context.config)
        if not is_valid:
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=ExecutionStatus.FAILED,
                success=False,
                error_message=f"Plugin configuration validation failed",
                error_details={"validation_errors": errors},
            )
        
        result = PluginExecutionResult(
            plugin_name=plugin_name,
            status=ExecutionStatus.RUNNING,
            success=False,
        )
        
        try:
            # Initialize plugin
            init_success = await plugin.initialize(context)
            if not init_success:
                result.status = ExecutionStatus.FAILED
                result.error_message = "Plugin initialization failed"
                result.mark_completed()
                return result
            
            # Execute with timeout if specified
            if timeout_seconds:
                result = await asyncio.wait_for(
                    plugin.execute(context),
                    timeout=timeout_seconds
                )
            else:
                result = await plugin.execute(context)
            
            # Cleanup
            await plugin.cleanup(context)
            
        except asyncio.TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.success = False
            result.error_message = f"Plugin execution timed out after {timeout_seconds}s"
            result.error_details = {"timeout": timeout_seconds}
            await plugin.cleanup(context)
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.success = False
            result.error_message = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            try:
                await plugin.cleanup(context)
            except Exception:
                pass  # Ignore cleanup errors
        
        result.mark_completed()
        return result
    
    async def execute_plugins(
        self,
        plugin_names: List[str],
        context: ExecutionContext,
        parallel: bool = True,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, PluginExecutionResult]:
        """
        Execute multiple plugins.
        
        Args:
            plugin_names: List of plugin names to execute.
            context: Execution context.
            parallel: Whether to execute plugins in parallel.
            timeout_seconds: Optional timeout in seconds per plugin.
            
        Returns:
            Dictionary mapping plugin names to execution results.
        """
        results = {}
        
        if parallel:
            # Execute all plugins in parallel
            tasks = [
                self.execute_plugin(name, context, timeout_seconds)
                for name in plugin_names
            ]
            plugin_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, result in zip(plugin_names, plugin_results):
                if isinstance(result, Exception):
                    results[name] = PluginExecutionResult(
                        plugin_name=name,
                        status=ExecutionStatus.FAILED,
                        success=False,
                        error_message=str(result),
                        error_details={"exception_type": type(result).__name__},
                    )
                else:
                    results[name] = result
        else:
            # Execute plugins sequentially
            for name in plugin_names:
                results[name] = await self.execute_plugin(name, context, timeout_seconds)
        
        return results
    
    async def execute_plugin_with_retry(
        self,
        plugin_name: str,
        context: ExecutionContext,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        timeout_seconds: Optional[int] = None,
    ) -> PluginExecutionResult:
        """
        Execute a plugin with retry logic.
        
        Args:
            plugin_name: The plugin name to execute.
            context: Execution context.
            max_retries: Maximum number of retry attempts.
            retry_delay_seconds: Delay between retries in seconds.
            timeout_seconds: Optional timeout in seconds per attempt.
            
        Returns:
            PluginExecutionResult with execution results.
        """
        last_result = None
        
        for attempt in range(max_retries + 1):
            context.retry_count = attempt
            context.max_retries = max_retries
            
            result = await self.execute_plugin(plugin_name, context, timeout_seconds)
            last_result = result
            
            # If successful, return immediately
            if result.success:
                return result
            
            # If not the last attempt, wait before retry
            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds)
        
        # All retries exhausted
        return last_result
    
    def cancel_execution(self, run_id: str) -> bool:
        """
        Cancel an active plugin execution for a run.
        
        Args:
            run_id: The run ID to cancel.
            
        Returns:
            True if cancellation was successful, False otherwise.
        """
        if run_id in self._active_executions:
            task = self._active_executions[run_id]
            task.cancel()
            del self._active_executions[run_id]
            return True
        return False
    
    def get_active_executions(self) -> List[str]:
        """
        Get list of run IDs with active executions.
        
        Returns:
            List of run IDs.
        """
        return list(self._active_executions.keys())
