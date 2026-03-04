from __future__ import annotations

import math
import re

from kb._lib.types import ChunkRecord, DocumentBlock


def chunk_blocks(
    blocks: list[DocumentBlock],
    *,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
) -> list[ChunkRecord]:
    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be > 0")
    if chunk_overlap_chars < 0:
        raise ValueError("chunk_overlap_chars must be >= 0")
    if chunk_overlap_chars >= chunk_size_chars:
        raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")

    counters: dict[str, int] = {}
    chunks: list[ChunkRecord] = []

    for doc_order, block in enumerate(blocks):
        source_stem = sanitize_source_stem(block.source_file)
        start = 0
        text = block.text.strip()
        if not text:
            continue
        while start < len(text):
            end = min(len(text), start + chunk_size_chars)
            window = text[start:end].strip()
            if not window:
                break
            chunk_index = counters.get(source_stem, 0)
            counters[source_stem] = chunk_index + 1
            chunks.append(
                ChunkRecord(
                    chunk_id=f"{source_stem}::{chunk_index:04d}",
                    source_file=block.source_file,
                    text=window,
                    char_len=len(window),
                    token_estimate=math.ceil(len(window) / 4),
                    headings=list(block.headings),
                    doc_order=doc_order,
                )
            )
            if end >= len(text):
                break
            start = max(end - chunk_overlap_chars, start + 1)
    return chunks


def sanitize_source_stem(source_file: str) -> str:
    stem = source_file.rsplit(".", 1)[0]
    return re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "document"
