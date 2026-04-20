from __future__ import annotations

from datetime import datetime
from typing import Optional

from orchestrator.storage.domain.errors import StorageBackendNotReady
from orchestrator.storage.domain.models import ArtifactRecord, FailureMemoryRecord, FailureSignature, RunRecord
from orchestrator.storage.domain.repositories import ArtifactRepository, MemoryRepository, RunRepository, VectorMemoryRepository


class _ServerBackendStub:
    def _raise(self) -> None:
        raise StorageBackendNotReady(
            "Server backend is configured but not implemented yet. "
            "Add PostgreSQL/object storage/vector backend implementation."
        )


class ServerRunRepositoryStub(_ServerBackendStub, RunRepository):
    def save_run(self, record: RunRecord) -> RunRecord:
        self._raise()

    def get_run(self, run_id: str, adapter_id: Optional[str] = None) -> Optional[RunRecord]:
        self._raise()

    def list_runs(
        self,
        *,
        adapter_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[RunRecord]:
        self._raise()

    def update_run_status(
        self,
        *,
        run_id: str,
        status: str,
        completed_at: Optional[datetime] = None,
        summary: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[RunRecord]:
        self._raise()

    def attach_release_decision(self, *, run_id: str, release_decision_ref: str) -> Optional[RunRecord]:
        self._raise()


class ServerArtifactRepositoryStub(_ServerBackendStub, ArtifactRepository):
    def store_artifact(
        self,
        *,
        run_id: str,
        adapter_id: str,
        artifact_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> ArtifactRecord:
        self._raise()

    def save_metadata(self, record: ArtifactRecord) -> ArtifactRecord:
        self._raise()

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        self._raise()

    def list_artifacts(self, *, run_id: str, adapter_id: Optional[str] = None) -> list[ArtifactRecord]:
        self._raise()


class ServerMemoryRepositoryStub(_ServerBackendStub, MemoryRepository):
    def upsert_memory(self, record: FailureMemoryRecord) -> FailureMemoryRecord:
        self._raise()

    def get_memory(self, memory_id: str, adapter_id: Optional[str] = None) -> Optional[FailureMemoryRecord]:
        self._raise()

    def lookup_by_signature(self, *, adapter_id: str, signature: FailureSignature) -> Optional[FailureMemoryRecord]:
        self._raise()

    def list_recent(self, *, adapter_id: str, limit: int = 50) -> list[FailureMemoryRecord]:
        self._raise()


class UnavailableVectorMemoryRepository(VectorMemoryRepository):
    @property
    def is_available(self) -> bool:
        return False

    def upsert_vector(
        self,
        *,
        memory_id: str,
        adapter_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        return None

    def search_similar(
        self,
        *,
        adapter_id: str,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list:
        return []
