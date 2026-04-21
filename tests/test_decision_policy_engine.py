from __future__ import annotations

from orchestrator.decision import (
    DecisionPolicyEngine,
    DecisionPolicyInput,
    DecisionPolicyType,
    GovernanceFlags,
    MemoryResolutionType,
    SeverityLevel,
)


def _input(**overrides):
    base = DecisionPolicyInput(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        severity=SeverityLevel.MEDIUM.value,
        confidence=0.70,
        memory_resolution_type=MemoryResolutionType.SIMILAR_MATCH.value,
        memory_confidence=0.70,
        occurrence_count=1,
        flaky=False,
        best_action=None,
        best_action_effectiveness=0.0,
        release_critical=False,
        protected_path=False,
        governance_flags=None,
        metadata={},
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_repeated_critical_exact_match_blocks_release():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.CRITICAL.value,
            confidence=0.92,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.95,
            occurrence_count=4,
            release_critical=True,
        )
    )
    assert result.primary_decision == DecisionPolicyType.BLOCK_RELEASE
    assert result.should_block_release is True


def test_ambiguous_high_severity_low_certainty_requires_manual_not_block():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.HIGH.value,
            confidence=0.40,
            memory_resolution_type=MemoryResolutionType.AMBIGUOUS_MATCH.value,
            memory_confidence=0.35,
            occurrence_count=2,
        )
    )
    assert result.primary_decision == DecisionPolicyType.MANUAL_INVESTIGATION
    assert result.should_block_release is False
    assert result.should_request_manual_review is True


def test_effective_known_action_selects_rerun_with_strategy():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.MEDIUM.value,
            confidence=0.70,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.80,
            occurrence_count=2,
            best_action="retry_with_backoff",
            best_action_effectiveness=0.80,
        )
    )
    assert result.primary_decision == DecisionPolicyType.RERUN_WITH_STRATEGY
    assert result.should_trigger_rerun is True
    assert result.strategy is not None
    assert result.strategy.value == "retry_with_backoff"


def test_ineffective_rerun_history_avoids_blind_retry():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.MEDIUM.value,
            confidence=0.70,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.80,
            occurrence_count=2,
            best_action="retry_3x",
            best_action_effectiveness=0.10,
        )
    )
    assert result.primary_decision == DecisionPolicyType.MANUAL_INVESTIGATION
    assert result.should_trigger_rerun is False


def test_known_flaky_non_critical_can_be_suppressed():
    engine = DecisionPolicyEngine()
    flags = GovernanceFlags(allow_auto_suppress=True)
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.LOW.value,
            confidence=0.50,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.70,
            occurrence_count=5,
            flaky=True,
            governance_flags=flags,
        ),
        profile_name="flaky_tolerant",
    )
    assert result.primary_decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY
    assert result.should_block_release is False


def test_release_critical_severe_route_triggers_stronger_gate():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.HIGH.value,
            confidence=0.95,
            memory_resolution_type=MemoryResolutionType.SIMILAR_MATCH.value,
            memory_confidence=0.90,
            occurrence_count=1,
            release_critical=True,
        )
    )
    assert result.primary_decision in {DecisionPolicyType.BLOCK_RELEASE, DecisionPolicyType.ESCALATE}
    assert result.should_escalate is True or result.should_block_release is True


def test_bug_candidate_emitted_for_recurring_non_transient_issue():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.MEDIUM.value,
            confidence=0.82,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.90,
            occurrence_count=3,
        )
    )
    assert result.should_open_bug_candidate is True
    assert DecisionPolicyType.BUG_CANDIDATE in result.secondary_decisions


def test_incident_candidate_emitted_for_repeated_critical_prod_like_pattern():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.CRITICAL.value,
            confidence=0.92,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.95,
            occurrence_count=4,
            release_critical=True,
            protected_path=True,
        )
    )
    assert result.should_open_incident_candidate is True
    assert DecisionPolicyType.INCIDENT_CANDIDATE in result.secondary_decisions


def test_profile_differences_conservative_vs_aggressive():
    engine = DecisionPolicyEngine()
    case = _input(
        severity=SeverityLevel.MEDIUM.value,
        confidence=0.65,
        memory_resolution_type=MemoryResolutionType.SIMILAR_MATCH.value,
        memory_confidence=0.50,
        occurrence_count=1,
        best_action="retry_3x",
        best_action_effectiveness=0.60,
    )
    conservative = engine.evaluate(case, profile_name="conservative")
    aggressive = engine.evaluate(case, profile_name="aggressive")
    assert conservative.primary_decision in {DecisionPolicyType.NO_ACTION, DecisionPolicyType.MANUAL_INVESTIGATION}
    assert aggressive.primary_decision in {
        DecisionPolicyType.RERUN,
        DecisionPolicyType.RERUN_WITH_STRATEGY,
        DecisionPolicyType.MANUAL_INVESTIGATION,
    }
    assert aggressive.decision_score >= conservative.decision_score


