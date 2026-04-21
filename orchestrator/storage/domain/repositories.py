from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from orchestrator.storage.domain.models import (
    ArtifactRecord,
    FailureMemoryRecord,
    FailureSignature,
    RunRecord,
    SimilarMemoryMatch,
)


@runtime_checkable
class RunRepository(Protocol):
    def save_run(self, record: RunRecord) -> RunRecord: ...

    def get_run(self, run_id: str, adapter_id: Optional[str] = None) -> Optional[RunRecord]: ...

    def list_runs(
        self,
        *,
        adapter_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[RunRecord]: ...

    def update_run_status(
        self,
        *,
        run_id: str,
        status: str,
        completed_at: Optional[datetime] = None,
        summary: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[RunRecord]: ...

    def attach_release_decision(self, *, run_id: str, release_decision_ref: str) -> Optional[RunRecord]: ...


@runtime_checkable
class ArtifactRepository(Protocol):
    def store_artifact(
        self,
        *,
        run_id: str,
        adapter_id: str,
        artifact_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> ArtifactRecord: ...

    def save_metadata(self, record: ArtifactRecord) -> ArtifactRecord: ...

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]: ...

    def list_artifacts(self, *, run_id: str, adapter_id: Optional[str] = None) -> list[ArtifactRecord]: ...


@runtime_checkable
class MemoryRepository(Protocol):
    def upsert_memory(self, record: FailureMemoryRecord) -> FailureMemoryRecord: ...

    def get_memory(self, memory_id: str, adapter_id: Optional[str] = None) -> Optional[FailureMemoryRecord]: ...

    def lookup_by_signature(self, *, adapter_id: str, signature: FailureSignature) -> Optional[FailureMemoryRecord]: ...

    def list_recent(self, *, adapter_id: str, limit: int = 50) -> list[FailureMemoryRecord]: ...


@runtime_checkable
class VectorMemoryRepository(Protocol):
    @property
    def is_available(self) -> bool: ...

    def upsert_vector(
        self,
        *,
        memory_id: str,
        adapter_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None: ...

    def search_similar(
        self,
        *,
        adapter_id: str,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list[SimilarMemoryMatch]: ...
