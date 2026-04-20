from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ..domain.models import LarkNotificationAuditRecord


class LarkNotificationAuditStore:
    def __init__(self, audit_root: Path) -> None:
        self.audit_root = audit_root
        self.index_root = self.audit_root.parent / "indexes"
        self.index_file = self.index_root / "lark_notifications_index.json"

    def write_record(self, record: LarkNotificationAuditRecord) -> str:
        self.audit_root.mkdir(parents=True, exist_ok=True)
        payload = asdict(record)
        file_path = self.audit_root / f"{record.notification_id}.json"
        file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._append_index(payload, str(file_path))
        return str(file_path)

    def _append_index(self, record: Dict[str, Any], record_path: str) -> None:
        self.index_root.mkdir(parents=True, exist_ok=True)
        current: List[Dict[str, Any]] = []
        if self.index_file.exists():
            try:
                loaded = json.loads(self.index_file.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    current = loaded
            except Exception:
                current = []
        current.append(
            {
                "notification_id": record.get("notification_id", ""),
                "timestamp": record.get("timestamp", ""),
                "source_type": record.get("source_type", ""),
                "source_id": record.get("source_id", ""),
                "event_type": record.get("event_type", ""),
                "status": record.get("status", ""),
                "dry_run": bool(record.get("dry_run", False)),
                "adapter_id": record.get("adapter_id", ""),
                "project_id": record.get("project_id", ""),
                "candidate_id": record.get("candidate_id", ""),
                "run_id": record.get("run_id", ""),
                "failure_id": record.get("failure_id", ""),
                "record_path": record_path,
                "rationale": record.get("rationale", ""),
            }
        )
        self.index_file.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")

