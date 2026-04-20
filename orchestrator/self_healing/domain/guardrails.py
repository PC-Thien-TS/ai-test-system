from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from orchestrator.decision.domain.models import DecisionPolicyResult, DecisionPolicyType, SeverityLevel

from .models import ActionContext, SelfHealingConfig


@dataclass(frozen=True)
class GuardrailAssessment:
    allowed: bool
    reason: str = ""


def evaluate_suppression_guardrail(
    decision_result: DecisionPolicyResult,
    context: ActionContext,
    config: SelfHealingConfig,
) -> GuardrailAssessment:
    if decision_result.primary_decision != DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
        return GuardrailAssessment(True)
    if not config.enable_suppression:
        return GuardrailAssessment(False, "Suppression disabled by configuration.")

    is_critical_path = bool(
        context.decision_context.get("release_critical")
        or decision_result.secondary_signals.get("release_critical")
        or context.decision_context.get("protected_path")
        or decision_result.secondary_signals.get("protected_path")
    )
    if is_critical_path:
        return GuardrailAssessment(False, "Suppression blocked on critical/protected path.")

    severity = str(decision_result.secondary_signals.get("severity", SeverityLevel.MEDIUM.value)).lower()
    if severity == SeverityLevel.CRITICAL.value:
        return GuardrailAssessment(False, "Suppression blocked for critical severity.")

    return GuardrailAssessment(True)


def evaluate_rerun_effectiveness_guardrail(
    decision_result: DecisionPolicyResult,
    config: SelfHealingConfig,
) -> GuardrailAssessment:
    if decision_result.primary_decision not in {
        DecisionPolicyType.RERUN,
        DecisionPolicyType.RERUN_WITH_STRATEGY,
    }:
        return GuardrailAssessment(True)

    score_components = decision_result.secondary_signals.get("score_components", {})
    effectiveness = score_components.get("action_effectiveness_signal")
    if effectiveness is None:
        effectiveness = decision_result.secondary_signals.get("action_effectiveness_signal")
    if effectiveness is None:
        return GuardrailAssessment(True)
    if float(effectiveness) < config.min_action_effectiveness_for_rerun:
        return GuardrailAssessment(
            False,
            "Rerun blocked due to low historical action effectiveness.",
        )
    return GuardrailAssessment(True)


def evaluate_retry_limits_guardrail(
    context: ActionContext,
    config: SelfHealingConfig,
) -> GuardrailAssessment:
    prior_attempts = int(context.memory_context.get("prior_attempts", 0))
    if prior_attempts >= config.max_attempts_per_failure:
        return GuardrailAssessment(False, "Max attempts per failure reached.")

    total_attempts = int(context.memory_context.get("global_attempts", 0))
    if total_attempts >= config.max_total_attempts:
        return GuardrailAssessment(False, "Max total attempts reached.")
    return GuardrailAssessment(True)

