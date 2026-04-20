from __future__ import annotations

from typing import Optional

from orchestrator.memory.application.engine import FailureMemoryEngine
from orchestrator.memory.domain.models import IncomingFailureRecord, MemoryResolutionResult


def build_triage_memory_context(
    *,
    engine: FailureMemoryEngine,
    incoming: IncomingFailureRecord,
) -> dict:
    resolution = engine.resolve_failure(incoming)
    context = engine.build_memory_context(resolution=resolution)
    return {
        "resolution": resolution.to_dict(),
        "memory_context": context,
        "triage_hint": (
            "Reuse historical root cause with confidence boost."
            if resolution.resolution_type.value == "EXACT_MATCH"
            else "Use similar memory candidates to enrich triage prompt."
            if resolution.resolution_type.value in {"SIMILAR_MATCH", "AMBIGUOUS_MATCH"}
            else "No memory hit; run full triage and create new memory."
        ),
    }


def update_memory_after_triage(
    *,
    engine: FailureMemoryEngine,
    incoming: IncomingFailureRecord,
    triage_root_cause: str,
    triage_confidence: float,
    recommended_actions: Optional[list[str]] = None,
) -> MemoryResolutionResult:
    patched = IncomingFailureRecord(
        adapter_id=incoming.adapter_id,
        project_id=incoming.project_id,
        plugin=incoming.plugin,
        error_type=incoming.error_type,
        endpoint=incoming.endpoint,
        stack_trace=incoming.stack_trace,
        message=incoming.message,
        severity_hint=incoming.severity_hint,
        triage_root_cause=triage_root_cause,
        triage_confidence=triage_confidence,
        recommended_actions=list(recommended_actions or incoming.recommended_actions),
        metadata=dict(incoming.metadata),
        component=incoming.component,
        fingerprint=incoming.fingerprint,
    )
    return engine.resolve_failure(patched)
