from __future__ import annotations

from typing import Optional

from orchestrator.decision.domain.models import (
    DecisionPolicyInput,
    DecisionPolicyProfile,
    DecisionPolicyType,
    DecisionStrategy,
)


HIGH_SEVERITIES = {"high", "critical", "p1", "p0"}
CRITICAL_SEVERITIES = {"critical", "p0"}


def severity_level(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw in {"p0", "critical"}:
        return "critical"
    if raw in {"p1", "high"}:
        return "high"
    if raw in {"p2", "medium"}:
        return "medium"
    return "low"


def evaluate_hard_rule(
    value: DecisionPolicyInput,
    profile: DecisionPolicyProfile,
) -> Optional[tuple[DecisionPolicyType, Optional[DecisionStrategy], str]]:
    severity = severity_level(value.severity)
    memory = value.memory_resolution_value

    # Critical repeated exact issue on active/release paths: hard block
    if (
        value.governance_flags.allow_auto_block_release
        and memory == "EXACT_MATCH"
        and severity == "critical"
        and value.occurrence_count >= profile.critical_recurrence_block_count
    ):
        return (
            DecisionPolicyType.BLOCK_RELEASE,
            DecisionStrategy.BLOCK_AND_ESCALATE,
            "Repeated critical exact-match failure exceeded release block recurrence threshold.",
        )

    # Release critical severe issue may block even low recurrence
    if (
        value.governance_flags.allow_auto_block_release
        and value.release_critical
        and severity in {"high", "critical"}
        and value.confidence >= 0.75
        and memory in {"EXACT_MATCH", "SIMILAR_MATCH"}
    ):
        return (
            DecisionPolicyType.BLOCK_RELEASE,
            DecisionStrategy.BLOCK_AND_ESCALATE,
            "Release-critical severe issue with high confidence requires immediate block and escalation.",
        )

    # Ambiguous high-severity but uncertain: never hard-block
    if (
        memory == "AMBIGUOUS_MATCH"
        and severity in {"high", "critical"}
        and value.confidence < profile.ambiguous_manual_review_confidence
    ):
        return (
            DecisionPolicyType.MANUAL_INVESTIGATION,
            DecisionStrategy.INVESTIGATE_BACKEND,
            "Ambiguous high-severity signal with low certainty requires manual investigation, not hard block.",
        )

    # Known flaky suppression for non-critical paths only when governance allows
    if (
        value.governance_flags.allow_auto_suppress
        and value.flaky
        and not value.release_critical
        and severity in {"low", "medium"}
        and value.occurrence_count >= profile.flaky_suppress_recurrence
    ):
        return (
            DecisionPolicyType.SUPPRESS_KNOWN_FLAKY,
            DecisionStrategy.QUARANTINE_TEST,
            "Known flaky non-critical recurring failure eligible for suppression/quarantine under policy.",
        )

    return None


def derive_primary_decision_from_score(
    value: DecisionPolicyInput,
    profile: DecisionPolicyProfile,
    score: float,
) -> DecisionPolicyType:
    severity = severity_level(value.severity)
    if (
        score >= profile.block_threshold
        and value.governance_flags.allow_auto_block_release
        and severity in {"high", "critical"}
    ):
        return DecisionPolicyType.BLOCK_RELEASE
    if score >= profile.escalate_threshold:
        if severity in {"high", "critical"} or value.release_critical:
            return DecisionPolicyType.ESCALATE
        if value.best_action_effectiveness < profile.min_action_effectiveness_for_rerun:
            return DecisionPolicyType.MANUAL_INVESTIGATION
        if value.governance_flags.allow_auto_rerun:
            if value.best_action:
                return DecisionPolicyType.RERUN_WITH_STRATEGY
            return DecisionPolicyType.RERUN
        return DecisionPolicyType.MANUAL_INVESTIGATION
    if score >= profile.rerun_threshold:
        if not value.governance_flags.allow_auto_rerun:
            return DecisionPolicyType.MANUAL_INVESTIGATION
        if value.best_action_effectiveness >= profile.min_action_effectiveness_for_rerun:
            if value.best_action:
                return DecisionPolicyType.RERUN_WITH_STRATEGY
            return DecisionPolicyType.RERUN
        return DecisionPolicyType.MANUAL_INVESTIGATION

    if severity in {"high", "critical"}:
        return DecisionPolicyType.MANUAL_INVESTIGATION
    return DecisionPolicyType.NO_ACTION


def derive_strategy(
    *,
    decision: DecisionPolicyType,
    value: DecisionPolicyInput,
) -> Optional[DecisionStrategy]:
    if decision == DecisionPolicyType.RERUN:
        return DecisionStrategy.RETRY_3X
    if decision == DecisionPolicyType.RERUN_WITH_STRATEGY:
        action = str((value.best_action or {}).get("action_type", "")).strip().lower()
        mapping = {
            "rerun": DecisionStrategy.RETRY_3X,
            "rerun_with_backoff": DecisionStrategy.RETRY_WITH_BACKOFF,
            "increase_timeout": DecisionStrategy.INCREASE_TIMEOUT,
            "isolate_test": DecisionStrategy.ISOLATE_TEST,
            "rerun_subset": DecisionStrategy.RERUN_SUBSET,
            "quarantine_test": DecisionStrategy.QUARANTINE_TEST,
        }
        return mapping.get(action, DecisionStrategy.RETRY_WITH_BACKOFF)
    if decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
        return DecisionStrategy.QUARANTINE_TEST
    if decision == DecisionPolicyType.BLOCK_RELEASE:
        return DecisionStrategy.BLOCK_AND_ESCALATE
    if decision == DecisionPolicyType.ESCALATE:
        plugin = (value.plugin or "").strip().lower()
        if "infra" in plugin:
            return DecisionStrategy.INVESTIGATE_INFRA
        if "data" in plugin:
            return DecisionStrategy.INVESTIGATE_DATA
        return DecisionStrategy.INVESTIGATE_BACKEND
    if decision == DecisionPolicyType.MANUAL_INVESTIGATION:
        return DecisionStrategy.INVESTIGATE_BACKEND
    return None


def derive_bug_candidate(value: DecisionPolicyInput, profile: DecisionPolicyProfile) -> bool:
    severity = severity_level(value.severity)
    if not value.governance_flags.allow_bug_candidate:
        return False
    if severity in {"low"}:
        return False
    return value.occurrence_count >= profile.bug_candidate_recurrence and value.memory_resolution_value != "NEW_MEMORY"


def derive_incident_candidate(value: DecisionPolicyInput, profile: DecisionPolicyProfile) -> bool:
    if not value.governance_flags.allow_incident_candidate:
        return False
    severity = severity_level(value.severity)
    if severity != "critical":
        return False
    if value.occurrence_count < profile.incident_candidate_recurrence:
        return False
    return bool(value.release_critical or value.execution_path.lower() in {"smoke", "release_hardening"})
