from __future__ import annotations

import copy
import os
from typing import Optional

from orchestrator.decision.domain.models import DecisionPolicyProfile


def _profile(
    name: str,
    *,
    block: float,
    escalate: float,
    rerun: float,
    ambiguity_penalty: float,
    critical_recur_block: int,
    release_boost: float,
    min_action_eff: float,
    ambiguous_manual_conf: float,
    flaky_suppress_recur: int,
    bug_recur: int,
    incident_recur: int,
    severity_weights: dict[str, float],
    memory_weights: dict[str, float],
    recurrence_weight: float = 0.25,
    action_eff_weight: float = 0.2,
    release_weight: float = 0.2,
    protected_weight: float = 0.1,
    flaky_bonus: float = 0.12,
    new_mem_penalty: float = 0.1,
) -> DecisionPolicyProfile:
    return DecisionPolicyProfile(
        profile_name=name,
        block_threshold=block,
        escalate_threshold=escalate,
        rerun_threshold=rerun,
        ambiguity_penalty=ambiguity_penalty,
        critical_recurrence_block_count=critical_recur_block,
        release_critical_boost=release_boost,
        min_action_effectiveness_for_rerun=min_action_eff,
        ambiguous_manual_review_confidence=ambiguous_manual_conf,
        flaky_suppress_recurrence=flaky_suppress_recur,
        bug_candidate_recurrence=bug_recur,
        incident_candidate_recurrence=incident_recur,
        severity_weights=severity_weights,
        memory_resolution_weights=memory_weights,
        recurrence_weight=recurrence_weight,
        action_effectiveness_weight=action_eff_weight,
        release_critical_weight=release_weight,
        protected_path_weight=protected_weight,
        flaky_bonus=flaky_bonus,
        new_memory_uncertainty_penalty=new_mem_penalty,
    )


def get_builtin_profiles() -> dict[str, DecisionPolicyProfile]:
    base_weights = {"low": 0.1, "medium": 0.3, "high": 0.55, "critical": 0.85}
    memory_weights = {
        "EXACT_MATCH": 0.25,
        "SIMILAR_MATCH": 0.18,
        "AMBIGUOUS_MATCH": 0.04,
        "NEW_MEMORY": 0.0,
    }
    return {
        "balanced": _profile(
            "balanced",
            block=0.8,
            escalate=0.6,
            rerun=0.45,
            ambiguity_penalty=0.2,
            critical_recur_block=3,
            release_boost=0.2,
            min_action_eff=0.55,
            ambiguous_manual_conf=0.75,
            flaky_suppress_recur=3,
            bug_recur=3,
            incident_recur=4,
            severity_weights=base_weights,
            memory_weights=memory_weights,
        ),
        "conservative": _profile(
            "conservative",
            block=0.9,
            escalate=0.58,
            rerun=0.5,
            ambiguity_penalty=0.24,
            critical_recur_block=4,
            release_boost=0.17,
            min_action_eff=0.65,
            ambiguous_manual_conf=0.82,
            flaky_suppress_recur=4,
            bug_recur=4,
            incident_recur=5,
            severity_weights=base_weights,
            memory_weights=memory_weights,
            action_eff_weight=0.18,
        ),
        "aggressive": _profile(
            "aggressive",
            block=0.75,
            escalate=0.55,
            rerun=0.35,
            ambiguity_penalty=0.16,
            critical_recur_block=2,
            release_boost=0.24,
            min_action_eff=0.45,
            ambiguous_manual_conf=0.68,
            flaky_suppress_recur=3,
            bug_recur=2,
            incident_recur=3,
            severity_weights=base_weights,
            memory_weights=memory_weights,
            action_eff_weight=0.24,
        ),
        "release_hardening": _profile(
            "release_hardening",
            block=0.72,
            escalate=0.55,
            rerun=0.4,
            ambiguity_penalty=0.22,
            critical_recur_block=2,
            release_boost=0.28,
            min_action_eff=0.55,
            ambiguous_manual_conf=0.78,
            flaky_suppress_recur=4,
            bug_recur=3,
            incident_recur=3,
            severity_weights={"low": 0.08, "medium": 0.28, "high": 0.62, "critical": 0.92},
            memory_weights=memory_weights,
            release_weight=0.25,
            protected_weight=0.16,
        ),
        "flaky_tolerant": _profile(
            "flaky_tolerant",
            block=0.86,
            escalate=0.62,
            rerun=0.4,
            ambiguity_penalty=0.18,
            critical_recur_block=3,
            release_boost=0.16,
            min_action_eff=0.5,
            ambiguous_manual_conf=0.72,
            flaky_suppress_recur=2,
            bug_recur=4,
            incident_recur=5,
            severity_weights=base_weights,
            memory_weights=memory_weights,
            flaky_bonus=0.2,
        ),
    }


def choose_profile(
    profile_name: Optional[str] = None,
    *,
    adapter_id: Optional[str] = None,
    adapter_overrides: Optional[dict[str, str]] = None,
) -> DecisionPolicyProfile:
    all_profiles = get_builtin_profiles()
    requested = (profile_name or os.getenv("DECISION_POLICY_PROFILE", "balanced")).strip().lower()
    if adapter_id and adapter_overrides and adapter_id in adapter_overrides:
        requested = adapter_overrides[adapter_id].strip().lower()
    selected = all_profiles.get(requested, all_profiles["balanced"])
    resolved = copy.deepcopy(selected)

    # optional env threshold overrides
    def _float(name: str, value: float) -> float:
        raw = os.getenv(name, "").strip()
        if not raw:
            return value
        try:
            return float(raw)
        except ValueError:
            return value

    def _int(name: str, value: int) -> int:
        raw = os.getenv(name, "").strip()
        if not raw:
            return value
        try:
            return int(raw)
        except ValueError:
            return value

    resolved.block_threshold = _float("DECISION_BLOCK_THRESHOLD", resolved.block_threshold)
    resolved.escalate_threshold = _float("DECISION_ESCALATE_THRESHOLD", resolved.escalate_threshold)
    resolved.rerun_threshold = _float("DECISION_RERUN_THRESHOLD", resolved.rerun_threshold)
    resolved.ambiguity_penalty = _float("DECISION_AMBIGUITY_PENALTY", resolved.ambiguity_penalty)
    resolved.critical_recurrence_block_count = _int(
        "DECISION_CRITICAL_RECURRENCE_BLOCK_COUNT", resolved.critical_recurrence_block_count
    )
    resolved.release_critical_boost = _float("DECISION_RELEASE_CRITICAL_BOOST", resolved.release_critical_boost)
    resolved.min_action_effectiveness_for_rerun = _float(
        "DECISION_MIN_ACTION_EFFECTIVENESS_FOR_RERUN",
        resolved.min_action_effectiveness_for_rerun,
    )
    return resolved
