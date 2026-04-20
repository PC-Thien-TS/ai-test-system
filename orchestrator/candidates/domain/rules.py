from __future__ import annotations

from typing import List, Tuple

from orchestrator.decision.domain.models import MemoryResolutionType

from .models import (
    BugCandidateInput,
    CandidateConfig,
    CandidateGovernanceFlags,
    IncidentCandidateInput,
)


def _resolution_type(input_obj: BugCandidateInput | IncidentCandidateInput) -> str:
    return str(input_obj.memory_resolution_type or "").upper()


def evaluate_bug_candidate_eligibility(
    input_obj: BugCandidateInput,
    config: CandidateConfig,
    governance: CandidateGovernanceFlags,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    eligible = True

    if not config.bug_auto_generation_enabled:
        return False, ["Bug auto generation is disabled by configuration."]
    if not governance.allow_bug_generation:
        return False, ["Bug generation disabled by governance."]

    if input_obj.occurrence_count < config.bug_min_occurrences:
        eligible = False
        reasons.append("Recurrence threshold not met for bug generation.")
    if input_obj.confidence < config.bug_min_confidence:
        eligible = False
        reasons.append("Confidence below bug generation minimum.")

    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    if severity_rank.get(input_obj.severity.lower(), 0) < severity_rank["medium"]:
        eligible = False
        reasons.append("Severity below bug generation minimum (medium).")

    resolution = _resolution_type(input_obj)
    if resolution == MemoryResolutionType.AMBIGUOUS_MATCH.value and governance.require_manual_review_for_ambiguous:
        eligible = False
        reasons.append("Ambiguous memory match requires manual review.")
    if resolution == MemoryResolutionType.SIMILAR_MATCH.value:
        if not config.bug_allow_similar_match:
            eligible = False
            reasons.append("Similar-match bug generation disabled by config.")
        if not governance.allow_generation_on_similar_match_only:
            eligible = False
            reasons.append("Governance disallows auto-generation from similar matches.")

    if input_obj.flaky:
        eligible = False
        reasons.append("Known flaky/noise issue; bug candidate suppressed.")

    if input_obj.decision_result is not None:
        primary = input_obj.decision_result.primary_decision.value
        if primary == "SUPPRESS_KNOWN_FLAKY":
            eligible = False
            reasons.append("Decision policy selected flaky suppression.")
    if input_obj.self_healing_result is not None and input_obj.self_healing_result.success:
        if input_obj.occurrence_count <= (config.bug_min_occurrences + 1):
            eligible = False
            reasons.append("Self-healing succeeded; candidate urgency reduced below generation threshold.")

    if not reasons and eligible:
        reasons.append("Recurring meaningful non-transient signal is bug-candidate eligible.")
    return eligible, reasons


def evaluate_incident_candidate_eligibility(
    input_obj: IncidentCandidateInput,
    config: CandidateConfig,
    governance: CandidateGovernanceFlags,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    eligible = True

    if not config.incident_auto_generation_enabled:
        return False, ["Incident auto generation is disabled by configuration."]
    if not governance.allow_incident_generation:
        return False, ["Incident generation disabled by governance."]

    if input_obj.occurrence_count < config.incident_min_occurrences:
        eligible = False
        reasons.append("Incident recurrence threshold not met.")
    if input_obj.confidence < config.incident_min_confidence:
        eligible = False
        reasons.append("Confidence below incident minimum.")

    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    if severity_rank.get(input_obj.severity.lower(), 0) < severity_rank["high"]:
        eligible = False
        reasons.append("Incident severity must be high or critical.")

    resolution = _resolution_type(input_obj)
    if resolution == MemoryResolutionType.AMBIGUOUS_MATCH.value:
        eligible = False
        reasons.append("Ambiguous match cannot auto-generate incident.")

    if config.incident_require_release_critical and not (input_obj.release_critical or input_obj.protected_path):
        eligible = False
        reasons.append("Incident requires release-critical or protected-path impact.")

    if input_obj.flaky:
        eligible = False
        reasons.append("Flaky issue cannot auto-generate incident.")

    if input_obj.self_healing_result is not None and input_obj.self_healing_result.success:
        eligible = False
        reasons.append("Self-healing succeeded; no active incident candidate required.")

    if input_obj.decision_result is not None:
        d = input_obj.decision_result
        if not (d.should_block_release or d.should_escalate or d.should_open_incident_candidate):
            eligible = False
            reasons.append("Decision policy did not indicate strong escalation/block signal for incident.")

    if not reasons and eligible:
        reasons.append("Critical recurring release-impacting pattern is incident-candidate eligible.")
    return eligible, reasons

