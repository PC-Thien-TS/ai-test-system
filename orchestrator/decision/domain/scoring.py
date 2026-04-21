from __future__ import annotations

from typing import Dict, Tuple

from .models import DecisionPolicyInput, DecisionPolicyProfile, MemoryResolutionType, clamp01, historical_action_effectiveness


def _memory_certainty(input_data: DecisionPolicyInput) -> float:
    resolution = input_data.resolution_type()
    base = {
        MemoryResolutionType.EXACT_MATCH: 0.90,
        MemoryResolutionType.SIMILAR_MATCH: 0.65,
        MemoryResolutionType.AMBIGUOUS_MATCH: 0.30,
        MemoryResolutionType.NEW_MEMORY: 0.20,
    }[resolution]
    return clamp01((0.60 * base) + (0.40 * clamp01(input_data.memory_confidence)))


def _recurrence_signal(input_data: DecisionPolicyInput, profile: DecisionPolicyProfile) -> float:
    if input_data.recurrence_score is not None:
        return clamp01(input_data.recurrence_score)
    return clamp01(input_data.occurrence_count / float(max(1, profile.critical_recurrence_block_count)))


def compute_decision_score(
    input_data: DecisionPolicyInput,
    profile: DecisionPolicyProfile,
) -> Tuple[float, Dict[str, float]]:
    severity_signal = clamp01(profile.severity_weights.get(input_data.severity_level().value, 0.45))
    recurrence_signal = _recurrence_signal(input_data, profile)
    memory_signal = _memory_certainty(input_data)

    release_signal = 0.0
    if input_data.release_critical:
        release_signal += profile.release_critical_boost
    if input_data.protected_path:
        release_signal += 0.10
    release_signal = clamp01(release_signal)

    action_effectiveness_signal = historical_action_effectiveness(input_data)

    weighted = (
        profile.component_weights["severity"] * severity_signal
        + profile.component_weights["recurrence"] * recurrence_signal
        + profile.component_weights["memory_certainty"] * memory_signal
        + profile.component_weights["release_criticality"] * release_signal
        + profile.component_weights["action_effectiveness"] * action_effectiveness_signal
    )

    penalties = 0.0
    resolution = input_data.resolution_type()
    if resolution == MemoryResolutionType.AMBIGUOUS_MATCH:
        penalties += profile.ambiguity_penalty
    if resolution == MemoryResolutionType.NEW_MEMORY:
        penalties += profile.new_memory_uncertainty_penalty

    if input_data.flaky and input_data.severity_level().value in {"low", "medium"}:
        weighted -= profile.flaky_suppression_bonus

    score = clamp01(weighted - penalties)

    return score, {
        "severity_signal": round(severity_signal, 4),
        "recurrence_signal": round(recurrence_signal, 4),
        "memory_signal": round(memory_signal, 4),
        "release_signal": round(release_signal, 4),
        "action_effectiveness_signal": round(action_effectiveness_signal, 4),
        "penalties": round(penalties, 4),
        "weighted_sum": round(weighted, 4),
        "score": round(score, 4),
    }
