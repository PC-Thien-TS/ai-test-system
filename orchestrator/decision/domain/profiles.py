from __future__ import annotations

import os
from dataclasses import replace
from typing import Any, Dict, Optional

from .models import DecisionPolicyProfile, GovernanceFlags


def _apply_env_override_float(profile: DecisionPolicyProfile, env: Dict[str, str]) -> DecisionPolicyProfile:
    mapping = {
        "DECISION_BLOCK_THRESHOLD": "block_threshold",
        "DECISION_ESCALATE_THRESHOLD": "escalate_threshold",
        "DECISION_RERUN_THRESHOLD": "rerun_threshold",
        "DECISION_AMBIGUITY_PENALTY": "ambiguity_penalty",
        "DECISION_RELEASE_CRITICAL_BOOST": "release_critical_boost",
        "DECISION_MIN_ACTION_EFFECTIVENESS_FOR_RERUN": "min_action_effectiveness_for_rerun",
    }
    for env_key, attr in mapping.items():
        raw = env.get(env_key)
        if raw is None:
            continue
        try:
            setattr(profile, attr, float(raw))
        except ValueError:
            continue
    raw = env.get("DECISION_CRITICAL_RECURRENCE_BLOCK_COUNT")
    if raw is not None:
        try:
            profile.critical_recurrence_block_count = max(1, int(raw))
        except ValueError:
            pass
    return profile


def _profile_conservative() -> DecisionPolicyProfile:
    return DecisionPolicyProfile(
        profile_name="conservative",
        block_threshold=0.90,
        escalate_threshold=0.68,
        rerun_threshold=0.50,
        ambiguity_penalty=0.25,
        release_critical_boost=0.18,
        min_action_effectiveness_for_rerun=0.60,
        governance_defaults=GovernanceFlags(
            allow_auto_rerun=True,
            allow_auto_suppress=False,
            allow_auto_block_release=False,
            require_manual_review_on_critical=True,
            allow_bug_candidate=True,
            allow_incident_candidate=True,
        ),
    )


def _profile_balanced() -> DecisionPolicyProfile:
    return DecisionPolicyProfile(
        profile_name="balanced",
        block_threshold=0.80,
        escalate_threshold=0.60,
        rerun_threshold=0.45,
        ambiguity_penalty=0.20,
        release_critical_boost=0.20,
        min_action_effectiveness_for_rerun=0.55,
        governance_defaults=GovernanceFlags(
            allow_auto_rerun=True,
            allow_auto_suppress=False,
            allow_auto_block_release=True,
            require_manual_review_on_critical=True,
            allow_bug_candidate=True,
            allow_incident_candidate=True,
        ),
    )


def _profile_aggressive() -> DecisionPolicyProfile:
    profile = DecisionPolicyProfile(
        profile_name="aggressive",
        block_threshold=0.75,
        escalate_threshold=0.55,
        rerun_threshold=0.35,
        ambiguity_penalty=0.16,
        release_critical_boost=0.24,
        min_action_effectiveness_for_rerun=0.50,
        governance_defaults=GovernanceFlags(
            allow_auto_rerun=True,
            allow_auto_suppress=True,
            allow_auto_block_release=True,
            require_manual_review_on_critical=False,
            allow_bug_candidate=True,
            allow_incident_candidate=True,
        ),
    )
    profile.component_weights["action_effectiveness"] = 0.15
    return profile


def _profile_release_hardening() -> DecisionPolicyProfile:
    profile = DecisionPolicyProfile(
        profile_name="release_hardening",
        block_threshold=0.74,
        escalate_threshold=0.54,
        rerun_threshold=0.42,
        ambiguity_penalty=0.30,
        critical_recurrence_block_count=2,
        release_critical_boost=0.30,
        min_action_effectiveness_for_rerun=0.58,
        governance_defaults=GovernanceFlags(
            allow_auto_rerun=True,
            allow_auto_suppress=False,
            allow_auto_block_release=True,
            require_manual_review_on_critical=True,
            allow_bug_candidate=True,
            allow_incident_candidate=True,
        ),
    )
    profile.component_weights["release_criticality"] = 0.20
    return profile


def _profile_flaky_tolerant() -> DecisionPolicyProfile:
    profile = DecisionPolicyProfile(
        profile_name="flaky_tolerant",
        block_threshold=0.88,
        escalate_threshold=0.64,
        rerun_threshold=0.48,
        ambiguity_penalty=0.18,
        release_critical_boost=0.14,
        min_action_effectiveness_for_rerun=0.52,
        flaky_suppression_bonus=0.14,
        governance_defaults=GovernanceFlags(
            allow_auto_rerun=True,
            allow_auto_suppress=True,
            allow_auto_block_release=False,
            require_manual_review_on_critical=True,
            allow_bug_candidate=True,
            allow_incident_candidate=False,
        ),
    )
    return profile


def builtin_profiles() -> Dict[str, DecisionPolicyProfile]:
    return {
        "conservative": _profile_conservative(),
        "balanced": _profile_balanced(),
        "aggressive": _profile_aggressive(),
        "release_hardening": _profile_release_hardening(),
        "flaky_tolerant": _profile_flaky_tolerant(),
    }


def choose_profile(
    profile_name: Optional[str] = None,
    *,
    adapter_overrides: Optional[Dict[str, Any]] = None,
    env: Optional[Dict[str, str]] = None,
) -> DecisionPolicyProfile:
    local_env = env or dict(os.environ)
    requested = profile_name or local_env.get("DECISION_POLICY_PROFILE", "balanced")
    profiles = builtin_profiles()
    selected = replace(profiles.get(requested, profiles["balanced"]))

    selected = _apply_env_override_float(selected, local_env)

    if adapter_overrides:
        for key, value in adapter_overrides.items():
            if hasattr(selected, key):
                setattr(selected, key, value)
    return selected

