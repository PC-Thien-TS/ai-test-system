from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.memory.application.engine import FailureMemoryEngine
from orchestrator.memory.domain.models import IncomingFailureRecord, MemoryEngineConfig, MemoryResolutionType
from orchestrator.storage.infrastructure.local.memory_repository import LocalMemoryRepository
from orchestrator.storage.infrastructure.local.vector_memory_repository import LocalVectorMemoryRepository
from orchestrator.storage.infrastructure.server.stubs import UnavailableVectorMemoryRepository


def _engine(tmp_path: Path, *, vector_available: bool = True, config: MemoryEngineConfig | None = None) -> FailureMemoryEngine:
    memory_repo = LocalMemoryRepository(tmp_path / "memory.sqlite3")
    vector_repo = (
        LocalVectorMemoryRepository(tmp_path / "vectors.json")
        if vector_available
        else UnavailableVectorMemoryRepository()
    )
    return FailureMemoryEngine(
        memory_repository=memory_repo,
        vector_repository=vector_repo,
        config=config or MemoryEngineConfig(),
    )


def _incoming(
    *,
    endpoint: str = "/api/v1/orders/1/payments",
    message: str = "Payment failed for order 1",
    root_cause: str = "stripe secret mismatch",
    confidence: float = 0.6,
    severity: str = "p1",
    component: str = "payment_api",
    fingerprint: str = "PAY-API-003",
) -> IncomingFailureRecord:
    return IncomingFailureRecord(
        adapter_id="rankmate",
        project_id="order_core",
        plugin="payment",
        error_type="HTTP_400",
        endpoint=endpoint,
        stack_trace='File "payment_helper.py", line 12, in create_payment_intent',
        message=message,
        severity_hint=severity,
        triage_root_cause=root_cause,
        triage_confidence=confidence,
        recommended_actions=["rerun", "manual_investigation"],
        metadata={"source": "pytest"},
        component=component,
        fingerprint=fingerprint,
    )


def test_exact_signature_resolution(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    first = engine.resolve_failure(_incoming())
    second = engine.resolve_failure(_incoming())
    assert first.resolution_type == MemoryResolutionType.NEW_MEMORY
    assert second.resolution_type == MemoryResolutionType.EXACT_MATCH
    assert second.resolved_memory_id == first.resolved_memory_id


def test_semantic_candidate_resolution(tmp_path: Path) -> None:
    config = MemoryEngineConfig(
        similarity_threshold=0.5,
        auto_merge_threshold=0.9,
        ambiguous_threshold=0.3,
    )
    engine = _engine(tmp_path, config=config)
    engine.resolve_failure(_incoming(message="Stripe callback invalid signature payment rejected"))
    result = engine.resolve_failure(
        _incoming(
            endpoint="/api/v1/payments/stripe/webhook",
            message="payment rejected due to invalid stripe signature callback",
            root_cause="stripe signature mismatch",
            component="webhook_handler",
        )
    )
    assert result.resolution_type in {MemoryResolutionType.SIMILAR_MATCH, MemoryResolutionType.AMBIGUOUS_MATCH}
    assert len(result.candidate_matches) >= 1


def test_new_memory_creation_when_no_match_exists(tmp_path: Path) -> None:
    engine = _engine(tmp_path, config=MemoryEngineConfig(ambiguous_threshold=0.95))
    first = engine.resolve_failure(_incoming(message="first unique failure", endpoint="/a"))
    second = engine.resolve_failure(_incoming(message="totally different subsystem crash", endpoint="/b"))
    assert first.resolved_memory_id != second.resolved_memory_id
    assert second.resolution_type == MemoryResolutionType.NEW_MEMORY


def test_auto_merge_when_similarity_passes_threshold(tmp_path: Path) -> None:
    config = MemoryEngineConfig(
        similarity_threshold=0.6,
        auto_merge_threshold=0.6,
        ambiguous_threshold=0.5,
        ambiguous_gap_threshold=0.0,
    )
    engine = _engine(tmp_path, config=config)
    initial = engine.resolve_failure(_incoming(message="merchant terminal complete allowed", endpoint="/merchant/orders/1/complete"))
    merged = engine.resolve_failure(
        _incoming(
            message="merchant terminal complete allowed repeated",
            endpoint="/merchant/orders/2/complete",
            root_cause="terminal mutation guard missing",
            component="merchant_transition",
        )
    )
    assert merged.resolution_type == MemoryResolutionType.SIMILAR_MATCH
    assert merged.resolved_memory_id == initial.resolved_memory_id


def test_ambiguous_match_behavior_does_not_merge(tmp_path: Path) -> None:
    config = MemoryEngineConfig(
        similarity_threshold=0.9,
        auto_merge_threshold=0.95,
        ambiguous_threshold=0.2,
        ambiguous_gap_threshold=0.25,
    )
    engine = _engine(tmp_path, config=config)
    left = engine.resolve_failure(_incoming(message="store invalid id returns 500", endpoint="/store/invalid"))
    right = engine.resolve_failure(
        _incoming(
            message="store invalid unique id returns 500",
            endpoint="/store/unique-invalid",
            component="store_unique_api",
            fingerprint="STORE-API-006",
        )
    )
    candidate = engine.resolve_failure(
        _incoming(
            message="store invalid lookup returning 500",
            endpoint="/store/lookup",
            root_cause="invalid lookup not guarded",
            component="store_lookup",
            fingerprint="STORE-API-007",
        )
    )
    assert candidate.resolution_type == MemoryResolutionType.AMBIGUOUS_MATCH
    assert candidate.resolved_memory_id in {left.resolved_memory_id, right.resolved_memory_id}


def test_occurrence_count_update_on_recurrence(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    first = engine.resolve_failure(_incoming())
    second = engine.resolve_failure(_incoming())
    assert second.matched_record is not None
    assert second.matched_record.occurrence_count >= 2
    assert second.resolved_memory_id == first.resolved_memory_id


def test_action_effectiveness_scoring(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    result = engine.resolve_failure(_incoming())
    mem_id = str(result.resolved_memory_id)
    updated = engine.record_action_outcome(
        memory_id=mem_id,
        adapter_id="rankmate",
        action_type="rerun",
        strategy="standard",
        result="success",
        notes="first rerun worked",
    )
    assert updated is not None
    stats = updated.action_effectiveness.get("rerun")
    assert isinstance(stats, dict)
    assert stats["success_count"] == 1
    assert stats["failure_count"] == 0
    assert stats["effectiveness_score"] > 0.0


def test_best_action_selection(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    result = engine.resolve_failure(_incoming())
    mem_id = str(result.resolved_memory_id)
    engine.record_action_outcome(
        memory_id=mem_id,
        adapter_id="rankmate",
        action_type="rerun",
        strategy="standard",
        result="failed",
    )
    engine.record_action_outcome(
        memory_id=mem_id,
        adapter_id="rankmate",
        action_type="increase_timeout",
        strategy="adaptive",
        result="success",
    )
    best = engine.get_best_action(memory_id=mem_id, adapter_id="rankmate")
    assert best is not None
    assert best["action_type"] == "increase_timeout"


def test_confidence_evolution_on_recurrence_and_contradiction(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    first = engine.resolve_failure(_incoming(confidence=0.4, root_cause="state guard missing"))
    second = engine.resolve_failure(_incoming(confidence=0.8, root_cause="state guard missing"))
    assert second.matched_record is not None
    assert second.matched_record.confidence >= first.confidence

    contradictory = engine.resolve_failure(_incoming(confidence=0.2, root_cause="different root cause statement"))
    assert contradictory.matched_record is not None
    assert contradictory.matched_record.confidence <= second.matched_record.confidence


def test_graceful_behavior_when_vector_backend_unavailable(tmp_path: Path) -> None:
    engine = _engine(tmp_path, vector_available=False)
    first = engine.resolve_failure(_incoming(message="alpha"))
    second = engine.resolve_failure(_incoming(message="beta", endpoint="/other"))
    assert first.resolution_type == MemoryResolutionType.NEW_MEMORY
    assert second.resolution_type == MemoryResolutionType.NEW_MEMORY
