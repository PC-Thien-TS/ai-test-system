from __future__ import annotations

from datetime import datetime
from typing import Optional

from orchestrator.storage.domain.models import (
    ArtifactRecord,
    FailureMemoryRecord,
    FailureSignature,
    RunRecord,
    SimilarMemoryMatch,
    utc_now,
)
from orchestrator.storage.domain.repositories import (
    ArtifactRepository,
    MemoryRepository,
    RunRepository,
    VectorMemoryRepository,
)


class RunService:
    def __init__(self, repository: RunRepository):
        self._repo = repository

    def create_run(
        self,
        *,
        adapter_id: str,
        project_id: str,
        status: str = "pending",
        metadata: Optional[dict] = None,
    ) -> RunRecord:
        record = RunRecord.new(adapter_id=adapter_id, project_id=project_id, status=status)
        if metadata:
            record.metadata.update(metadata)
        return self._repo.save_run(record)

    def get_run(self, run_id: str, adapter_id: Optional[str] = None) -> Optional[RunRecord]:
        return self._repo.get_run(run_id, adapter_id=adapter_id)

    def list_runs(
        self,
        *,
        adapter_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[RunRecord]:
        return self._repo.list_runs(
            adapter_id=adapter_id,
            project_id=project_id,
            status=status,
            limit=limit,
        )

    def mark_run_status(
        self,
        *,
        run_id: str,
        status: str,
        summary: Optional[dict] = None,
        metadata: Optional[dict] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[RunRecord]:
        done_states = {"completed", "failed", "cancelled"}
        final_completed_at = completed_at
        if status in done_states and final_completed_at is None:
            final_completed_at = utc_now()
        return self._repo.update_run_status(
            run_id=run_id,
            status=status,
            completed_at=final_completed_at,
            summary=summary,
            metadata=metadata,
        )

    def attach_release_decision(self, *, run_id: str, release_decision_ref: str) -> Optional[RunRecord]:
        return self._repo.attach_release_decision(run_id=run_id, release_decision_ref=release_decision_ref)


class ArtifactService:
    def __init__(self, repository: ArtifactRepository):
        self._repo = repository

    def store_bytes(
        self,
        *,
        run_id: str,
        adapter_id: str,
        artifact_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> ArtifactRecord:
        return self._repo.store_artifact(
            run_id=run_id,
            adapter_id=adapter_id,
            artifact_name=artifact_name,
            content=content,
            content_type=content_type,
            metadata=metadata,
        )

    def store_text(
        self,
        *,
        run_id: str,
        adapter_id: str,
        artifact_name: str,
        text: str,
        content_type: str = "text/plain; charset=utf-8",
        metadata: Optional[dict] = None,
    ) -> ArtifactRecord:
        return self.store_bytes(
            run_id=run_id,
            adapter_id=adapter_id,
            artifact_name=artifact_name,
            content=text.encode("utf-8"),
            content_type=content_type,
            metadata=metadata,
        )

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        return self._repo.get_artifact(artifact_id)

    def list_run_artifacts(self, *, run_id: str, adapter_id: Optional[str] = None) -> list[ArtifactRecord]:
        return self._repo.list_artifacts(run_id=run_id, adapter_id=adapter_id)


class MemoryService:
    def __init__(self, repository: MemoryRepository, vector_repository: VectorMemoryRepository):
        self._repo = repository
        self._vector_repo = vector_repository

    def remember_failure(
        self,
        *,
        adapter_id: str,
        signature: FailureSignature,
        root_cause: str,
        severity: str,
        confidence: float,
        project_id: Optional[str] = None,
        flaky: bool = False,
        recommended_actions: Optional[list[str]] = None,
        action_note: Optional[str] = None,
        metadata: Optional[dict] = None,
        semantic_text: Optional[str] = None,
    ) -> FailureMemoryRecord:
        record = FailureMemoryRecord.new(
            adapter_id=adapter_id,
            project_id=project_id,
            signature=signature,
            root_cause=root_cause,
            severity=severity,
            confidence=confidence,
            flaky=flaky,
            recommended_actions=recommended_actions or [],
            metadata=metadata or {},
        )
        if action_note:
            record.action_history.append({"timestamp": utc_now().isoformat(), "note": action_note})
        stored = self._repo.upsert_memory(record)

        if self._vector_repo.is_available:
            vector_text = semantic_text or " | ".join(
                [
                    signature.fingerprint,
                    signature.error_type,
                    signature.component,
                    root_cause,
                    " ".join(stored.recommended_actions),
                ]
            )
            self._vector_repo.upsert_vector(
                memory_id=stored.memory_id,
                adapter_id=adapter_id,
                text=vector_text,
                metadata={"severity": stored.severity, "root_cause": stored.root_cause},
            )
        return stored

    def exact_lookup(self, *, adapter_id: str, signature: FailureSignature) -> Optional[FailureMemoryRecord]:
        return self._repo.lookup_by_signature(adapter_id=adapter_id, signature=signature)

    def similar_lookup(
        self,
        *,
        adapter_id: str,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list[SimilarMemoryMatch]:
        if not self._vector_repo.is_available:
            return []
        return self._vector_repo.search_similar(
            adapter_id=adapter_id,
            query_text=query_text,
            top_k=top_k,
            min_score=min_score,
        )

    def get_memory(self, memory_id: str, adapter_id: Optional[str] = None) -> Optional[FailureMemoryRecord]:
        return self._repo.get_memory(memory_id, adapter_id=adapter_id)
