"""Plugin runtime registry for managing plugin instances."""

from typing import Dict, List, Optional, Type
from pathlib import Path

from orchestrator.models import ProductType, PluginMetadata, SupportLevel
from orchestrator.plugins.base import BasePlugin, ExecutionContext, ExecutionPath
from orchestrator.compatibility import BUILTIN_PLUGINS


class PluginRegistry:
    """Registry for managing plugin instances and metadata."""
    
    def __init__(self):
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self._plugin_instances: Dict[str, BasePlugin] = {}
        self._metadata: Dict[str, PluginMetadata] = BUILTIN_PLUGINS.copy()
    
    def register_plugin_class(
        self,
        plugin_class: Type[BasePlugin],
        metadata: Optional[PluginMetadata] = None
    ) -> None:
        """
        Register a plugin class.
        
        Args:
            plugin_class: The plugin class to register.
            metadata: Optional plugin metadata.
        """
        instance = plugin_class()
        plugin_name = instance.name
        
        self._plugin_classes[plugin_name] = plugin_class
        
        # If metadata provided, update it
        if metadata:
            self._metadata[plugin_name] = metadata
        elif plugin_name not in self._metadata:
            # Create default metadata from instance
            self._metadata[plugin_name] = PluginMetadata(
                name=instance.name,
                version=instance.version,
                description=f"{instance.name} plugin",
                product_types=[ProductType.WEB],  # Default, should be overridden
                capabilities=[],
                support_level=SupportLevel.FULL,
                dependencies=[],
                min_platform_version="3.0.0",
            )
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get or create a plugin instance.
        
        Args:
            plugin_name: The plugin name.
            
        Returns:
            Plugin instance if found, None otherwise.
        """
        # Return cached instance if available
        if plugin_name in self._plugin_instances:
            return self._plugin_instances[plugin_name]
        
        # Create new instance if class is registered
        if plugin_name in self._plugin_classes:
            instance = self._plugin_classes[plugin_name]()
            self._plugin_instances[plugin_name] = instance
            return instance
        
        return None
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata.
        
        Args:
            plugin_name: The plugin name.
            
        Returns:
            PluginMetadata if found, None otherwise.
        """
        return self._metadata.get(plugin_name)
    
    def list_plugins(
        self,
        product_type: Optional[ProductType] = None,
        execution_path: Optional[ExecutionPath] = None
    ) -> List[PluginMetadata]:
        """
        List available plugins.
        
        Args:
            product_type: Optional product type filter.
            execution_path: Optional execution path filter.
            
        Returns:
            List of matching plugin metadata.
        """
        plugins = list(self._metadata.values())
        
        if product_type:
            plugins = [p for p in plugins if product_type in p.product_types]
        
        if execution_path:
            # Filter by plugins that support the execution path
            supported = []
            for plugin_metadata in plugins:
                plugin = self.get_plugin(plugin_metadata.name)
                if plugin and plugin.supports_execution_path(execution_path):
                    supported.append(plugin_metadata)
            plugins = supported
        
        return plugins
    
    def list_executable_plugins(self) -> List[str]:
        """
        List plugins that have registered execution classes.
        
        Returns:
            List of plugin names that can be executed.
        """
        return list(self._plugin_classes.keys())
    
    def is_plugin_executable(self, plugin_name: str) -> bool:
        """
        Check if a plugin has executable implementation.
        
        Args:
            plugin_name: The plugin name.
            
        Returns:
            True if executable, False otherwise.
        """
        return plugin_name in self._plugin_classes
    
    def get_supported_execution_paths(
        self,
        plugin_name: str
    ) -> List[ExecutionPath]:
        """
        Get supported execution paths for a plugin.
        
        Args:
            plugin_name: The plugin name.
            
        Returns:
            List of supported execution paths.
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.supported_execution_paths
        return []
    
    def validate_plugin_config(
        self,
        plugin_name: str,
        config: dict
    ) -> tuple[bool, List[str]]:
        """
        Validate plugin configuration.
        
        Args:
            plugin_name: The plugin name.
            config: Configuration to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.validate_config(config)
        
        return False, [f"Plugin {plugin_name} not found or not executable"]
    
    def clear_instances(self) -> None:
        """Clear all cached plugin instances."""
        self._plugin_instances.clear()


# Global plugin registry instance
_global_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """
    Get the global plugin registry instance.
    
    Returns:
        The global PluginRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry
