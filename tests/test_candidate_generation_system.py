from __future__ import annotations

import json
from pathlib import Path

from orchestrator.candidates.application.bug_engine import BugAutoGenerator
from orchestrator.candidates.application.incident_engine import IncidentCandidateEngine
from orchestrator.candidates.domain.formatting import build_bug_title
from orchestrator.candidates.domain.models import (
    BugCandidateInput,
    CandidateConfig,
    CandidateGovernanceFlags,
    IncidentCandidateInput,
)
from orchestrator.candidates.infrastructure.artifact_writer import CandidateArtifactWriter
from orchestrator.candidates.infrastructure.local_index_store import LocalCandidateIndexStore
from orchestrator.decision.domain.models import (
    DecisionPolicyResult,
    DecisionPolicyType,
    GovernanceFlags,
)
from orchestrator.self_healing.domain.models import ActionExecutionResult


def _decision(primary: DecisionPolicyType = DecisionPolicyType.ESCALATE) -> DecisionPolicyResult:
    return DecisionPolicyResult(
        primary_decision=primary,
        strategy=None,
        rationale=["policy rationale"],
        confidence=0.8,
        decision_score=0.72,
        governance_flags=GovernanceFlags(),
        secondary_signals={
            "severity": "high",
            "release_critical": True,
            "protected_path": True,
            "score_components": {"action_effectiveness_signal": 0.8},
        },
        secondary_decisions=[],
        should_block_release=primary == DecisionPolicyType.BLOCK_RELEASE,
        should_trigger_rerun=False,
        should_escalate=primary in {DecisionPolicyType.ESCALATE, DecisionPolicyType.BLOCK_RELEASE},
        should_open_bug_candidate=True,
        should_open_incident_candidate=primary in {DecisionPolicyType.ESCALATE, DecisionPolicyType.BLOCK_RELEASE},
        should_request_manual_review=False,
        recommended_owner="backend_owner",
        metadata={},
    )


def _self_healing(success: bool) -> ActionExecutionResult:
    return ActionExecutionResult(
        action_id="action-001",
        executed=True,
        success=success,
        attempts_used=2,
        duration_ms=200,
        error=None if success else "failed",
        logs=["log"],
    )


