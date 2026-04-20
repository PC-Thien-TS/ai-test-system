from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


class StorageMode(str, Enum):
    LOCAL = "local"
    SERVER = "server"


class ArtifactBackend(str, Enum):
    LOCAL_FS = "local_fs"
    S3_STUB = "s3_stub"


class MemoryBackend(str, Enum):
    JSON = "json"
    SQLITE = "sqlite"
    POSTGRES_STUB = "postgres_stub"


class VectorBackend(str, Enum):
    LOCAL_STUB = "local_stub"
    FAISS_STUB = "faiss_stub"
    QDRANT_STUB = "qdrant_stub"


@dataclass(slots=True)
class StorageConfig:
    storage_mode: StorageMode = StorageMode.LOCAL
    artifact_backend: ArtifactBackend = ArtifactBackend.LOCAL_FS
    memory_backend: MemoryBackend = MemoryBackend.SQLITE
    vector_backend: VectorBackend = VectorBackend.LOCAL_STUB
    base_dir: Path = Path(".platform_storage")
    artifact_dir: Path = Path(".platform_storage/artifacts")
    run_data_path: Path = Path(".platform_storage/runs/run_records.json")
    memory_sqlite_path: Path = Path(".platform_storage/memory/failure_memory.sqlite3")
    memory_json_path: Path = Path(".platform_storage/memory/failure_memory.json")
    vector_index_path: Path = Path(".platform_storage/memory/vector_memory.json")
    adapter_id: str = "rankmate"
    project_id: Optional[str] = None
    postgres_dsn: Optional[str] = None
    object_storage_bucket: Optional[str] = None
    vector_endpoint: Optional[str] = None

    @classmethod
    def from_env(cls, repo_root: Optional[Path] = None) -> "StorageConfig":
        root = repo_root or Path.cwd()
        mode = StorageMode(os.getenv("STORAGE_MODE", StorageMode.LOCAL.value).strip().lower())
        artifact_backend = ArtifactBackend(
            os.getenv("ARTIFACT_BACKEND", ArtifactBackend.LOCAL_FS.value).strip().lower()
        )
        memory_backend = MemoryBackend(os.getenv("MEMORY_BACKEND", MemoryBackend.SQLITE.value).strip().lower())
        vector_backend = VectorBackend(os.getenv("VECTOR_BACKEND", VectorBackend.LOCAL_STUB.value).strip().lower())

        base_dir_value = os.getenv("STORAGE_BASE_DIR", "").strip()
        base_dir = Path(base_dir_value) if base_dir_value else root / ".platform_storage"
        artifact_dir = base_dir / "artifacts"
        run_data_path = base_dir / "runs" / "run_records.json"
        memory_sqlite = base_dir / "memory" / "failure_memory.sqlite3"
        memory_json = base_dir / "memory" / "failure_memory.json"
        vector_index = base_dir / "memory" / "vector_memory.json"

        return cls(
            storage_mode=mode,
            artifact_backend=artifact_backend,
            memory_backend=memory_backend,
            vector_backend=vector_backend,
            base_dir=base_dir,
            artifact_dir=artifact_dir,
            run_data_path=run_data_path,
            memory_sqlite_path=memory_sqlite,
            memory_json_path=memory_json,
            vector_index_path=vector_index,
            adapter_id=os.getenv("AI_TESTING_ADAPTER", "rankmate").strip().lower() or "rankmate",
            project_id=os.getenv("AI_TESTING_PROJECT_ID", "").strip() or None,
            postgres_dsn=os.getenv("STORAGE_POSTGRES_DSN", "").strip() or None,
            object_storage_bucket=os.getenv("STORAGE_OBJECT_BUCKET", "").strip() or None,
            vector_endpoint=os.getenv("STORAGE_VECTOR_ENDPOINT", "").strip() or None,
        )


