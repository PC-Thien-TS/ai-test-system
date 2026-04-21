from __future__ import annotations

import json
import math
import re
import threading
from pathlib import Path
from typing import Optional

from orchestrator.storage.domain.models import SimilarMemoryMatch, utc_now
from orchestrator.storage.domain.repositories import VectorMemoryRepository

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _to_freq(tokens: list[str]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return freq


def _cosine(a: dict[str, int], b: dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a).intersection(b)
    if not shared:
        return 0.0
    dot = sum(a[token] * b[token] for token in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalVectorMemoryRepository(VectorMemoryRepository):
    def __init__(self, index_path: Path):
        self._index_path = index_path
        self._lock = threading.RLock()
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._index_path.exists():
            self._save([])

    @property
    def is_available(self) -> bool:
        return True

    def _load(self) -> list[dict]:
        try:
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    def _save(self, payload: list[dict]) -> None:
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._index_path)

    def upsert_vector(
        self,
        *,
        memory_id: str,
        adapter_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        tokens = _tokenize(text)
        freq = _to_freq(tokens)
        record = {
            "memory_id": memory_id,
            "adapter_id": adapter_id,
            "text": text,
            "token_freq": freq,
            "metadata": dict(metadata or {}),
            "updated_at": utc_now().isoformat(),
        }
        with self._lock:
            rows = self._load()
            updated = False
            for idx, row in enumerate(rows):
                if row.get("memory_id") == memory_id and row.get("adapter_id") == adapter_id:
                    rows[idx] = record
                    updated = True
                    break
            if not updated:
                rows.append(record)
            self._save(rows)

    def search_similar(
        self,
        *,
        adapter_id: str,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list[SimilarMemoryMatch]:
        query_freq = _to_freq(_tokenize(query_text))
        if not query_freq:
            return []

        with self._lock:
            rows = self._load()

        matches: list[SimilarMemoryMatch] = []
        for row in rows:
            if row.get("adapter_id") != adapter_id:
                continue
            vector = row.get("token_freq")
            if not isinstance(vector, dict):
                continue
            casted = {str(k): int(v) for k, v in vector.items() if isinstance(v, int)}
            score = _cosine(query_freq, casted)
            if score < min_score:
                continue
            matches.append(
                SimilarMemoryMatch(
                    memory_id=str(row.get("memory_id")),
                    score=score,
                    reason=f"token cosine similarity >= {min_score:.2f}",
                    metadata=dict(row.get("metadata") or {}),
                )
            )
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[: max(top_k, 0)]
