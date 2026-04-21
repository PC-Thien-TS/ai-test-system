from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import (
    DecisionPolicyInput,
    DecisionPolicyProfile,
    DecisionPolicyType,
    DecisionStrategy,
    GovernanceFlags,
    MemoryResolutionType,
    SeverityLevel,
    clamp01,
    historical_action_effectiveness,
    rerun_history_counts,
    rerun_success_rate,
    seen_count,
)


@dataclass
class HardRuleOutcome:
    decision: DecisionPolicyType
    rationale: str
    strategy: Optional[DecisionStrategy] = None


def evaluate_hard_rule(
    input_data: DecisionPolicyInput,
    governance: GovernanceFlags,
    profile: DecisionPolicyProfile,
    *,
    combined_confidence: float,
) -> Optional[HardRuleOutcome]:
    severity = input_data.severity_level()
    resolution = input_data.resolution_type()

    critical_repeat = (
        resolution == MemoryResolutionType.EXACT_MATCH
        and severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
        and input_data.occurrence_count >= profile.critical_recurrence_block_count
        and combined_confidence >= 0.70
    )
    if critical_repeat:
        if governance.allow_auto_block_release:
            return HardRuleOutcome(
                decision=DecisionPolicyType.BLOCK_RELEASE,
                rationale="Repeated high/critical exact-match failure crossed recurrence threshold.",
                strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
            )
        return HardRuleOutcome(
            decision=DecisionPolicyType.ESCALATE,
            rationale="Repeated high/critical exact-match failure requires escalation (auto-block disabled).",
            strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
        )

    critical_path_severe = (
        input_data.release_critical
        and severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
        and combined_confidence >= 0.80
        and resolution != MemoryResolutionType.AMBIGUOUS_MATCH
    )
    if critical_path_severe and governance.allow_auto_block_release:
        return HardRuleOutcome(
            decision=DecisionPolicyType.BLOCK_RELEASE,
            rationale="Release-critical severe issue with high confidence.",
            strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
        )

    if resolution == MemoryResolutionType.AMBIGUOUS_MATCH and severity in {
        SeverityLevel.HIGH,
        SeverityLevel.CRITICAL,
    }:
        if combined_confidence < 0.70:
            return HardRuleOutcome(
                decision=DecisionPolicyType.MANUAL_INVESTIGATION,
                rationale="Ambiguous severe signal with low certainty; manual verification required.",
                strategy=DecisionStrategy.INVESTIGATE_BACKEND,
            )

    if (
        input_data.flaky
        and severity in {SeverityLevel.LOW, SeverityLevel.MEDIUM}
        and not input_data.release_critical
        and not input_data.protected_path
        and seen_count(input_data) >= 3
        and rerun_success_rate(input_data) is None
        and governance.allow_auto_suppress
    ):
        return HardRuleOutcome(
            decision=DecisionPolicyType.SUPPRESS_KNOWN_FLAKY,
            rationale="Repeated non-critical flaky signal is stable enough for suppression when rerun history is unavailable.",
            strategy=DecisionStrategy.QUARANTINE_TEST,
        )

    if severity == SeverityLevel.CRITICAL and governance.require_manual_review_on_critical:
        return HardRuleOutcome(
            decision=DecisionPolicyType.MANUAL_INVESTIGATION,
            rationale="Critical issue requires manual review by governance rule.",
            strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
        )

    return None


def _rerun_recommended_decision(input_data: DecisionPolicyInput, governance: GovernanceFlags) -> DecisionPolicyType:
    if not governance.allow_auto_rerun:
        return DecisionPolicyType.ESCALATE
    if input_data.best_action:
        return DecisionPolicyType.RERUN_WITH_STRATEGY
    return DecisionPolicyType.RERUN


def _low_rerun_effectiveness_decision(
    input_data: DecisionPolicyInput,
    governance: GovernanceFlags,
) -> DecisionPolicyType:
    severity = input_data.severity_level()
    high_risk = severity == SeverityLevel.CRITICAL or (
        severity == SeverityLevel.HIGH and (input_data.release_critical or input_data.protected_path)
    )
    if high_risk and governance.allow_auto_block_release:
        return DecisionPolicyType.BLOCK_RELEASE
    return DecisionPolicyType.ESCALATE


def _can_auto_suppress(input_data: DecisionPolicyInput, governance: GovernanceFlags) -> bool:
    return (
        governance.allow_auto_suppress
        and input_data.severity_level() in {SeverityLevel.LOW, SeverityLevel.MEDIUM}
        and not input_data.release_critical
        and not input_data.protected_path
    )


