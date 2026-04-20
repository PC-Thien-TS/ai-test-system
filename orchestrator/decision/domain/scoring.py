from __future__ import annotations

from orchestrator.decision.domain.models import DecisionPolicyInput, DecisionPolicyProfile


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _severity_score(severity: str, profile: DecisionPolicyProfile) -> float:
    return float(profile.severity_weights.get((severity or "low").strip().lower(), 0.1))


def _memory_certainty_score(memory_resolution: str, profile: DecisionPolicyProfile) -> float:
    return float(profile.memory_resolution_weights.get(memory_resolution, 0.0))


def _recurrence_score(value: DecisionPolicyInput) -> float:
    if value.recurrence_score > 0:
        return _clamp(value.recurrence_score)
    if value.occurrence_count <= 1:
        return 0.0
    return _clamp((value.occurrence_count - 1) / 5.0)


def compute_decision_score(
    value: DecisionPolicyInput,
    profile: DecisionPolicyProfile,
) -> tuple[float, dict[str, float]]:
    severity = _severity_score(value.severity, profile)
    memory = _memory_certainty_score(value.memory_resolution_value, profile)
    recurrence = _recurrence_score(value)
    release_criticality = 1.0 if value.release_critical else 0.0
    protected_path = 1.0 if value.protected_path else 0.0
    action_effective = _clamp(value.best_action_effectiveness)
    ambiguity_penalty = profile.ambiguity_penalty if value.memory_resolution_value == "AMBIGUOUS_MATCH" else 0.0
    flaky_bonus = profile.flaky_bonus if value.flaky else 0.0
    new_memory_penalty = profile.new_memory_uncertainty_penalty if value.memory_resolution_value == "NEW_MEMORY" else 0.0

    score = (
        severity * 0.35
        + memory * 0.2
        + recurrence * profile.recurrence_weight
        + release_criticality * profile.release_critical_weight
        + protected_path * profile.protected_path_weight
        + action_effective * profile.action_effectiveness_weight
        + flaky_bonus
        + (profile.release_critical_boost if value.release_critical and severity >= 0.55 else 0.0)
        - ambiguity_penalty
        - new_memory_penalty
    )
    score = _clamp(score, 0.0, 1.5)
    components = {
        "severity_score": severity,
        "memory_certainty_score": memory,
        "recurrence_score": recurrence,
        "release_criticality_score": release_criticality,
        "protected_path_score": protected_path,
        "action_effectiveness_score": action_effective,
        "flaky_bonus": flaky_bonus,
        "ambiguity_penalty": ambiguity_penalty,
        "new_memory_penalty": new_memory_penalty,
    }
    return score, components
