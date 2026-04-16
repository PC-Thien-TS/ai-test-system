from __future__ import annotations

from orchestrator.adapters.base.models import FlowDefinition


FLOW_REGISTRY: dict[str, FlowDefinition] = {
{{FLOW_REGISTRY_ENTRIES}}
}

FLOW_ORDER: tuple[str, ...] = (
{{FLOW_ORDER_ENTRIES}}
)

CORE_ANCHOR_FLOWS: tuple[str, ...] = (
{{CORE_ANCHOR_ENTRIES}}
)

RELEASE_CRITICAL_FLOWS: tuple[str, ...] = (
{{RELEASE_CRITICAL_ENTRIES}}
)

