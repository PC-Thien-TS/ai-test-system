from __future__ import annotations

from typing import Optional

from orchestrator.decision.domain.models import (
    DecisionPolicyInput,
    DecisionPolicyProfile,
    DecisionPolicyResult,
    DecisionPolicyType,
    DecisionStrategy,
    parse_env_governance,
)
from orchestrator.decision.domain.profiles import choose_profile
from orchestrator.decision.domain.rules import (
    derive_bug_candidate,
    derive_incident_candidate,
    derive_primary_decision_from_score,
    derive_strategy,
    evaluate_hard_rule,
    severity_level,
)
from orchestrator.decision.domain.scoring import compute_decision_score


class DecisionPolicyEngine:
    def __init__(
        self,
        *,
        profile_name: Optional[str] = None,
        adapter_id: Optional[str] = None,
        adapter_profile_overrides: Optional[dict[str, str]] = None,
    ):
        self._profile: DecisionPolicyProfile = choose_profile(
            profile_name,
            adapter_id=adapter_id,
            adapter_overrides=adapter_profile_overrides,
        )

    @property
    def profile(self) -> DecisionPolicyProfile:
        return self._profile

    def choose_profile(
        self,
        *,
        profile_name: Optional[str] = None,
        adapter_id: Optional[str] = None,
        adapter_profile_overrides: Optional[dict[str, str]] = None,
    ) -> DecisionPolicyProfile:
        self._profile = choose_profile(
            profile_name,
            adapter_id=adapter_id,
            adapter_overrides=adapter_profile_overrides,
        )
        return self._profile

    def compute_decision_score(self, value: DecisionPolicyInput) -> tuple[float, dict[str, float]]:
        return compute_decision_score(value, self._profile)

    def derive_primary_decision(self, value: DecisionPolicyInput, score: float) -> DecisionPolicyType:
        hard = evaluate_hard_rule(value, self._profile)
        if hard:
            return hard[0]
        return derive_primary_decision_from_score(value, self._profile, score)

    def derive_strategy(self, value: DecisionPolicyInput, decision: DecisionPolicyType) -> Optional[DecisionStrategy]:
        return derive_strategy(decision=decision, value=value)

    def derive_bug_candidate(self, value: DecisionPolicyInput) -> bool:
        return derive_bug_candidate(value, self._profile)

    def derive_incident_candidate(self, value: DecisionPolicyInput) -> bool:
        return derive_incident_candidate(value, self._profile)

    def evaluate(self, value: DecisionPolicyInput) -> DecisionPolicyResult:
        # governance from env can tighten/relax per runtime without changing caller payload
        governance = parse_env_governance(value.governance_flags)
        value.governance_flags = governance

        score, score_components = self.compute_decision_score(value)
        hard = evaluate_hard_rule(value, self._profile)

        if hard:
            primary_decision, strategy, hard_reason = hard
            rationale = hard_reason
        else:
            primary_decision = derive_primary_decision_from_score(value, self._profile, score)
            strategy = derive_strategy(decision=primary_decision, value=value)
            rationale = self._default_rationale(value=value, score=score, decision=primary_decision)

        should_block = primary_decision == DecisionPolicyType.BLOCK_RELEASE
        should_rerun = primary_decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY}
        should_escalate = primary_decision in {
            DecisionPolicyType.ESCALATE,
            DecisionPolicyType.BLOCK_RELEASE,
            DecisionPolicyType.INCIDENT_CANDIDATE,
        }
        should_manual = primary_decision == DecisionPolicyType.MANUAL_INVESTIGATION

        should_bug = self.derive_bug_candidate(value)
        should_incident = self.derive_incident_candidate(value)
        if should_incident and primary_decision not in {
            DecisionPolicyType.BLOCK_RELEASE,
            DecisionPolicyType.ESCALATE,
        }:
            primary_decision = DecisionPolicyType.INCIDENT_CANDIDATE
            strategy = DecisionStrategy.BLOCK_AND_ESCALATE
            should_escalate = True
            should_block = governance.allow_auto_block_release
            rationale = f"{rationale} Repeated critical production-like pattern qualifies as incident candidate."
        elif should_bug and primary_decision == DecisionPolicyType.NO_ACTION:
            primary_decision = DecisionPolicyType.BUG_CANDIDATE
            rationale = f"{rationale} Recurring meaningful issue qualifies as bug candidate."

        secondary_signals = {
            "profile": self._profile.profile_name,
            "memory_resolution_type": value.memory_resolution_value,
            "severity_level": severity_level(value.severity),
            "occurrence_count": value.occurrence_count,
            "score_components": score_components,
            "best_action_effectiveness": value.best_action_effectiveness,
            "release_critical": value.release_critical,
            "protected_path": value.protected_path,
        }

        return DecisionPolicyResult(
            primary_decision=primary_decision,
            strategy=strategy,
            rationale=rationale,
            confidence=max(0.0, min(1.0, value.confidence)),
            decision_score=round(score, 4),
            governance_flags=governance,
            secondary_signals=secondary_signals,
            should_block_release=should_block,
            should_trigger_rerun=should_rerun,
            should_escalate=should_escalate,
            should_open_bug_candidate=should_bug,
            should_open_incident_candidate=should_incident,
            should_request_manual_review=should_manual or (
                governance.require_manual_review_on_critical and severity_level(value.severity) == "critical"
            ),
            recommended_owner=self._recommend_owner(value, primary_decision),
            metadata={
                "ci_mode": value.ci_mode,
                "run_id": value.run_id,
                "adapter_id": value.adapter_id,
                "project_id": value.project_id,
                "profile_name": self._profile.profile_name,
            },
        )

    def build_ci_decision_hint(self, result: DecisionPolicyResult) -> dict:
        return {
            "primary_decision": result.primary_decision.value,
            "should_block_release": result.should_block_release,
            "should_escalate": result.should_escalate,
            "should_request_manual_review": result.should_request_manual_review,
            "decision_score": result.decision_score,
            "rationale": result.rationale,
            "profile": result.secondary_signals.get("profile"),
        }

    def build_self_healing_instruction(self, result: DecisionPolicyResult) -> dict:
        can_execute = result.primary_decision in {
            DecisionPolicyType.RERUN,
            DecisionPolicyType.RERUN_WITH_STRATEGY,
            DecisionPolicyType.SUPPRESS_KNOWN_FLAKY,
        }
        return {
            "execute_automatically": can_execute,
            "decision": result.primary_decision.value,
            "strategy": result.strategy.value if result.strategy else None,
            "should_stop_blind_retry": not result.should_trigger_rerun,
            "should_escalate": result.should_escalate,
            "owner_hint": result.recommended_owner,
            "rationale": result.rationale,
        }

    def _default_rationale(
        self,
        *,
        value: DecisionPolicyInput,
        score: float,
        decision: DecisionPolicyType,
    ) -> str:
        return (
            f"Decision {decision.value} from deterministic policy score={score:.3f} "
            f"(severity={severity_level(value.severity)}, recurrence={value.occurrence_count}, "
            f"memory={value.memory_resolution_value}, release_critical={value.release_critical})."
        )

    @staticmethod
    def _recommend_owner(value: DecisionPolicyInput, decision: DecisionPolicyType) -> Optional[str]:
        plugin = (value.plugin or "").lower()
        if decision in {
            DecisionPolicyType.BLOCK_RELEASE,
            DecisionPolicyType.ESCALATE,
            DecisionPolicyType.INCIDENT_CANDIDATE,
        }:
            if "infra" in plugin:
                return "sre"
            if "data" in plugin:
                return "data-platform"
            return "backend"
        if decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY}:
            return "qa-automation"
        if decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
            return "qa-lead"
        return None
