from __future__ import annotations

import os
import time
import uuid
from dataclasses import asdict
from typing import Callable, Optional, Protocol

from orchestrator.decision.domain.models import (
    DecisionPolicyResult,
    DecisionPolicyType,
    DecisionStrategy,
    GovernanceFlags,
)

from ..domain.guardrails import (
    evaluate_rerun_effectiveness_guardrail,
    evaluate_retry_limits_guardrail,
    evaluate_suppression_guardrail,
)
from ..domain.models import (
    ActionContext,
    ActionExecutionBundle,
    ActionExecutionResult,
    ActionOutcomeRecord,
    ActionPlan,
    SelfHealingConfig,
)
from ..domain.strategies import resolve_strategy_config


class MemoryOutcomeRecorder(Protocol):
    def record_action_outcome(self, context: ActionContext, outcome: ActionOutcomeRecord) -> None:
        ...


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class SelfHealingEngine:
    def __init__(
        self,
        *,
        config: Optional[SelfHealingConfig] = None,
        memory_recorder: Optional[MemoryOutcomeRecorder] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.time,
    ) -> None:
        self.config = config or SelfHealingConfig(
            max_attempts=_env_int("SELF_HEAL_MAX_ATTEMPTS", 3),
            max_total_attempts=_env_int("SELF_HEAL_MAX_TOTAL_ATTEMPTS", 20),
            max_attempts_per_failure=_env_int("SELF_HEAL_MAX_ATTEMPTS_PER_FAILURE", 5),
            backoff_base=_env_float("SELF_HEAL_BACKOFF_BASE", 2.0),
            timeout_multiplier=_env_float("SELF_HEAL_TIMEOUT_MULTIPLIER", 1.5),
            cooldown_seconds=_env_float("SELF_HEAL_COOLDOWN_SECONDS", 2.0),
            enable_suppression=_env_bool("SELF_HEAL_ENABLE_SUPPRESSION", True),
            enable_escalation=_env_bool("SELF_HEAL_ENABLE_ESCALATION", True),
        )
        self.memory_recorder = memory_recorder
        self.sleep_fn = sleep_fn
        self.clock_fn = clock_fn

    def build_action_plan(self, decision_result: DecisionPolicyResult, context: ActionContext) -> ActionPlan:
        action_id = f"{context.run_id}:{context.failure_id}:{uuid.uuid4().hex[:8]}"
        strategy = decision_result.strategy

        if decision_result.primary_decision == DecisionPolicyType.RERUN and strategy is None:
            strategy = DecisionStrategy.RETRY_3X
        if decision_result.primary_decision == DecisionPolicyType.RERUN_WITH_STRATEGY and strategy is None:
            strategy = DecisionStrategy.RETRY_3X

        strategy_cfg = resolve_strategy_config(
            strategy,
            fallback_max_attempts=self.config.max_attempts,
            timeout_multiplier=self.config.timeout_multiplier,
        )

        max_attempts = strategy_cfg.max_attempts
        if decision_result.primary_decision not in {
            DecisionPolicyType.RERUN,
            DecisionPolicyType.RERUN_WITH_STRATEGY,
        }:
            max_attempts = 0

        plan = ActionPlan(
            action_id=action_id,
            decision_type=decision_result.primary_decision,
            strategy=strategy,
            max_attempts=max_attempts,
            cooldown_seconds=self.config.cooldown_seconds,
            allow_partial_success=False,
            metadata={
                "strategy_config": asdict(strategy_cfg),
                "decision_score": decision_result.decision_score,
                "decision_confidence": decision_result.confidence,
            },
        )
        return self.apply_guardrails(plan, decision_result, context)

    def apply_guardrails(
        self,
        plan: ActionPlan,
        decision_result: DecisionPolicyResult,
        context: ActionContext,
    ) -> ActionPlan:
        suppression_guard = evaluate_suppression_guardrail(decision_result, context, self.config)
        effectiveness_guard = evaluate_rerun_effectiveness_guardrail(decision_result, self.config)
        retry_limit_guard = evaluate_retry_limits_guardrail(context, self.config)

        if plan.decision_type == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY and not suppression_guard.allowed:
            return ActionPlan(
                action_id=plan.action_id,
                decision_type=DecisionPolicyType.MANUAL_INVESTIGATION,
                strategy=DecisionStrategy.INVESTIGATE_BACKEND,
                max_attempts=0,
                cooldown_seconds=plan.cooldown_seconds,
                metadata={**plan.metadata, "guardrail": suppression_guard.reason},
            )

        if plan.decision_type in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY}:
            if not effectiveness_guard.allowed:
                return ActionPlan(
                    action_id=plan.action_id,
                    decision_type=DecisionPolicyType.MANUAL_INVESTIGATION,
                    strategy=DecisionStrategy.INVESTIGATE_BACKEND,
                    max_attempts=0,
                    cooldown_seconds=plan.cooldown_seconds,
                    metadata={**plan.metadata, "guardrail": effectiveness_guard.reason},
                )
            if not retry_limit_guard.allowed:
                return ActionPlan(
                    action_id=plan.action_id,
                    decision_type=DecisionPolicyType.ESCALATE,
                    strategy=DecisionStrategy.BLOCK_AND_ESCALATE,
                    max_attempts=0,
                    cooldown_seconds=plan.cooldown_seconds,
                    metadata={**plan.metadata, "guardrail": retry_limit_guard.reason},
                )

        return plan

    def should_stop_retry(self, attempts_used: int, plan: ActionPlan, context: ActionContext) -> bool:
        if attempts_used >= plan.max_attempts:
            return True
        prior_attempts = int(context.memory_context.get("prior_attempts", 0))
        if prior_attempts + attempts_used >= self.config.max_attempts_per_failure:
            return True
        total_attempts = int(context.memory_context.get("global_attempts", 0))
        if total_attempts + attempts_used >= self.config.max_total_attempts:
            return True
        return False

    def execute(self, decision_result: DecisionPolicyResult, context: ActionContext) -> ActionExecutionBundle:
        plan = self.build_action_plan(decision_result, context)
        start = self.clock_fn()

        try:
            if plan.decision_type == DecisionPolicyType.RERUN:
                result = self.execute_rerun(plan, context)
            elif plan.decision_type == DecisionPolicyType.RERUN_WITH_STRATEGY:
                result = self.execute_rerun_with_strategy(plan, context)
            elif plan.decision_type == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY:
                result = self.execute_suppress(plan, context)
            elif plan.decision_type == DecisionPolicyType.ESCALATE:
                result = self.execute_escalate(plan, context)
            elif plan.decision_type == DecisionPolicyType.MANUAL_INVESTIGATION:
                result = self.execute_manual_review(plan, context)
            else:
                result = self.execute_no_action(plan, context)
        except Exception as exc:  # fail-safe
            duration_ms = int((self.clock_fn() - start) * 1000)
            result = ActionExecutionResult(
                action_id=plan.action_id,
                executed=False,
                success=False,
                attempts_used=0,
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
                logs=["Self-healing engine recovered from action execution exception."],
            )

        outcome = self.record_outcome(plan, result, context)
        return ActionExecutionBundle(
            decision_result=decision_result,
            action_plan=plan,
            execution_result=result,
            outcome_record=outcome,
        )

    def execute_rerun(self, plan: ActionPlan, context: ActionContext) -> ActionExecutionResult:
        return self._run_attempt_loop(plan, context, strategy_backoff=False, timeout_multiplier=None)

    def execute_rerun_with_strategy(self, plan: ActionPlan, context: ActionContext) -> ActionExecutionResult:
        strategy_cfg = plan.metadata.get("strategy_config", {})
        return self._run_attempt_loop(
            plan,
            context,
            strategy_backoff=bool(strategy_cfg.get("use_backoff", False)),
            timeout_multiplier=strategy_cfg.get("timeout_multiplier"),
            isolate=bool(strategy_cfg.get("isolate", False)),
            rerun_subset=bool(strategy_cfg.get("rerun_subset", False)),
        )

    def _run_attempt_loop(
        self,
        plan: ActionPlan,
        context: ActionContext,
        *,
        strategy_backoff: bool,
        timeout_multiplier: Optional[float],
        isolate: bool = False,
        rerun_subset: bool = False,
    ) -> ActionExecutionResult:
        start = self.clock_fn()
        logs = []
        attempts_used = 0
        success = False
        error = None

        executor = context.executor
        if executor is None:
            return ActionExecutionResult(
                action_id=plan.action_id,
                executed=False,
                success=False,
                attempts_used=0,
                duration_ms=int((self.clock_fn() - start) * 1000),
                error="No executor provided in ActionContext.",
                logs=["Rerun skipped because executor callback is missing."],
            )

        while not self.should_stop_retry(attempts_used, plan, context):
            attempts_used += 1
            try:
                ok = bool(executor(attempts_used, plan, context))
                logs.append(f"Attempt {attempts_used}/{plan.max_attempts}: {'success' if ok else 'failure'}")
                if ok:
                    success = True
                    break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                logs.append(f"Attempt {attempts_used}/{plan.max_attempts}: exception {error}")
                success = False

            if self.should_stop_retry(attempts_used, plan, context):
                break

            delay = plan.cooldown_seconds
            if strategy_backoff:
                delay = plan.cooldown_seconds * (self.config.backoff_base ** (attempts_used - 1))
            logs.append(f"Cooldown before next attempt: {delay:.3f}s")
            self.sleep_fn(delay)

        if timeout_multiplier is not None:
            logs.append(f"Timeout multiplier applied: {timeout_multiplier}")
        if isolate:
            logs.append("Isolated test execution strategy applied.")
        if rerun_subset:
            logs.append("Rerun subset execution strategy applied.")

        return ActionExecutionResult(
            action_id=plan.action_id,
            executed=True,
            success=success,
            attempts_used=attempts_used,
            duration_ms=int((self.clock_fn() - start) * 1000),
            error=error,
            logs=logs,
        )

    def execute_suppress(self, plan: ActionPlan, context: ActionContext) -> ActionExecutionResult:
        return ActionExecutionResult(
            action_id=plan.action_id,
            executed=True,
            success=True,
            attempts_used=0,
            duration_ms=0,
            error=None,
            logs=["Failure suppressed as known flaky/noise based on policy and guardrails."],
            metadata={"suppressed": True},
        )

    def execute_escalate(self, plan: ActionPlan, context: ActionContext) -> ActionExecutionResult:
        if not self.config.enable_escalation:
            return ActionExecutionResult(
                action_id=plan.action_id,
                executed=False,
                success=False,
                attempts_used=0,
                duration_ms=0,
                error="Escalation disabled by configuration.",
                logs=["Escalation request ignored due to config."],
            )
        owner = context.decision_context.get("recommended_owner", "backend_owner")
        return ActionExecutionResult(
            action_id=plan.action_id,
            executed=True,
            success=False,
            attempts_used=0,
            duration_ms=0,
            error=None,
            logs=[f"Escalation generated for owner={owner}."],
            metadata={"escalated": True, "owner": owner},
        )

    def execute_manual_review(self, plan: ActionPlan, context: ActionContext) -> ActionExecutionResult:
        return ActionExecutionResult(
            action_id=plan.action_id,
            executed=True,
            success=False,
            attempts_used=0,
            duration_ms=0,
            error=None,
            logs=["Manual investigation requested. Automation intentionally stopped."],
            metadata={"manual_review": True},
        )

    def execute_no_action(self, plan: ActionPlan, context: ActionContext) -> ActionExecutionResult:
        return ActionExecutionResult(
            action_id=plan.action_id,
            executed=True,
            success=True,
            attempts_used=0,
            duration_ms=0,
            error=None,
            logs=["No action required by policy decision."],
        )

    def record_outcome(
        self,
        plan: ActionPlan,
        result: ActionExecutionResult,
        context: ActionContext,
    ) -> ActionOutcomeRecord:
        notes = "; ".join(result.logs[-3:]) if result.logs else ""
        outcome = ActionOutcomeRecord(
            action_type=plan.decision_type.value,
            strategy=plan.strategy.value if plan.strategy else "",
            success=result.success,
            attempts=result.attempts_used,
            notes=notes,
            metadata={
                "action_id": plan.action_id,
                "error": result.error or "",
                "adapter_id": context.adapter_id,
                "project_id": context.project_id,
                "run_id": context.run_id,
                "failure_id": context.failure_id,
            },
        )
        if self.memory_recorder is not None:
            try:
                self.memory_recorder.record_action_outcome(context, outcome)
            except Exception:
                # No crash by design; outcome still returned.
                pass
        return outcome
