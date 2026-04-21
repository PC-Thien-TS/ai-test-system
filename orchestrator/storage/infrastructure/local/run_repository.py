from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from orchestrator.storage.domain.models import RunRecord
from orchestrator.storage.domain.repositories import RunRepository


class LocalRunRepository(RunRepository):
    def __init__(self, data_path: Path):
        self._data_path = data_path
        self._lock = threading.RLock()
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._data_path.exists():
            self._save_all({})

    def _load_all(self) -> dict[str, dict]:
        try:
            raw = json.loads(self._data_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return raw

    def _save_all(self, payload: dict[str, dict]) -> None:
        tmp = self._data_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._data_path)

    def save_run(self, record: RunRecord) -> RunRecord:
        with self._lock:
            data = self._load_all()
            data[record.run_id] = record.to_dict()
            self._save_all(data)
        return record

    def get_run(self, run_id: str, adapter_id: Optional[str] = None) -> Optional[RunRecord]:
        with self._lock:
            data = self._load_all()
            payload = data.get(run_id)
        if not isinstance(payload, dict):
            return None
        record = RunRecord.from_dict(payload)
        if adapter_id and record.adapter_id != adapter_id:
            return None
        return record

    def list_runs(
        self,
        *,
        adapter_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[RunRecord]:
        with self._lock:
            data = self._load_all()
        runs = [RunRecord.from_dict(item) for item in data.values() if isinstance(item, dict)]
        filtered: list[RunRecord] = []
        for run in runs:
            if adapter_id and run.adapter_id != adapter_id:
                continue
            if project_id and run.project_id != project_id:
                continue
            if status and run.status != status:
                continue
            filtered.append(run)
        filtered.sort(key=lambda x: x.started_at, reverse=True)
        return filtered[: max(limit, 0)]

    def update_run_status(
        self,
        *,
        run_id: str,
        status: str,
        completed_at: Optional[datetime] = None,
        summary: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[RunRecord]:
        with self._lock:
            data = self._load_all()
            payload = data.get(run_id)
            if not isinstance(payload, dict):
                return None
            run = RunRecord.from_dict(payload)
            run.status = status
            if completed_at is not None:
                run.completed_at = completed_at
            if summary is not None:
                run.summary = summary
            if metadata:
                run.metadata.update(metadata)
            data[run_id] = run.to_dict()
            self._save_all(data)
        return run

    def attach_release_decision(self, *, run_id: str, release_decision_ref: str) -> Optional[RunRecord]:
        with self._lock:
            data = self._load_all()
            payload = data.get(run_id)
            if not isinstance(payload, dict):
                return None
            run = RunRecord.from_dict(payload)
            run.release_decision_ref = release_decision_ref
            data[run_id] = run.to_dict()
            self._save_all(data)
        return run
