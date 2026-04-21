from __future__ import annotations

from orchestrator.memory.domain.models import ActionEffectiveness, MemoryEngineConfig


def clamp_confidence(value: float, config: MemoryEngineConfig) -> float:
    return max(config.confidence_min, min(config.confidence_max, value))


def confidence_on_exact_recurrence(current: float, triage_confidence: float, config: MemoryEngineConfig) -> float:
    target = max(current, triage_confidence)
    return clamp_confidence(target + config.confidence_boost_exact, config)


def confidence_on_similar_merge(current: float, triage_confidence: float, config: MemoryEngineConfig) -> float:
    target = max(current, triage_confidence)
    return clamp_confidence(target + config.confidence_boost_similar, config)


def confidence_on_contradiction(current: float, config: MemoryEngineConfig) -> float:
    return clamp_confidence(current - config.confidence_decay_contradiction, config)


def update_action_effectiveness(effectiveness: ActionEffectiveness, success: bool) -> ActionEffectiveness:
    if success:
        effectiveness.success_count += 1
    else:
        effectiveness.failure_count += 1
    total = effectiveness.success_count + effectiveness.failure_count
    if total <= 0:
        effectiveness.effectiveness_score = 0.0
    else:
        base = effectiveness.success_count / total
        support = min(total, 10) / 10.0
        effectiveness.effectiveness_score = round(base * support, 4)
    return effectiveness
