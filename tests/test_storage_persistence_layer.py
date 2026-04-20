from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.storage.application.services import MemoryService
from orchestrator.storage.domain.models import FailureSignature, StorageMode
from orchestrator.storage.infrastructure.factory import build_storage_provider
from orchestrator.storage.infrastructure.local.memory_repository import LocalMemoryRepository
from orchestrator.storage.infrastructure.server.stubs import UnavailableVectorMemoryRepository


def _set_local_env(monkeypatch: pytest.MonkeyPatch, base_dir: Path) -> None:
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("ARTIFACT_BACKEND", "local_fs")
    monkeypatch.setenv("MEMORY_BACKEND", "sqlite")
    monkeypatch.setenv("VECTOR_BACKEND", "local_stub")
    monkeypatch.setenv("STORAGE_BASE_DIR", str(base_dir))
    monkeypatch.setenv("AI_TESTING_ADAPTER", "rankmate")


def test_run_repository_crud_and_status_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_local_env(monkeypatch, tmp_path / "storage")
    provider = build_storage_provider(repo_root=tmp_path)

    run = provider.run_service.create_run(adapter_id="rankmate", project_id="order_core")
    assert run.run_id
    assert run.status == "pending"

    updated = provider.run_service.mark_run_status(run_id=run.run_id, status="running")
    assert updated is not None
    assert updated.status == "running"

    done = provider.run_service.mark_run_status(
        run_id=run.run_id,
        status="completed",
        summary={"passed": 10, "failed": 0},
    )
    assert done is not None
    assert done.completed_at is not None
    assert done.summary == {"passed": 10, "failed": 0}

    listed = provider.run_service.list_runs(adapter_id="rankmate", project_id="order_core")
    assert len(listed) == 1
    assert listed[0].run_id == run.run_id


def test_artifact_store_metadata_correctness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_local_env(monkeypatch, tmp_path / "storage")
    provider = build_storage_provider(repo_root=tmp_path)
    run = provider.run_service.create_run(adapter_id="rankmate", project_id="order_core")

    content = b"hello-storage"
    artifact = provider.artifact_service.store_bytes(
        run_id=run.run_id,
        adapter_id="rankmate",
        artifact_name="run.log",
        content=content,
        content_type="text/plain",
        metadata={"stage": "smoke"},
    )

    assert artifact.size_bytes == len(content)
    assert artifact.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert artifact.metadata["stage"] == "smoke"
    assert Path(artifact.storage_path).exists()

    items = provider.artifact_service.list_run_artifacts(run_id=run.run_id, adapter_id="rankmate")
    assert len(items) == 1
    assert items[0].artifact_id == artifact.artifact_id


def test_memory_exact_signature_lookup_and_occurrence_increment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_local_env(monkeypatch, tmp_path / "storage")
    provider = build_storage_provider(repo_root=tmp_path)

    signature = FailureSignature(
        fingerprint="ORD-API-014",
        error_type="HTTP_500",
        component="order_api",
        endpoint="/api/v1/orders/{id}/retry-payment",
    )
    first = provider.memory_service.remember_failure(
        adapter_id="rankmate",
        project_id="order_core",
        signature=signature,
        root_cause="Missing invalid-state guard",
        severity="P1",
        confidence=0.9,
        recommended_actions=["Add retry precondition guard"],
    )
    second = provider.memory_service.remember_failure(
        adapter_id="rankmate",
        project_id="order_core",
        signature=signature,
        root_cause="Missing invalid-state guard",
        severity="P1",
        confidence=0.8,
    )

    assert first.memory_id == second.memory_id
    assert second.occurrence_count >= 2
    exact = provider.memory_service.exact_lookup(adapter_id="rankmate", signature=signature)
    assert exact is not None
    assert exact.memory_id == second.memory_id
    assert exact.occurrence_count >= 2


def test_config_driven_backend_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_local_env(monkeypatch, tmp_path / "storage")
    provider = build_storage_provider(repo_root=tmp_path)
    assert provider.config.storage_mode == StorageMode.LOCAL
    assert provider.vector_repository.is_available is True

    monkeypatch.setenv("STORAGE_MODE", "server")
    provider_server = build_storage_provider(repo_root=tmp_path)
    assert provider_server.config.storage_mode == StorageMode.SERVER
    assert provider_server.vector_repository.is_available is False


def test_service_layer_full_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_local_env(monkeypatch, tmp_path / "storage")
    provider = build_storage_provider(repo_root=tmp_path)

    run = provider.run_service.create_run(adapter_id="rankmate", project_id="merchant_flow")
    artifact = provider.artifact_service.store_text(
        run_id=run.run_id,
        adapter_id=run.adapter_id,
        artifact_name="summary.md",
        text="# run summary",
    )
    provider.run_service.attach_release_decision(
        run_id=run.run_id,
        release_decision_ref="artifacts/adapter_evidence/rankmate/release_decision.json",
    )
    fetched = provider.run_service.get_run(run.run_id)

    signature = FailureSignature(
        fingerprint="MER-API-021",
        error_type="HTTP_200_TERMINAL_REPEAT",
        component="merchant_transition",
        endpoint="/api/v1/merchant/orders/{id}/complete",
    )
    memory = provider.memory_service.remember_failure(
        adapter_id="rankmate",
        project_id="merchant_flow",
        signature=signature,
        root_cause="Repeat complete allowed on terminal order",
        severity="P1",
        confidence=0.95,
        semantic_text="merchant stale terminal mutation repeat complete returns 200",
    )
    similar = provider.memory_service.similar_lookup(
        adapter_id="rankmate",
        query_text="terminal order repeated complete accepted",
        top_k=3,
        min_score=0.01,
    )

    assert fetched is not None
    assert fetched.release_decision_ref is not None
    assert artifact.run_id == run.run_id
    assert memory.memory_id
    assert len(similar) >= 1


def test_graceful_behavior_when_vector_backend_unavailable(tmp_path: Path) -> None:
    memory_repo = LocalMemoryRepository(tmp_path / "memory.sqlite3")
    vector_repo = UnavailableVectorMemoryRepository()
    service = MemoryService(memory_repo, vector_repo)

    signature = FailureSignature(
        fingerprint="STORE-API-004",
        error_type="HTTP_500",
        component="store_api",
        endpoint="/api/v1/store/{id}",
    )
    service.remember_failure(
        adapter_id="rankmate",
        signature=signature,
        root_cause="Invalid store lookup returns 500",
        severity="P2",
        confidence=0.8,
    )

    matches = service.similar_lookup(adapter_id="rankmate", query_text="invalid store lookup", top_k=5)
    assert matches == []
