"""Plugin execution framework."""

from orchestrator.plugins.base import (
    BasePlugin,
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.executor import PluginExecutor, PluginExecutionError
from orchestrator.plugins.registry import PluginRegistry, get_plugin_registry

__all__ = [
    "BasePlugin",
    "ExecutionContext",
    "EvidenceItem",
    "EvidenceType",
    "ExecutionStatus",
    "PluginExecutionResult",
    "PluginExecutor",
    "PluginExecutionError",
    "PluginRegistry",
    "get_plugin_registry",
]
