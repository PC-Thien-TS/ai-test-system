from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentBlock:
    source_file: str
    text: str
    headings: list[str]
    block_index: int


@dataclass(frozen=True)
class DomainKBConfig:
    top_k_per_step: dict[str, int] = field(default_factory=dict)
    step_queries: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class KBConfig:
    embedding_model_name: str
    embedding_local_path: str | None
    local_files_only: bool
    chunk_size_chars: int
    chunk_overlap_chars: int
    index_backend: str
    default_top_k: int
    max_pack_chars: int
    domain: DomainKBConfig

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_file: str
    text: str
    char_len: int
    token_estimate: int
    headings: list[str]
    doc_order: int


@dataclass(frozen=True)
class IndexManifest:
    domain: str
    backend: str
    embedding_model_name: str
    embedding_local_path: str | None
    dimension: int
    chunk_count: int
    doc_count: int
    created_at: str
    config_snapshot: dict[str, Any]


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    score: float
    source_file: str
    text: str
    headings: list[str]
