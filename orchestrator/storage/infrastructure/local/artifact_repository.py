from __future__ import annotations

import hashlib
import json
import threading
import uuid
from pathlib import Path
from typing import Optional

from orchestrator.storage.domain.models import ArtifactRecord, utc_now
from orchestrator.storage.domain.repositories import ArtifactRepository


def _safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", ".", "+"} else "_" for ch in name).strip("_") or "artifact"


class LocalArtifactRepository(ArtifactRepository):
    def __init__(self, artifact_root: Path):
        self._artifact_root = artifact_root
        self._metadata_path = artifact_root / "artifact_records.json"
        self._lock = threading.RLock()
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        if not self._metadata_path.exists():
            self._save_all({})

    def _load_all(self) -> dict[str, dict]:
        try:
            raw = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return raw

    def _save_all(self, payload: dict[str, dict]) -> None:
        tmp = self._metadata_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._metadata_path)

    def save_metadata(self, record: ArtifactRecord) -> ArtifactRecord:
        with self._lock:
            data = self._load_all()
            data[record.artifact_id] = record.to_dict()
            self._save_all(data)
        return record

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
        artifact_id = str(uuid.uuid4())
        name = _safe_name(artifact_name)
        adapter_dir = self._artifact_root / adapter_id / run_id
        adapter_dir.mkdir(parents=True, exist_ok=True)
        file_path = adapter_dir / f"{artifact_id}_{name}"
        file_path.write_bytes(content)

        checksum = hashlib.sha256(content).hexdigest()
        record = ArtifactRecord(
            artifact_id=artifact_id,
            run_id=run_id,
            adapter_id=adapter_id,
            artifact_name=artifact_name,
            storage_path=str(file_path),
            content_type=content_type,
            size_bytes=len(content),
            checksum_sha256=checksum,
            created_at=utc_now(),
            metadata=dict(metadata or {}),
        )
        return self.save_metadata(record)

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        with self._lock:
            data = self._load_all()
            payload = data.get(artifact_id)
        if not isinstance(payload, dict):
            return None
        return ArtifactRecord.from_dict(payload)

    def list_artifacts(self, *, run_id: str, adapter_id: Optional[str] = None) -> list[ArtifactRecord]:
        with self._lock:
            data = self._load_all()
        records = [ArtifactRecord.from_dict(item) for item in data.values() if isinstance(item, dict)]
        result: list[ArtifactRecord] = []
        for record in records:
            if record.run_id != run_id:
                continue
            if adapter_id and record.adapter_id != adapter_id:
                continue
            result.append(record)
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result
