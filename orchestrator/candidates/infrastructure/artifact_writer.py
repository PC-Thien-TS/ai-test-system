from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

from ..domain.formatting import to_jsonable
from ..domain.models import CandidateSuppressionRecord, CandidateType
from .local_index_store import LocalCandidateIndexStore


class CandidateArtifactWriter:
    def __init__(self, root_dir: Path, index_store: LocalCandidateIndexStore) -> None:
        self.root_dir = root_dir
        self.index_store = index_store
        self.bug_dir = self.root_dir / "bugs"
        self.incident_dir = self.root_dir / "incidents"
        self.suppression_dir = self.root_dir / "suppressions"
        self.bug_dir.mkdir(parents=True, exist_ok=True)
        self.incident_dir.mkdir(parents=True, exist_ok=True)
        self.suppression_dir.mkdir(parents=True, exist_ok=True)

    def _json_dump(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _artifact_path(self, candidate_type: CandidateType, candidate_id: str) -> Path:
        if candidate_type == CandidateType.BUG:
            return self.bug_dir / f"{candidate_id}.json"
        if candidate_type == CandidateType.INCIDENT:
            return self.incident_dir / f"{candidate_id}.json"
        return self.suppression_dir / f"{candidate_id}.json"

    def write_candidate(self, *, candidate_type: CandidateType, artifact: Any) -> str:
        payload = to_jsonable(artifact)
        candidate_id = str(payload.get("candidate_id", ""))
        path = self._artifact_path(candidate_type, candidate_id)
        self._json_dump(path, payload)
        return str(path)

    def update_existing_candidate(self, *, candidate_type: CandidateType, candidate_id: str, artifact: Any) -> str:
        return self.write_candidate(candidate_type=candidate_type, artifact=artifact)

    def write_candidate_index(self, *, index_name: str, entry: Dict[str, Any]) -> None:
        self.index_store.upsert_entry(index_name, entry)

    def write_suppression_record(self, record: CandidateSuppressionRecord) -> str:
        payload = to_jsonable(record)
        suppression_id = str(payload.get("suppression_id", ""))
        path = self._artifact_path(CandidateType.SUPPRESSION, suppression_id)
        self._json_dump(path, payload)
        return str(path)

