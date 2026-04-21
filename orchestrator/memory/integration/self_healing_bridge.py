from __future__ import annotations

from typing import Optional

from orchestrator.memory.application.engine import FailureMemoryEngine
from orchestrator.memory.domain.models import MemoryResolutionResult


def choose_action_for_self_healing(
    *,
    engine: FailureMemoryEngine,
    resolution: MemoryResolutionResult,
) -> Optional[dict]:
    if not resolution.resolved_memory_id or not resolution.matched_record:
        return None
    return engine.get_best_action(
        memory_id=resolution.resolved_memory_id,
        adapter_id=resolution.matched_record.adapter_id,
    )


def record_self_healing_outcome(
    *,
    engine: FailureMemoryEngine,
    resolution: MemoryResolutionResult,
    action_type: str,
    strategy: str,
    result: str,
    notes: str = "",
) -> Optional[dict]:
    if not resolution.resolved_memory_id or not resolution.matched_record:
        return None
    updated = engine.record_action_outcome(
        memory_id=resolution.resolved_memory_id,
        adapter_id=resolution.matched_record.adapter_id,
        action_type=action_type,
        strategy=strategy,
        result=result,
        notes=notes,
        source="self-healing",
    )
    if not updated:
        return None
    return updated.to_dict()