def evaluate_memory_policy(
    input_data: DecisionPolicyInput,
    governance: GovernanceFlags,
    profile: DecisionPolicyProfile,
) -> Optional[HardRuleOutcome]:
    current_seen_count = seen_count(input_data)
    success_rate = rerun_success_rate(input_data)

    if current_seen_count <= 1:
        if not input_data.flaky:
            return None
        if input_data.severity_level() in {SeverityLevel.HIGH, SeverityLevel.CRITICAL} or input_data.release_critical or input_data.protected_path:
            return HardRuleOutcome(
                decision=_low_rerun_effectiveness_decision(input_data, governance),
                rationale="First observed flaky occurrence should not be suppressed; escalate instead of suppressing early.",
                strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
            )
        return HardRuleOutcome(
            decision=_rerun_recommended_decision(input_data, governance),
            rationale="First observed flaky occurrence should not be suppressed; recommend rerun while evidence is still limited.",
        )

    if success_rate is not None:
        if success_rate >= 0.80 and _can_auto_suppress(input_data, governance):
            if current_seen_count >= 3:
                return HardRuleOutcome(
                    decision=DecisionPolicyType.SUPPRESS_KNOWN_FLAKY,
                    rationale="Strong flaky signal detected: repeated failures with very high rerun success rate.",
                    strategy=DecisionStrategy.QUARANTINE_TEST,
                )
            return HardRuleOutcome(
                decision=DecisionPolicyType.SUPPRESS_KNOWN_FLAKY,
                rationale="Repeated failure shows consistently high rerun success rate; suppress and monitor.",
                strategy=DecisionStrategy.QUARANTINE_TEST,
            )

        if success_rate < 0.50:
            return HardRuleOutcome(
                decision=_low_rerun_effectiveness_decision(input_data, governance),
                rationale="Repeated failure shows poor rerun success history; escalate instead of rerunning repeatedly.",
                strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
            )

        return HardRuleOutcome(
            decision=_rerun_recommended_decision(input_data, governance),
            rationale="Repeated failure has mixed rerun history; rerun remains recommended.",
        )

    if current_seen_count >= 3 and _can_auto_suppress(input_data, governance) and input_data.flaky:
        return HardRuleOutcome(
            decision=DecisionPolicyType.SUPPRESS_KNOWN_FLAKY,
            rationale="Repeated flaky signal reached suppression threshold even without explicit rerun history.",
            strategy=DecisionStrategy.QUARANTINE_TEST,
        )

    return None


def derive_primary_decision_from_score(
    input_data: DecisionPolicyInput,
    governance: GovernanceFlags,
    profile: DecisionPolicyProfile,
    *,
    decision_score: float,
) -> DecisionPolicyType:
    severity = input_data.severity_level()

    if decision_score >= profile.block_threshold:
        if governance.allow_auto_block_release and input_data.resolution_type() != MemoryResolutionType.AMBIGUOUS_MATCH:
            return DecisionPolicyType.BLOCK_RELEASE
        return DecisionPolicyType.ESCALATE

    if decision_score >= profile.escalate_threshold:
        return DecisionPolicyType.ESCALATE

    if decision_score >= profile.rerun_threshold:
        if not governance.allow_auto_rerun:
            return DecisionPolicyType.MANUAL_INVESTIGATION

        effectiveness = historical_action_effectiveness(input_data)
        if effectiveness >= profile.min_action_effectiveness_for_rerun:
            if input_data.best_action:
                return DecisionPolicyType.RERUN_WITH_STRATEGY
            return DecisionPolicyType.RERUN
        return DecisionPolicyType.MANUAL_INVESTIGATION

    if (
        input_data.flaky
        and governance.allow_auto_suppress
        and severity in {SeverityLevel.LOW, SeverityLevel.MEDIUM}
        and not input_data.release_critical
        and not input_data.protected_path
        and seen_count(input_data) >= 3
    ):
        return DecisionPolicyType.SUPPRESS_KNOWN_FLAKY

    if input_data.resolution_type() == MemoryResolutionType.AMBIGUOUS_MATCH:
        return DecisionPolicyType.MANUAL_INVESTIGATION

    return DecisionPolicyType.NO_ACTION


def _to_strategy(action_name: Optional[str]) -> Optional[DecisionStrategy]:
    if not action_name:
        return None
    for strategy in DecisionStrategy:
        if strategy.value == action_name:
            return strategy
    return None


def derive_strategy(input_data: DecisionPolicyInput, decision: DecisionPolicyType) -> Optional[DecisionStrategy]:
    explicit = _to_strategy(input_data.best_action)
    if decision == DecisionPolicyType.RERUN_WITH_STRATEGY:
        if explicit:
            return explicit
        if historical_action_effectiveness(input_data) >= 0.70:
            return DecisionStrategy.RETRY_WITH_BACKOFF
        return DecisionStrategy.RETRY_3X

    if decision == DecisionPolicyType.RERUN:
        return DecisionStrategy.RETRY_3X

    if decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
        return DecisionStrategy.QUARANTINE_TEST

    if decision == DecisionPolicyType.BLOCK_RELEASE:
        return DecisionStrategy.BLOCK_AND_ESCALATE

    if decision in {DecisionPolicyType.ESCALATE, DecisionPolicyType.MANUAL_INVESTIGATION}:
        domain = str(input_data.metadata.get("failure_domain", "")).lower()
        if "infra" in domain or "network" in domain or "timeout" in domain:
            return DecisionStrategy.INVESTIGATE_INFRA
        if "data" in domain or "seed" in domain:
            return DecisionStrategy.INVESTIGATE_DATA
        return DecisionStrategy.INVESTIGATE_BACKEND

    return None


