from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.decision.application.engine import DecisionPolicyEngine
from orchestrator.decision.domain.models import (
    DecisionPolicyInput,
    DecisionPolicyType,
    GovernanceFlags,
)
from orchestrator.decision.integration.ci_gate_bridge import build_ci_policy_hint
from orchestrator.decision.integration.self_healing_bridge import build_self_healing_policy_instruction
from orchestrator.memory.domain.models import MemoryResolutionType


def _input(
    *,
    severity: str = "medium",
    confidence: float = 0.75,
    memory_resolution_type: MemoryResolutionType = MemoryResolutionType.EXACT_MATCH,
    occurrence_count: int = 2,
    flaky: bool = False,
    best_action_effectiveness: float = 0.7,
    best_action: dict | None = None,
    release_critical: bool = False,
    protected_path: bool = False,
    execution_path: str = "standard",
    governance_flags: GovernanceFlags | None = None,
) -> DecisionPolicyInput:
    return DecisionPolicyInput(
        adapter_id="rankmate",
        project_id="order_core",
        run_id="run-001",
        plugin="backend",
        execution_path=execution_path,
        severity=severity,
        confidence=confidence,
        memory_resolution_type=memory_resolution_type,
        memory_confidence=confidence,
        occurrence_count=occurrence_count,
        flaky=flaky,
        best_action=best_action or {"action_type": "rerun_with_backoff"},
        best_action_effectiveness=best_action_effectiveness,
        release_critical=release_critical,
        protected_path=protected_path,
        ci_mode="pr",
        governance_flags=governance_flags or GovernanceFlags(),
        metadata={},
    )


def test_repeated_critical_exact_match_blocks_release() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    result = engine.evaluate(
        _input(
            severity="critical",
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
            occurrence_count=4,
            release_critical=True,
            confidence=0.9,
        )
    )
    assert result.primary_decision == DecisionPolicyType.BLOCK_RELEASE
    assert result.should_block_release is True


def test_ambiguous_high_severity_low_certainty_manual_not_hard_block() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    result = engine.evaluate(
        _input(
            severity="high",
            confidence=0.5,
            memory_resolution_type=MemoryResolutionType.AMBIGUOUS_MATCH,
            occurrence_count=3,
        )
    )
    assert result.primary_decision in {DecisionPolicyType.MANUAL_INVESTIGATION, DecisionPolicyType.ESCALATE}
    assert result.should_block_release is False


def test_effective_rerun_action_prefers_rerun_with_strategy() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    result = engine.evaluate(
        _input(
            severity="medium",
            confidence=0.8,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
            occurrence_count=4,
            best_action_effectiveness=0.8,
            best_action={"action_type": "increase_timeout"},
        )
    )
    assert result.primary_decision == DecisionPolicyType.RERUN_WITH_STRATEGY
    assert result.strategy is not None
    assert result.should_trigger_rerun is True


def test_ineffective_rerun_history_avoids_blind_rerun() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    result = engine.evaluate(
        _input(
            severity="medium",
            confidence=0.8,
            occurrence_count=3,
            best_action_effectiveness=0.2,
            best_action={"action_type": "rerun"},
        )
    )
    assert result.should_trigger_rerun is False


def test_known_flaky_noncritical_suppression_when_allowed() -> None:
    engine = DecisionPolicyEngine(profile_name="flaky_tolerant")
    flags = GovernanceFlags(allow_auto_suppress=True)
    result = engine.evaluate(
        _input(
            severity="low",
            confidence=0.6,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
            occurrence_count=3,
            flaky=True,
            best_action_effectiveness=0.4,
            governance_flags=flags,
        )
    )
    assert result.primary_decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY


def test_release_critical_severe_route_stronger_gate_outcome() -> None:
    engine = DecisionPolicyEngine(profile_name="release_hardening")
    result = engine.evaluate(
        _input(
            severity="high",
            confidence=0.85,
            memory_resolution_type=MemoryResolutionType.SIMILAR_MATCH,
            occurrence_count=2,
            release_critical=True,
        )
    )
    assert result.primary_decision == DecisionPolicyType.BLOCK_RELEASE
    assert result.should_block_release is True


def test_bug_candidate_for_recurring_logic_issue() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    result = engine.evaluate(
        _input(
            severity="medium",
            confidence=0.78,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
            occurrence_count=4,
            best_action_effectiveness=0.3,
        )
    )
    assert result.should_open_bug_candidate is True


def test_incident_candidate_for_repeated_critical_pattern() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    result = engine.evaluate(
        _input(
            severity="critical",
            confidence=0.9,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
            occurrence_count=5,
            release_critical=True,
            execution_path="smoke",
        )
    )
    assert result.should_open_incident_candidate is True
    assert result.should_escalate is True


def test_profile_difference_conservative_vs_aggressive() -> None:
    value = _input(
        severity="high",
        confidence=0.7,
        memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
        occurrence_count=3,
        release_critical=False,
        best_action_effectiveness=0.6,
        best_action={"action_type": "rerun_with_backoff"},
    )
    conservative = DecisionPolicyEngine(profile_name="conservative").evaluate(value)
    aggressive = DecisionPolicyEngine(profile_name="aggressive").evaluate(value)
    assert conservative.primary_decision != aggressive.primary_decision


def test_governance_flags_disable_automation() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    flags = GovernanceFlags(
        allow_auto_rerun=False,
        allow_auto_suppress=False,
        allow_auto_block_release=False,
        require_manual_review_on_critical=True,
    )
    result = engine.evaluate(
        _input(
            severity="critical",
            confidence=0.9,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH,
            occurrence_count=6,
            release_critical=True,
            governance_flags=flags,
        )
    )
    assert result.primary_decision in {DecisionPolicyType.MANUAL_INVESTIGATION, DecisionPolicyType.ESCALATE}
    assert result.should_block_release is False


def test_ci_decision_hint_generation() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    value = _input(severity="critical", occurrence_count=4, release_critical=True)
    hint = build_ci_policy_hint(engine=engine, value=value)
    assert "primary_decision" in hint
    assert "should_block_release" in hint
    assert "policy_result" in hint


def test_self_healing_instruction_generation() -> None:
    engine = DecisionPolicyEngine(profile_name="balanced")
    value = _input(
        severity="medium",
        confidence=0.8,
        occurrence_count=3,
        best_action_effectiveness=0.8,
        best_action={"action_type": "rerun_with_backoff"},
    )
    instruction = build_self_healing_policy_instruction(engine=engine, value=value)
    assert "execute_automatically" in instruction
    assert "decision" in instruction
    assert "policy_result" in instruction
