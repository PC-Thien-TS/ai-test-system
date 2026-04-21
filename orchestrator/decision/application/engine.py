from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from ..domain.models import (
    DecisionPolicyInput,
    DecisionPolicyProfile,
    DecisionPolicyResult,
    DecisionPolicyType,
    GovernanceFlags,
    combine_confidence,
    merge_governance,
    parse_env_governance,
)
from ..domain.profiles import choose_profile
from ..domain.rules import (
    build_secondary_signals,
    derive_boolean_flags,
    derive_bug_candidate,
    derive_incident_candidate,
    derive_primary_decision_from_score,
    derive_recommended_owner,
    derive_strategy,
    evaluate_hard_rule,
    evaluate_memory_policy,
    secondary_decisions_from_candidates,
)
from ..domain.scoring import compute_decision_score


class DecisionPolicyEngine:
    """Deterministic policy engine mapping failure + memory signals to operational decisions."""

    def __init__(
        self,
        *,
        default_profile_name: str = "balanced",
        adapter_profile_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.default_profile_name = default_profile_name
        self.adapter_profile_overrides = adapter_profile_overrides or {}

    def choose_profile(self, input_data: DecisionPolicyInput, profile_name: Optional[str] = None) -> DecisionPolicyProfile:
        adapter_overrides = self.adapter_profile_overrides.get(input_data.adapter_id, {})
        return choose_profile(profile_name or self.default_profile_name, adapter_overrides=adapter_overrides)

    def compute_decision_score(
        self,
        input_data: DecisionPolicyInput,
        profile: DecisionPolicyProfile,
    ) -> tuple[float, Dict[str, float]]:
        return compute_decision_score(input_data, profile)

    def derive_primary_decision(
        self,
        input_data: DecisionPolicyInput,
        governance: GovernanceFlags,
        profile: DecisionPolicyProfile,
        *,
        decision_score: float,
        combined_confidence: float,
    ) -> tuple[DecisionPolicyType, Optional[str]]:
        hard_outcome = evaluate_hard_rule(input_data, governance, profile, combined_confidence=combined_confidence)
        if hard_outcome is not None:
            return hard_outcome.decision, hard_outcome.rationale

        memory_outcome = evaluate_memory_policy(input_data, governance, profile)
        if memory_outcome is not None:
            return memory_outcome.decision, memory_outcome.rationale

        decision = derive_primary_decision_from_score(
            input_data,
            governance,
            profile,
            decision_score=decision_score,
        )
        return decision, None

    def evaluate(
        self,
        input_data: DecisionPolicyInput,
        *,
        profile_name: Optional[str] = None,
    ) -> DecisionPolicyResult:
        profile = self.choose_profile(input_data, profile_name=profile_name)
        env_governance = parse_env_governance(profile.governance_defaults)
        governance = merge_governance(env_governance, input_data.governance_flags)

        combined_confidence = combine_confidence(
            signal_confidence=input_data.confidence,
            memory_confidence=input_data.memory_confidence,
            resolution=input_data.resolution_type(),
        )

        decision_score, score_components = self.compute_decision_score(input_data, profile)
        primary_decision, hard_rule_reason = self.derive_primary_decision(
            input_data,
            governance,
            profile,
            decision_score=decision_score,
            combined_confidence=combined_confidence,
        )
        strategy = derive_strategy(input_data, primary_decision)

        bug_candidate = derive_bug_candidate(
            input_data,
            governance,
            profile,
            combined_confidence=combined_confidence,
        )
        incident_candidate = derive_incident_candidate(
            input_data,
            governance,
            profile,
            combined_confidence=combined_confidence,
        )
        secondary_decisions = secondary_decisions_from_candidates(bug_candidate, incident_candidate)
        decision_flags = derive_boolean_flags(
            primary_decision,
            bug_candidate=bug_candidate,
            incident_candidate=incident_candidate,
        )

        rationale = []
        if hard_rule_reason:
            rationale.append(hard_rule_reason)
        else:
            rationale.append("Deterministic score and governance policy evaluation applied.")

        if primary_decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY}:
            rationale.append("Rerun selected only because historical action effectiveness meets minimum threshold.")
        if primary_decision == DecisionPolicyType.MANUAL_INVESTIGATION:
            rationale.append("Manual review requested due to ambiguity, governance guardrails, or unsafe automation.")
        if primary_decision == DecisionPolicyType.BLOCK_RELEASE:
            rationale.append("Release block selected from severe, recurring, or release-critical failure signals.")
        if primary_decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
            rationale.append("Suppression limited to non-critical known flaky/noise behavior.")

        if bug_candidate:
            rationale.append("Recurring non-transient issue qualifies as bug candidate.")
        if incident_candidate:
            rationale.append("Critical repeated production-like pattern qualifies as incident candidate.")

        recommended_owner = derive_recommended_owner(
            input_data,
            primary_decision,
            incident_candidate=incident_candidate,
        )

        secondary_signals = build_secondary_signals(
            input_data,
            decision_score,
            combined_confidence,
            strategy,
            primary_decision,
        )
        secondary_signals["profile"] = profile.profile_name
        secondary_signals["score_components"] = score_components

        return DecisionPolicyResult(
            primary_decision=primary_decision,
            strategy=strategy,
            rationale=rationale,
            confidence=combined_confidence,
            decision_score=decision_score,
            governance_flags=governance,
            secondary_signals=secondary_signals,
            secondary_decisions=secondary_decisions,
            should_block_release=decision_flags["should_block_release"],
            should_trigger_rerun=decision_flags["should_trigger_rerun"],
            should_escalate=decision_flags["should_escalate"],
            should_open_bug_candidate=decision_flags["should_open_bug_candidate"],
            should_open_incident_candidate=decision_flags["should_open_incident_candidate"],
            should_request_manual_review=decision_flags["should_request_manual_review"],
            recommended_owner=recommended_owner,
            metadata={
                "profile": asdict(profile),
                "input_adapter_id": input_data.adapter_id,
                "input_project_id": input_data.project_id,
            },
        )

    def build_ci_decision_hint(self, result: DecisionPolicyResult) -> Dict[str, Any]:
        if result.should_block_release:
            return {
                "gate_signal": "hard_block",
                "strictness": "harden",
                "release_penalty": 20,
                "summary": "Policy engine recommends release block for current failure pattern.",
            }
        if result.should_escalate:
            return {
                "gate_signal": "escalate",
                "strictness": "warning",
                "release_penalty": 10,
                "summary": "Policy engine recommends escalation before promoting changes.",
            }
        if result.should_trigger_rerun:
            return {
                "gate_signal": "rerun",
                "strictness": "normal",
                "release_penalty": 4,
                "summary": "Policy engine recommends targeted rerun strategy before gate finalization.",
            }
        if result.primary_decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
            return {
                "gate_signal": "suppress_flaky",
                "strictness": "normal",
                "release_penalty": 0,
                "summary": "Known flaky/non-critical behavior can be suppressed with explicit annotation.",
            }
        return {
            "gate_signal": "observe",
            "strictness": "normal",
            "release_penalty": 0,
            "summary": "No immediate operational action required by policy engine.",
        }

    def build_self_healing_instruction(self, result: DecisionPolicyResult) -> Dict[str, Any]:
        if result.should_trigger_rerun:
            return {
                "should_execute": True,
                "instruction_type": "rerun",
                "strategy": result.strategy.value if result.strategy else "",
                "owner_hint": result.recommended_owner,
                "notes": result.rationale,
            }
        if result.primary_decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
            return {
                "should_execute": False,
                "instruction_type": "suppress",
                "strategy": result.strategy.value if result.strategy else "",
                "owner_hint": result.recommended_owner,
                "notes": result.rationale,
            }
        if result.primary_decision in {DecisionPolicyType.ESCALATE, DecisionPolicyType.BLOCK_RELEASE}:
            return {
                "should_execute": False,
                "instruction_type": "escalate",
                "strategy": result.strategy.value if result.strategy else "",
                "owner_hint": result.recommended_owner,
                "notes": result.rationale,
            }
        if result.primary_decision == DecisionPolicyType.MANUAL_INVESTIGATION:
            return {
                "should_execute": False,
                "instruction_type": "manual_review",
                "strategy": result.strategy.value if result.strategy else "",
                "owner_hint": result.recommended_owner,
                "notes": result.rationale,
            }
        return {
            "should_execute": False,
            "instruction_type": "none",
            "strategy": "",
            "owner_hint": result.recommended_owner,
            "notes": result.rationale,
        }