def derive_bug_candidate(
    input_data: DecisionPolicyInput,
    governance: GovernanceFlags,
    profile: DecisionPolicyProfile,
    *,
    combined_confidence: float,
) -> bool:
    if not governance.allow_bug_candidate:
        return False
    if input_data.flaky:
        return False
    if input_data.occurrence_count < profile.bug_candidate_min_occurrences:
        return False
    if input_data.resolution_type() not in {MemoryResolutionType.EXACT_MATCH, MemoryResolutionType.SIMILAR_MATCH}:
        return False
    return input_data.severity_level() in {SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL} and combined_confidence >= 0.55


def derive_incident_candidate(
    input_data: DecisionPolicyInput,
    governance: GovernanceFlags,
    profile: DecisionPolicyProfile,
    *,
    combined_confidence: float,
) -> bool:
    if not governance.allow_incident_candidate:
        return False
    if input_data.severity_level() != SeverityLevel.CRITICAL:
        return False
    if input_data.occurrence_count < profile.incident_candidate_min_occurrences:
        return False
    if not input_data.release_critical and not input_data.protected_path:
        return False
    return combined_confidence >= 0.70


def derive_recommended_owner(
    input_data: DecisionPolicyInput,
    decision: DecisionPolicyType,
    *,
    incident_candidate: bool,
) -> str:
    if incident_candidate:
        return "sre_oncall"
    if decision in {DecisionPolicyType.BLOCK_RELEASE, DecisionPolicyType.ESCALATE}:
        if input_data.severity_level() in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}:
            return "backend_owner"
        return "qa_lead"
    if decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
        return "qa_automation"
    if decision == DecisionPolicyType.MANUAL_INVESTIGATION:
        return "feature_owner"
    return "qa_automation"


def build_secondary_signals(
    input_data: DecisionPolicyInput,
    decision_score: float,
    combined_confidence: float,
    strategy: Optional[DecisionStrategy],
    decision: DecisionPolicyType,
) -> Dict[str, float | bool | str]:
    success_count, failure_count = rerun_history_counts(input_data)
    success_rate = rerun_success_rate(input_data)
    release_action = "OBSERVE"
    if decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
        release_action = "SUPPRESS_AND_MONITOR"
    elif decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY}:
        release_action = "RERUN_RECOMMENDED"
    elif decision == DecisionPolicyType.BLOCK_RELEASE:
        release_action = "BLOCK_RELEASE"
    elif decision == DecisionPolicyType.ESCALATE:
        release_action = "ESCALATE"
    elif decision == DecisionPolicyType.MANUAL_INVESTIGATION:
        release_action = "MANUAL_REVIEW"
    return {
        "severity": input_data.severity_level().value,
        "decision_score": round(decision_score, 4),
        "combined_confidence": round(combined_confidence, 4),
        "memory_resolution_type": input_data.resolution_type().value,
        "occurrence_count": input_data.occurrence_count,
        "seen_count": seen_count(input_data),
        "flaky": input_data.flaky,
        "strategy": strategy.value if strategy else "",
        "release_critical": input_data.release_critical,
        "protected_path": input_data.protected_path,
        "rerun_success_count": success_count,
        "rerun_failure_count": failure_count,
        "rerun_success_rate": round(success_rate, 4) if success_rate is not None else "",
        "release_action": release_action,
    }


def derive_boolean_flags(decision: DecisionPolicyType, *, bug_candidate: bool, incident_candidate: bool) -> Dict[str, bool]:
    return {
        "should_block_release": decision == DecisionPolicyType.BLOCK_RELEASE,
        "should_trigger_rerun": decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY},
        "should_escalate": decision in {DecisionPolicyType.ESCALATE, DecisionPolicyType.BLOCK_RELEASE},
        "should_request_manual_review": decision == DecisionPolicyType.MANUAL_INVESTIGATION,
        "should_open_bug_candidate": bug_candidate,
        "should_open_incident_candidate": incident_candidate,
    }


def secondary_decisions_from_candidates(bug_candidate: bool, incident_candidate: bool) -> List[DecisionPolicyType]:
    secondary: List[DecisionPolicyType] = []
    if bug_candidate:
        secondary.append(DecisionPolicyType.BUG_CANDIDATE)
    if incident_candidate:
        secondary.append(DecisionPolicyType.INCIDENT_CANDIDATE)
    return secondary