@dataclass(slots=True)
class RunRecord:
    run_id: str
    adapter_id: str
    project_id: str
    status: str
    started_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    summary: Optional[dict[str, Any]] = None
    release_decision_ref: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, adapter_id: str, project_id: str, status: str = "pending") -> "RunRecord":
        return cls(
            run_id=str(uuid.uuid4()),
            adapter_id=adapter_id,
            project_id=project_id,
            status=status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "adapter_id": self.adapter_id,
            "project_id": self.project_id,
            "status": self.status,
            "started_at": _iso(self.started_at),
            "completed_at": _iso(self.completed_at),
            "summary": self.summary,
            "release_decision_ref": self.release_decision_ref,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        return cls(
            run_id=str(data["run_id"]),
            adapter_id=str(data["adapter_id"]),
            project_id=str(data["project_id"]),
            status=str(data["status"]),
            started_at=_from_iso(data.get("started_at")) or utc_now(),
            completed_at=_from_iso(data.get("completed_at")),
            summary=data.get("summary"),
            release_decision_ref=data.get("release_decision_ref"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    run_id: str
    adapter_id: str
    artifact_name: str
    storage_path: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "run_id": self.run_id,
            "adapter_id": self.adapter_id,
            "artifact_name": self.artifact_name,
            "storage_path": self.storage_path,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "created_at": _iso(self.created_at),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRecord":
        return cls(
            artifact_id=str(data["artifact_id"]),
            run_id=str(data["run_id"]),
            adapter_id=str(data["adapter_id"]),
            artifact_name=str(data["artifact_name"]),
            storage_path=str(data["storage_path"]),
            content_type=str(data["content_type"]),
            size_bytes=int(data["size_bytes"]),
            checksum_sha256=str(data["checksum_sha256"]),
            created_at=_from_iso(data.get("created_at")) or utc_now(),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class FailureSignature:
    fingerprint: str
    error_type: str
    component: str
    endpoint: Optional[str] = None
    message_hash: Optional[str] = None
    plugin: Optional[str] = None
    normalized_stack_signature: Optional[str] = None
    raw_message_fingerprint: Optional[str] = None
    signature_hash: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def canonical_key(self) -> str:
        payload = {
            "fingerprint": self.fingerprint,
            "error_type": self.error_type,
            "component": self.component,
            "endpoint": self.endpoint or "",
            "message_hash": self.message_hash or self.raw_message_fingerprint or "",
            "plugin": self.plugin or "",
            "normalized_stack_signature": self.normalized_stack_signature or "",
            "metadata": self.metadata,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def hash(self) -> str:
        if self.signature_hash:
            return self.signature_hash
        return hashlib.sha256(self.canonical_key().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "error_type": self.error_type,
            "component": self.component,
            "endpoint": self.endpoint,
            "message_hash": self.message_hash,
            "plugin": self.plugin,
            "normalized_stack_signature": self.normalized_stack_signature,
            "raw_message_fingerprint": self.raw_message_fingerprint,
            "signature_hash": self.hash(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailureSignature":
        return cls(
            fingerprint=str(data["fingerprint"]),
            error_type=str(data["error_type"]),
            component=str(data["component"]),
            endpoint=data.get("endpoint"),
            message_hash=data.get("message_hash"),
            plugin=data.get("plugin"),
            normalized_stack_signature=data.get("normalized_stack_signature"),
            raw_message_fingerprint=data.get("raw_message_fingerprint"),
            signature_hash=data.get("signature_hash"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class FailureMemoryRecord:
    memory_id: str
    adapter_id: str
    project_id: Optional[str]
    signature: FailureSignature
    signature_hash: str
    root_cause: str
    severity: str
    confidence: float
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    flaky: bool
    recommended_actions: list[str] = field(default_factory=list)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    action_effectiveness: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        *,
        adapter_id: str,
        signature: FailureSignature,
        root_cause: str,
        severity: str,
        confidence: float,
        recommended_actions: Optional[list[str]] = None,
        project_id: Optional[str] = None,
        flaky: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "FailureMemoryRecord":
        now = utc_now()
        return cls(
            memory_id=str(uuid.uuid4()),
            adapter_id=adapter_id,
            project_id=project_id,
            signature=signature,
            signature_hash=signature.hash(),
            root_cause=root_cause,
            severity=severity,
            confidence=confidence,
            first_seen=now,
            last_seen=now,
            occurrence_count=1,
            flaky=flaky,
            recommended_actions=list(recommended_actions or []),
            action_history=[],
            action_effectiveness={},
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "adapter_id": self.adapter_id,
            "project_id": self.project_id,
            "signature": self.signature.to_dict(),
            "signature_hash": self.signature_hash or self.signature.hash(),
            "root_cause": self.root_cause,
            "severity": self.severity,
            "confidence": self.confidence,
            "first_seen": _iso(self.first_seen),
            "last_seen": _iso(self.last_seen),
            "occurrence_count": self.occurrence_count,
            "flaky": self.flaky,
            "recommended_actions": self.recommended_actions,
            "action_history": self.action_history,
            "action_effectiveness": self.action_effectiveness,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailureMemoryRecord":
        signature = FailureSignature.from_dict(dict(data["signature"]))
        return cls(
            memory_id=str(data["memory_id"]),
            adapter_id=str(data["adapter_id"]),
            project_id=data.get("project_id"),
            signature=signature,
            signature_hash=str(data.get("signature_hash") or signature.hash()),
            root_cause=str(data.get("root_cause") or ""),
            severity=str(data.get("severity") or "unknown"),
            confidence=float(data.get("confidence") or 0.0),
            first_seen=_from_iso(data.get("first_seen")) or utc_now(),
            last_seen=_from_iso(data.get("last_seen")) or utc_now(),
            occurrence_count=int(data.get("occurrence_count") or 1),
            flaky=bool(data.get("flaky")),
            recommended_actions=list(data.get("recommended_actions") or []),
            action_history=list(data.get("action_history") or []),
            action_effectiveness=dict(data.get("action_effectiveness") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class SimilarMemoryMatch:
    memory_id: str
    score: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "score": self.score,
            "reason": self.reason,
            "metadata": self.metadata,
        }