def _bug_input(**overrides) -> BugCandidateInput:
    base = BugCandidateInput(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        failure_id="failure-001",
        memory_id="mem-001",
        signature_hash="sig-001",
        memory_resolution_type="EXACT_MATCH",
        root_cause="Order controller validation mismatch",
        severity="high",
        confidence=0.82,
        occurrence_count=3,
        flaky=False,
        decision_result=_decision(),
        self_healing_result=_self_healing(False),
        execution_path="/api/v1/orders",
        evidence_refs=["artifact:log-001"],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _incident_input(**overrides) -> IncidentCandidateInput:
    base = IncidentCandidateInput(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        failure_id="failure-002",
        memory_id="mem-002",
        signature_hash="sig-002",
        memory_resolution_type="EXACT_MATCH",
        root_cause="Payment settlement endpoint release regression",
        severity="critical",
        confidence=0.91,
        occurrence_count=4,
        flaky=False,
        decision_result=_decision(DecisionPolicyType.BLOCK_RELEASE),
        self_healing_result=_self_healing(False),
        execution_path="/api/v1/payments/verify",
        evidence_refs=["artifact:trace-001"],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _build_bug_engine(tmp_path: Path, *, governance: CandidateGovernanceFlags | None = None, config: CandidateConfig | None = None) -> BugAutoGenerator:
    cfg = config or CandidateConfig(root_dir=str(tmp_path))
    idx = LocalCandidateIndexStore(Path(cfg.root_dir))
    writer = CandidateArtifactWriter(Path(cfg.root_dir), idx)
    return BugAutoGenerator(config=cfg, governance=governance, index_store=idx, writer=writer)


def _build_incident_engine(
    tmp_path: Path,
    *,
    governance: CandidateGovernanceFlags | None = None,
    config: CandidateConfig | None = None,
) -> IncidentCandidateEngine:
    cfg = config or CandidateConfig(root_dir=str(tmp_path))
    idx = LocalCandidateIndexStore(Path(cfg.root_dir))
    writer = CandidateArtifactWriter(Path(cfg.root_dir), idx)
    return IncidentCandidateEngine(config=cfg, governance=governance, index_store=idx, writer=writer)


def test_recurring_medium_high_non_flaky_generates_bug_candidate(tmp_path: Path):
    engine = _build_bug_engine(tmp_path)
    result = engine.generate_bug_candidate(_bug_input())
    assert result.generated is True
    assert result.candidate_id.startswith("BUG-")


def test_repeated_critical_protected_path_generates_incident_candidate(tmp_path: Path):
    engine = _build_incident_engine(tmp_path)
    result = engine.generate_incident_candidate(_incident_input())
    assert result.generated is True
    assert result.candidate_id.startswith("INC-")


def test_flaky_suppressible_issue_does_not_generate_bug_candidate(tmp_path: Path):
    engine = _build_bug_engine(tmp_path)
    result = engine.generate_bug_candidate(_bug_input(flaky=True, severity="medium"))
    assert result.generated is False
    assert result.metadata.get("suppression_path")


def test_ambiguous_low_confidence_does_not_auto_generate_candidate(tmp_path: Path):
    engine = _build_bug_engine(tmp_path)
    result = engine.generate_bug_candidate(
        _bug_input(memory_resolution_type="AMBIGUOUS_MATCH", confidence=0.40)
    )
    assert result.generated is False


def test_duplicate_candidate_detection_prevents_duplicate_creation(tmp_path: Path):
    cfg = CandidateConfig(root_dir=str(tmp_path), candidate_allow_auto_update_existing=False)
    gov = CandidateGovernanceFlags(allow_auto_update_existing_candidate=False)
    engine = _build_bug_engine(tmp_path, governance=gov, config=cfg)
    first = engine.generate_bug_candidate(_bug_input())
    second = engine.generate_bug_candidate(_bug_input())
    assert first.generated is True
    assert second.generated is False
    assert second.dedup_result is not None
    assert second.dedup_result.action == "skip"


def test_existing_candidate_can_be_updated_when_allowed(tmp_path: Path):
    cfg = CandidateConfig(root_dir=str(tmp_path), candidate_allow_auto_update_existing=True)
    gov = CandidateGovernanceFlags(allow_auto_update_existing_candidate=True)
    engine = _build_bug_engine(tmp_path, governance=gov, config=cfg)
    first = engine.generate_bug_candidate(_bug_input())
    second = engine.generate_bug_candidate(_bug_input(root_cause="Updated root cause text"))
    assert first.generated is True
    assert second.generated is True
    assert second.dedup_result is not None
    assert second.dedup_result.action == "update"
    assert first.candidate_id == second.candidate_id


def test_self_healing_success_reduces_or_suppresses_candidate_urgency(tmp_path: Path):
    cfg = CandidateConfig(root_dir=str(tmp_path), bug_min_occurrences=2)
    engine = _build_bug_engine(tmp_path, config=cfg)
    result = engine.generate_bug_candidate(_bug_input(occurrence_count=2, self_healing_result=_self_healing(True)))
    assert result.generated is False


def test_self_healing_failure_strengthens_candidate_generation(tmp_path: Path):
    cfg = CandidateConfig(root_dir=str(tmp_path), bug_min_occurrences=2)
    engine = _build_bug_engine(tmp_path, config=cfg)
    result = engine.generate_bug_candidate(_bug_input(occurrence_count=2, self_healing_result=_self_healing(False)))
    assert result.generated is True


def test_title_generation_is_deterministic_and_non_empty():
    t1 = build_bug_title(_bug_input())
    t2 = build_bug_title(_bug_input())
    assert t1 == t2
    assert t1.strip() != ""


def test_artifact_writing_produces_expected_json_and_index_structure(tmp_path: Path):
    engine = _build_bug_engine(tmp_path)
    result = engine.generate_bug_candidate(_bug_input())
    assert result.generated is True
    candidate_path = Path(result.metadata["artifact_path"])
    assert candidate_path.exists()
    index_path = tmp_path / "indexes" / "bug_index.json"
    assert index_path.exists()
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    assert isinstance(index_data, list)
    assert any(e.get("candidate_id") == result.candidate_id for e in index_data)


def test_governance_flags_can_disable_generation(tmp_path: Path):
    gov = CandidateGovernanceFlags(allow_bug_generation=False)
    engine = _build_bug_engine(tmp_path, governance=gov)
    result = engine.generate_bug_candidate(_bug_input())
    assert result.generated is False


def test_similar_match_behavior_respects_config_thresholds(tmp_path: Path):
    cfg = CandidateConfig(root_dir=str(tmp_path), bug_allow_similar_match=False)
    engine = _build_bug_engine(tmp_path, config=cfg)
    result = engine.generate_bug_candidate(_bug_input(memory_resolution_type="SIMILAR_MATCH"))
    assert result.generated is False

