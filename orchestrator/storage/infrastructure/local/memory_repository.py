from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from orchestrator.storage.domain.models import FailureMemoryRecord, FailureSignature, utc_now
from orchestrator.storage.domain.repositories import MemoryRepository


class LocalMemoryRepository(MemoryRepository):
    def __init__(self, sqlite_path: Path):
        self._sqlite_path = sqlite_path
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS failure_memory (
                    memory_id TEXT PRIMARY KEY,
                    adapter_id TEXT NOT NULL,
                    project_id TEXT,
                    signature_hash TEXT NOT NULL,
                    signature_json TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    occurrence_count INTEGER NOT NULL,
                    flaky INTEGER NOT NULL,
                    recommended_actions_json TEXT NOT NULL,
                    action_history_json TEXT NOT NULL,
                    action_effectiveness_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_failure_memory_adapter_signature
                ON failure_memory(adapter_id, signature_hash);
                CREATE INDEX IF NOT EXISTS idx_failure_memory_adapter_last_seen
                ON failure_memory(adapter_id, last_seen DESC);
                """
            )
            columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(failure_memory)").fetchall()
            }
            if "action_effectiveness_json" not in columns:
                conn.execute(
                    "ALTER TABLE failure_memory ADD COLUMN action_effectiveness_json TEXT NOT NULL DEFAULT '{}'"
                )
                conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> FailureMemoryRecord:
        payload = {
            "memory_id": row["memory_id"],
            "adapter_id": row["adapter_id"],
            "project_id": row["project_id"],
            "signature": json.loads(row["signature_json"]),
            "signature_hash": row["signature_hash"],
            "root_cause": row["root_cause"],
            "severity": row["severity"],
            "confidence": row["confidence"],
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "occurrence_count": row["occurrence_count"],
            "flaky": bool(row["flaky"]),
            "recommended_actions": json.loads(row["recommended_actions_json"]),
            "action_history": json.loads(row["action_history_json"]),
            "action_effectiveness": json.loads(row["action_effectiveness_json"] or "{}"),
            "metadata": json.loads(row["metadata_json"]),
        }
        return FailureMemoryRecord.from_dict(payload)

    def get_memory(self, memory_id: str, adapter_id: Optional[str] = None) -> Optional[FailureMemoryRecord]:
        with self._lock, self._connect() as conn:
            if adapter_id:
                row = conn.execute(
                    "SELECT * FROM failure_memory WHERE memory_id = ? AND adapter_id = ?",
                    (memory_id, adapter_id),
                ).fetchone()
            else:
                row = conn.execute("SELECT * FROM failure_memory WHERE memory_id = ?", (memory_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def lookup_by_signature(self, *, adapter_id: str, signature: FailureSignature) -> Optional[FailureMemoryRecord]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM failure_memory WHERE adapter_id = ? AND signature_hash = ?",
                (adapter_id, signature.hash()),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_recent(self, *, adapter_id: str, limit: int = 50) -> list[FailureMemoryRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM failure_memory WHERE adapter_id = ? ORDER BY last_seen DESC LIMIT ?",
                (adapter_id, max(limit, 0)),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def upsert_memory(self, record: FailureMemoryRecord) -> FailureMemoryRecord:
        signature_hash = record.signature_hash or record.signature.hash()
        record.signature_hash = signature_hash
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM failure_memory WHERE adapter_id = ? AND signature_hash = ?",
                (record.adapter_id, signature_hash),
            ).fetchone()

            if existing is None:
                payload = record.to_dict()
                conn.execute(
                    """
                    INSERT INTO failure_memory (
                        memory_id, adapter_id, project_id, signature_hash, signature_json,
                        root_cause, severity, confidence, first_seen, last_seen,
                        occurrence_count, flaky, recommended_actions_json, action_history_json,
                        action_effectiveness_json, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["memory_id"],
                        payload["adapter_id"],
                        payload.get("project_id"),
                        signature_hash,
                        json.dumps(payload["signature"], ensure_ascii=False, sort_keys=True),
                        payload["root_cause"],
                        payload["severity"],
                        float(payload["confidence"]),
                        payload["first_seen"],
                        payload["last_seen"],
                        int(payload["occurrence_count"]),
                        1 if payload["flaky"] else 0,
                        json.dumps(payload["recommended_actions"], ensure_ascii=False),
                        json.dumps(payload["action_history"], ensure_ascii=False),
                        json.dumps(payload.get("action_effectiveness", {}), ensure_ascii=False),
                        json.dumps(payload["metadata"], ensure_ascii=False),
                    ),
                )
                conn.commit()
                return record

            existing_record = self._row_to_record(existing)
            existing_record.last_seen = utc_now()
            existing_record.occurrence_count += max(record.occurrence_count, 1)
            existing_record.root_cause = record.root_cause or existing_record.root_cause
            existing_record.severity = record.severity or existing_record.severity
            existing_record.confidence = max(existing_record.confidence, record.confidence)
            existing_record.flaky = existing_record.flaky or record.flaky
            existing_record.project_id = record.project_id or existing_record.project_id
            existing_record.recommended_actions = sorted(
                set(existing_record.recommended_actions).union(record.recommended_actions)
            )
            existing_record.action_history.extend(record.action_history)
            merged_effectiveness = dict(existing_record.action_effectiveness or {})
            merged_effectiveness.update(record.action_effectiveness or {})
            existing_record.action_effectiveness = merged_effectiveness
            merged_metadata = dict(existing_record.metadata)
            merged_metadata.update(record.metadata)
            existing_record.metadata = merged_metadata

            payload = existing_record.to_dict()
            conn.execute(
                """
                UPDATE failure_memory
                SET project_id = ?,
                    root_cause = ?,
                    severity = ?,
                    confidence = ?,
                    last_seen = ?,
                    occurrence_count = ?,
                    flaky = ?,
                    recommended_actions_json = ?,
                    action_history_json = ?,
                    action_effectiveness_json = ?,
                    metadata_json = ?
                WHERE adapter_id = ? AND signature_hash = ?
                """,
                (
                    payload.get("project_id"),
                    payload["root_cause"],
                    payload["severity"],
                    float(payload["confidence"]),
                    payload["last_seen"],
                    int(payload["occurrence_count"]),
                    1 if payload["flaky"] else 0,
                    json.dumps(payload["recommended_actions"], ensure_ascii=False),
                    json.dumps(payload["action_history"], ensure_ascii=False),
                    json.dumps(payload.get("action_effectiveness", {}), ensure_ascii=False),
                    json.dumps(payload["metadata"], ensure_ascii=False),
                    existing_record.adapter_id,
                    signature_hash,
                ),
            )
            conn.commit()
            return existing_record
