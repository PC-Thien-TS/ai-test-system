from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class LocalCandidateIndexStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.index_dir = self.root_dir / "indexes"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def _index_path(self, index_name: str) -> Path:
        return self.index_dir / index_name

    def load_index(self, index_name: str) -> List[Dict[str, Any]]:
        path = self._index_path(index_name)
        if not path.exists():
            return []
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(content, list):
                return content
        except Exception:
            return []
        return []

    def save_index(self, index_name: str, entries: List[Dict[str, Any]]) -> None:
        path = self._index_path(index_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def find_by_key(self, index_name: str, candidate_key: str) -> Dict[str, Any] | None:
        for entry in self.load_index(index_name):
            if str(entry.get("candidate_key", "")) == candidate_key:
                return entry
        return None

    def upsert_entry(self, index_name: str, entry: Dict[str, Any]) -> None:
        entries = self.load_index(index_name)
        key = str(entry.get("candidate_key", ""))
        updated = False
        for idx, existing in enumerate(entries):
            if str(existing.get("candidate_key", "")) == key:
                entries[idx] = entry
                updated = True
                break
        if not updated:
            entries.append(entry)
        self.save_index(index_name, entries)

