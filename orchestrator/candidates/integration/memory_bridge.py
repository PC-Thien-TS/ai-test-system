from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..domain.models import BugCandidateInput, IncidentCandidateInput


def apply_memory_context_to_bug_input(
    bug_input: BugCandidateInput,
    memory_resolution_result: Any,
) -> BugCandidateInput:
    if memory_resolution_result is None:
        return bug_input
    memory_id = getattr(memory_resolution_result, "resolved_memory_id", "") or bug_input.memory_id
    signature_hash = getattr(memory_resolution_result, "signature_hash", "") or bug_input.signature_hash
    confidence = float(getattr(memory_resolution_result, "confidence", bug_input.confidence))
    occurrence_count = int(getattr(memory_resolution_result, "occurrence_count", bug_input.occurrence_count))
    resolution_type = getattr(memory_resolution_result, "resolution_type", bug_input.memory_resolution_type)
    return replace(
        bug_input,
        memory_id=memory_id,
        signature_hash=signature_hash,
        confidence=confidence,
        occurrence_count=occurrence_count,
        memory_resolution_type=str(resolution_type),
    )


def apply_memory_context_to_incident_input(
    incident_input: IncidentCandidateInput,
    memory_resolution_result: Any,
) -> IncidentCandidateInput:
    if memory_resolution_result is None:
        return incident_input
    memory_id = getattr(memory_resolution_result, "resolved_memory_id", "") or incident_input.memory_id
    signature_hash = getattr(memory_resolution_result, "signature_hash", "") or incident_input.signature_hash
    confidence = float(getattr(memory_resolution_result, "confidence", incident_input.confidence))
    occurrence_count = int(getattr(memory_resolution_result, "occurrence_count", incident_input.occurrence_count))
    resolution_type = getattr(memory_resolution_result, "resolution_type", incident_input.memory_resolution_type)
    return replace(
        incident_input,
        memory_id=memory_id,
        signature_hash=signature_hash,
        confidence=confidence,
        occurrence_count=occurrence_count,
        memory_resolution_type=str(resolution_type),
    )

