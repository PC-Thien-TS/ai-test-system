"""Plugin executor layer for running plugins with orchestration."""

import asyncio
import inspect
from typing import Dict, List, Optional

from orchestrator.plugins.base import (
    ExecutionContext,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.registry import PluginRegistry


class PluginExecutionError(Exception):
    """Exception raised when plugin execution fails."""


class PluginExecutor:
    """Executes plugins with orchestration and error handling."""

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or PluginRegistry()
        self._active_executions: Dict[str, asyncio.Task] = {}

    def _run_sync(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "Cannot run sync plugin executor API inside an active event loop. "
            "Use execute_plugin_async/execute_plugins_async methods instead."
        )

    def execute_plugin(
        self,
        plugin_name: str,
        context: ExecutionContext,
        timeout_seconds: Optional[int] = None,
    ) -> PluginExecutionResult:
        """Synchronous compatibility wrapper for single plugin execution."""
        return self._run_sync(
            self.execute_plugin_async(
                plugin_name=plugin_name,
                context=context,
                timeout_seconds=timeout_seconds,
            )
        )

    async def execute_plugin_async(
        self,
        plugin_name: str,
        context: ExecutionContext,
        timeout_seconds: Optional[int] = None,
    ) -> PluginExecutionResult:
        """Execute a single plugin asynchronously."""
        plugin = self.registry.get_plugin(plugin_name)

        if not plugin:
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=ExecutionStatus.FAILED,
                success=False,
                error_message=f"Plugin {plugin_name} not found or not executable",
                error_details={"reason": "plugin_not_found"},
            )

        if not plugin.supports_execution_path(context.execution_path):
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=ExecutionStatus.SKIPPED,
                success=False,
                error_message=(
                    f"Plugin {plugin_name} does not support execution path "
                    f"{context.execution_path.value}"
                ),
                error_details={"reason": "unsupported_execution_path"},
            )

        validation_result = plugin.validate_config(context.config)
        if inspect.isawaitable(validation_result):
            is_valid, errors = await validation_result
        else:
            is_valid, errors = validation_result

        if not is_valid:
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=ExecutionStatus.FAILED,
                success=False,
                error_message="Plugin configuration validation failed",
                error_details={"validation_errors": errors},
            )

        result = PluginExecutionResult(
            plugin_name=plugin_name,
            status=ExecutionStatus.RUNNING,
            success=False,
        )

        try:
            init_success = await plugin.initialize(context)
            if not init_success:
                result.status = ExecutionStatus.FAILED
                result.error_message = "Plugin initialization failed"
                result.mark_completed()
                return result

            if timeout_seconds:
                result = await asyncio.wait_for(
                    plugin.execute(context),
                    timeout=timeout_seconds,
                )
            else:
                result = await plugin.execute(context)

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
                pass

        result.mark_completed()
        return result

    def execute_plugins(
        self,
        plugin_names: List[str],
        context: ExecutionContext,
        parallel: bool = True,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, PluginExecutionResult]:
        """Synchronous compatibility wrapper for multi-plugin execution."""
        return self._run_sync(
            self.execute_plugins_async(
                plugin_names=plugin_names,
                context=context,
                parallel=parallel,
                timeout_seconds=timeout_seconds,
            )
        )

    async def execute_plugins_async(
        self,
        plugin_names: List[str],
        context: ExecutionContext,
        parallel: bool = True,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, PluginExecutionResult]:
        """Execute multiple plugins asynchronously."""
        results: Dict[str, PluginExecutionResult] = {}

        if parallel:
            tasks = [
                self.execute_plugin_async(name, context, timeout_seconds)
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
            for name in plugin_names:
                results[name] = await self.execute_plugin_async(name, context, timeout_seconds)

        return results

    def execute_plugin_with_retry(
        self,
        plugin_name: str,
        context: ExecutionContext,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        timeout_seconds: Optional[int] = None,
    ) -> PluginExecutionResult:
        """Synchronous compatibility wrapper for retry execution."""
        return self._run_sync(
            self.execute_plugin_with_retry_async(
                plugin_name=plugin_name,
                context=context,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                timeout_seconds=timeout_seconds,
            )
        )

    async def execute_plugin_with_retry_async(
        self,
        plugin_name: str,
        context: ExecutionContext,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        timeout_seconds: Optional[int] = None,
    ) -> PluginExecutionResult:
        """Execute plugin with retry logic asynchronously."""
        last_result: Optional[PluginExecutionResult] = None

        for attempt in range(max_retries + 1):
            context.retry_count = attempt
            context.max_retries = max_retries

            result = await self.execute_plugin_async(plugin_name, context, timeout_seconds)
            last_result = result

            if result.success:
                return result

            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds)

        return last_result

    def cancel_execution(self, run_id: str) -> bool:
        """Cancel an active plugin execution for a run."""
        if run_id in self._active_executions:
            task = self._active_executions[run_id]
            task.cancel()
            del self._active_executions[run_id]
            return True
        return False

    def get_active_executions(self) -> List[str]:
        """Get list of run IDs with active executions."""
        return list(self._active_executions.keys())
