from __future__ import annotations

from dataclasses import replace

from orchestrator.decision.domain.models import DecisionPolicyResult

from ..domain.models import BugCandidateInput, IncidentCandidateInput


def apply_decision_to_bug_input(
    bug_input: BugCandidateInput,
    decision_result: DecisionPolicyResult,
) -> BugCandidateInput:
    return replace(
        bug_input,
        decision_result=decision_result,
        confidence=max(bug_input.confidence, decision_result.confidence),
        metadata={
            **bug_input.metadata,
            "decision_primary": decision_result.primary_decision.value,
            "decision_score": decision_result.decision_score,
        },
    )


def apply_decision_to_incident_input(
    incident_input: IncidentCandidateInput,
    decision_result: DecisionPolicyResult,
) -> IncidentCandidateInput:
    return replace(
        incident_input,
        decision_result=decision_result,
        confidence=max(incident_input.confidence, decision_result.confidence),
        metadata={
            **incident_input.metadata,
            "decision_primary": decision_result.primary_decision.value,
            "decision_score": decision_result.decision_score,
        },
    )

