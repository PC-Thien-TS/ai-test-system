from __future__ import annotations

from dataclasses import dataclass
from typing import List

from orchestrator.decision.domain.models import (
    DecisionPolicyResult,
    DecisionPolicyType,
    DecisionStrategy,
    GovernanceFlags,
)
from orchestrator.self_healing.application.engine import SelfHealingEngine
from orchestrator.self_healing.domain.models import ActionContext, SelfHealingConfig


def _decision_result(
    *,
    decision: DecisionPolicyType,
    strategy: DecisionStrategy | None = None,
    severity: str = "medium",
    release_critical: bool = False,
    protected_path: bool = False,
    action_effectiveness_signal: float = 0.8,
) -> DecisionPolicyResult:
    return DecisionPolicyResult(
        primary_decision=decision,
        strategy=strategy,
        rationale=["test"],
        confidence=0.8,
        decision_score=0.65,
        governance_flags=GovernanceFlags(),
        secondary_signals={
            "severity": severity,
            "release_critical": release_critical,
            "protected_path": protected_path,
            "score_components": {"action_effectiveness_signal": action_effectiveness_signal},
        },
        secondary_decisions=[],
        should_block_release=decision == DecisionPolicyType.BLOCK_RELEASE,
        should_trigger_rerun=decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY},
        should_escalate=decision in {DecisionPolicyType.ESCALATE, DecisionPolicyType.BLOCK_RELEASE},
        should_open_bug_candidate=False,
        should_open_incident_candidate=False,
        should_request_manual_review=decision == DecisionPolicyType.MANUAL_INVESTIGATION,
        recommended_owner="backend_owner",
        metadata={},
    )


def _context(executor=None, *, prior_attempts=0, global_attempts=0):
    return ActionContext(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        failure_id="failure-001",
        memory_context={"prior_attempts": prior_attempts, "global_attempts": global_attempts},
        decision_context={},
        executor=executor,
    )


@dataclass
class Recorder:
    outcomes: List[object]

    def record_action_outcome(self, context, outcome) -> None:
        self.outcomes.append((context.failure_id, outcome))


def test_rerun_executes_with_correct_attempts():
    seq = [False, False, True]

    def executor(attempt, plan, ctx):
        return seq[attempt - 1]

    engine = SelfHealingEngine(config=SelfHealingConfig(max_attempts=3, cooldown_seconds=0))
    bundle = engine.execute(_decision_result(decision=DecisionPolicyType.RERUN), _context(executor=executor))
    assert bundle.execution_result.executed is True
    assert bundle.execution_result.success is True
    assert bundle.execution_result.attempts_used == 3


def test_backoff_strategy_increases_delay():
    seq = [False, False, True]
    delays = []

    def executor(attempt, plan, ctx):
        return seq[attempt - 1]

    def sleep_fn(seconds):
        delays.append(seconds)

    engine = SelfHealingEngine(
        config=SelfHealingConfig(max_attempts=3, cooldown_seconds=1, backoff_base=2),
        sleep_fn=sleep_fn,
    )
    bundle = engine.execute(
        _decision_result(
            decision=DecisionPolicyType.RERUN_WITH_STRATEGY,
            strategy=DecisionStrategy.RETRY_WITH_BACKOFF,
        ),
        _context(executor=executor),
    )
    assert bundle.execution_result.success is True
    assert len(delays) == 2
    assert delays[1] > delays[0]


def test_suppression_stops_execution():
    called = {"value": 0}

    def executor(attempt, plan, ctx):
        called["value"] += 1
        return True

    engine = SelfHealingEngine(config=SelfHealingConfig(enable_suppression=True))
    bundle = engine.execute(
        _decision_result(decision=DecisionPolicyType.SUPPRESS_KNOWN_FLAKY, severity="low"),
        _context(executor=executor),
    )
    assert bundle.execution_result.success is True
    assert called["value"] == 0
    assert bundle.execution_result.metadata.get("suppressed") is True


def test_escalation_triggers_correctly():
    engine = SelfHealingEngine(config=SelfHealingConfig(enable_escalation=True))
    bundle = engine.execute(_decision_result(decision=DecisionPolicyType.ESCALATE), _context())
    assert bundle.execution_result.executed is True
    assert bundle.execution_result.success is False
    assert bundle.execution_result.metadata.get("escalated") is True


def test_guardrails_prevent_infinite_retry():
    def executor(attempt, plan, ctx):
        return False

    engine = SelfHealingEngine(config=SelfHealingConfig(max_attempts=3, cooldown_seconds=0))
    bundle = engine.execute(_decision_result(decision=DecisionPolicyType.RERUN), _context(executor=executor))
    assert bundle.execution_result.attempts_used == 3
    assert bundle.execution_result.success is False


def test_ineffective_rerun_is_skipped():
    called = {"value": 0}

    def executor(attempt, plan, ctx):
        called["value"] += 1
        return True

    engine = SelfHealingEngine(config=SelfHealingConfig(min_action_effectiveness_for_rerun=0.55))
    bundle = engine.execute(
        _decision_result(
            decision=DecisionPolicyType.RERUN,
            action_effectiveness_signal=0.10,
        ),
        _context(executor=executor),
    )
    assert bundle.action_plan.decision_type == DecisionPolicyType.MANUAL_INVESTIGATION
    assert called["value"] == 0


def test_action_outcome_recorded_to_memory():
    recorder = Recorder(outcomes=[])
    engine = SelfHealingEngine(config=SelfHealingConfig(cooldown_seconds=0), memory_recorder=recorder)
    bundle = engine.execute(_decision_result(decision=DecisionPolicyType.NO_ACTION), _context())
    assert bundle.outcome_record.action_type == DecisionPolicyType.NO_ACTION.value
    assert len(recorder.outcomes) == 1


def test_decision_mapping_to_action_plan_correct():
    engine = SelfHealingEngine(config=SelfHealingConfig(max_attempts=3))
    decision = _decision_result(
        decision=DecisionPolicyType.RERUN_WITH_STRATEGY,
        strategy=DecisionStrategy.RETRY_WITH_BACKOFF,
    )
    plan = engine.build_action_plan(decision, _context())
    assert plan.decision_type == DecisionPolicyType.RERUN_WITH_STRATEGY
    assert plan.strategy == DecisionStrategy.RETRY_WITH_BACKOFF
    assert plan.max_attempts == 3


def test_failure_execution_does_not_crash_engine():
    def executor(attempt, plan, ctx):
        raise RuntimeError("boom")

    engine = SelfHealingEngine(config=SelfHealingConfig(max_attempts=2, cooldown_seconds=0))
    bundle = engine.execute(_decision_result(decision=DecisionPolicyType.RERUN), _context(executor=executor))
    assert bundle.execution_result.success is False
    assert bundle.execution_result.error is not None


def test_cooldown_respected():
    delays = []

    def executor(attempt, plan, ctx):
        return False

    def sleep_fn(seconds):
        delays.append(seconds)

    engine = SelfHealingEngine(
        config=SelfHealingConfig(max_attempts=3, cooldown_seconds=2),
        sleep_fn=sleep_fn,
    )
    bundle = engine.execute(_decision_result(decision=DecisionPolicyType.RERUN), _context(executor=executor))
    assert bundle.execution_result.attempts_used == 3
    assert delays == [2, 2]

