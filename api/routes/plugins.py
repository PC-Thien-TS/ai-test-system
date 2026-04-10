"""Plugin API endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_project_service, get_user_context
from orchestrator.models import ProductType

router = APIRouter()


class PluginResponse(BaseModel):
    """Response model for plugin metadata."""
    name: str
    version: str
    description: str
    product_types: List[str]
    capabilities: List[str]
    support_level: str
    dependencies: Optional[List[str]]
    min_platform_version: Optional[str]


class CompatibilitySummaryResponse(BaseModel):
    """Response model for compatibility summary."""
    plugin_name: str
    platform_version: str
    compatible: bool
    support_level: str
    notes: List[str]
    blockers: List[str]


@router.get("", response_model=List[PluginResponse])
async def list_plugins(
    product_type: Optional[ProductType] = None,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    List available plugins.
    
    Args:
        product_type: Optional product type filter.
        
    Returns:
        List of plugins.
    """
    plugins = service.list_plugins(product_type=product_type)
    
    return [
        PluginResponse(
            name=p.name,
            version=p.version,
            description=p.description,
            product_types=[pt.value for pt in p.product_types],
            capabilities=p.capabilities,
            support_level=p.support_level.value,
            dependencies=p.dependencies,
            min_platform_version=p.min_platform_version,
        )
        for p in plugins
    ]


@router.get("/{plugin_name}", response_model=PluginResponse)
async def get_plugin(
    plugin_name: str,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Get plugin metadata by name.
    
    Args:
        plugin_name: The plugin name.
        
    Returns:
        Plugin metadata.
    """
    plugin = service.get_plugin(plugin_name)
    
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_name} not found"
        )
    
    return PluginResponse(
        name=plugin.name,
        version=plugin.version,
        description=plugin.description,
        product_types=[pt.value for pt in plugin.product_types],
        capabilities=plugin.capabilities,
        support_level=plugin.support_level.value,
        dependencies=plugin.dependencies,
        min_platform_version=plugin.min_platform_version,
    )


@router.get("/{plugin_name}/compatibility", response_model=CompatibilitySummaryResponse)
async def get_plugin_compatibility(
    plugin_name: str,
    service = Depends(get_project_service),
    user = Depends(get_user_context),
):
    """
    Analyze plugin compatibility with the platform.
    
    Args:
        plugin_name: The plugin name.
        
    Returns:
        Compatibility summary.
    """
    summary = service.analyze_plugin_compatibility(plugin_name)
    
    return CompatibilitySummaryResponse(
        plugin_name=summary.plugin_name,
        platform_version=summary.platform_version,
        compatible=summary.compatible,
        support_level=summary.support_level.value,
        notes=summary.notes,
        blockers=summary.blockers,
    )