def test_governance_flags_can_disable_automation():
    engine = DecisionPolicyEngine()
    flags = GovernanceFlags(
        allow_auto_rerun=False,
        allow_auto_suppress=False,
        allow_auto_block_release=False,
        require_manual_review_on_critical=False,
    )
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.MEDIUM.value,
            confidence=0.72,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.82,
            occurrence_count=2,
            best_action="retry_with_backoff",
            best_action_effectiveness=0.82,
            governance_flags=flags,
        ),
        profile_name="aggressive",
    )
    assert result.should_trigger_rerun is False
    assert result.primary_decision in {DecisionPolicyType.MANUAL_INVESTIGATION, DecisionPolicyType.ESCALATE}


def test_ci_decision_hint_generation():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.HIGH.value,
            confidence=0.88,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.92,
            occurrence_count=3,
            release_critical=True,
        )
    )
    hint = engine.build_ci_decision_hint(result)
    assert "gate_signal" in hint
    assert "summary" in hint
    assert hint["gate_signal"] in {"hard_block", "escalate", "rerun", "suppress_flaky", "observe"}


def test_self_healing_instruction_generation():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.MEDIUM.value,
            confidence=0.72,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.88,
            occurrence_count=2,
            best_action="retry_with_backoff",
            best_action_effectiveness=0.75,
        )
    )
    instruction = engine.build_self_healing_instruction(result)
    assert "instruction_type" in instruction
    if result.should_trigger_rerun:
        assert instruction["should_execute"] is True
        assert instruction["instruction_type"] == "rerun"
    else:
        assert instruction["should_execute"] is False


def test_first_occurrence_never_suppresses_even_with_flaky_signal():
    engine = DecisionPolicyEngine()
    flags = GovernanceFlags(allow_auto_suppress=True)
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.LOW.value,
            confidence=0.55,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.70,
            occurrence_count=1,
            flaky=True,
            governance_flags=flags,
            metadata={"seen_count": 1},
        ),
        profile_name="flaky_tolerant",
    )
    assert result.primary_decision != DecisionPolicyType.SUPPRESS_KNOWN_FLAKY
    assert result.primary_decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY, DecisionPolicyType.ESCALATE}


def test_repeated_failure_with_high_rerun_success_rate_suppresses_and_monitors():
    engine = DecisionPolicyEngine()
    flags = GovernanceFlags(allow_auto_suppress=True)
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.LOW.value,
            confidence=0.60,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.80,
            occurrence_count=2,
            flaky=True,
            governance_flags=flags,
            metadata={
                "seen_count": 2,
                "rerun_success_count": 4,
                "rerun_failure_count": 1,
            },
        ),
        profile_name="flaky_tolerant",
    )
    assert result.primary_decision == DecisionPolicyType.SUPPRESS_KNOWN_FLAKY
    assert result.secondary_signals["release_action"] == "SUPPRESS_AND_MONITOR"
    assert result.secondary_signals["rerun_success_rate"] == 0.8


def test_repeated_failure_with_low_rerun_success_rate_escalates():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.HIGH.value,
            confidence=0.75,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.85,
            occurrence_count=3,
            release_critical=True,
            metadata={
                "seen_count": 3,
                "rerun_success_count": 1,
                "rerun_failure_count": 3,
            },
        )
    )
    assert result.primary_decision in {DecisionPolicyType.ESCALATE, DecisionPolicyType.BLOCK_RELEASE}


def test_repeated_flaky_failure_with_poor_rerun_history_does_not_suppress():
    engine = DecisionPolicyEngine()
    flags = GovernanceFlags(allow_auto_suppress=True)
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.LOW.value,
            confidence=0.70,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.80,
            occurrence_count=4,
            flaky=True,
            governance_flags=flags,
            metadata={
                "seen_count": 4,
                "rerun_success_count": 1,
                "rerun_failure_count": 3,
            },
        ),
        profile_name="flaky_tolerant",
    )
    assert result.primary_decision == DecisionPolicyType.ESCALATE
    assert result.primary_decision != DecisionPolicyType.SUPPRESS_KNOWN_FLAKY


def test_repeated_failure_with_mixed_rerun_success_rate_prefers_rerun():
    engine = DecisionPolicyEngine()
    result = engine.evaluate(
        _input(
            severity=SeverityLevel.MEDIUM.value,
            confidence=0.70,
            memory_resolution_type=MemoryResolutionType.EXACT_MATCH.value,
            memory_confidence=0.80,
            occurrence_count=2,
            best_action="retry_with_backoff",
            metadata={
                "seen_count": 2,
                "rerun_success_count": 1,
                "rerun_failure_count": 1,
            },
        )
    )
    assert result.primary_decision in {DecisionPolicyType.RERUN, DecisionPolicyType.RERUN_WITH_STRATEGY}
    assert result.secondary_signals["release_action"] == "RERUN_RECOMMENDED"
