from __future__ import annotations

from dataclasses import replace

from orchestrator.self_healing.domain.models import ActionExecutionResult

from ..domain.models import BugCandidateInput, IncidentCandidateInput


def apply_self_healing_to_bug_input(
    bug_input: BugCandidateInput,
    action_result: ActionExecutionResult,
) -> BugCandidateInput:
    return replace(
        bug_input,
        self_healing_result=action_result,
        metadata={
            **bug_input.metadata,
            "self_healing_action_id": action_result.action_id,
            "self_healing_success": action_result.success,
            "self_healing_attempts": action_result.attempts_used,
        },
    )


def apply_self_healing_to_incident_input(
    incident_input: IncidentCandidateInput,
    action_result: ActionExecutionResult,
) -> IncidentCandidateInput:
    return replace(
        incident_input,
        self_healing_result=action_result,
        metadata={
            **incident_input.metadata,
            "self_healing_action_id": action_result.action_id,
            "self_healing_success": action_result.success,
            "self_healing_attempts": action_result.attempts_used,
        },
    )

