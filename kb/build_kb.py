from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kb._lib.chunking import chunk_blocks
from kb._lib.docx_extract import extract_document_blocks
from kb._lib.embedder import LocalSentenceTransformerEmbedder
from kb._lib.index_faiss import build_index as build_faiss_index
from kb._lib.index_faiss import is_available as faiss_available
from kb._lib.index_faiss import save_index as save_faiss_index
from kb._lib.index_hnsw import build_index as build_hnsw_index
from kb._lib.index_hnsw import is_available as hnsw_available
from kb._lib.index_hnsw import save_index as save_hnsw_index
from kb._lib.paths import index_dir, load_kb_config, requirements_dir
from kb._lib.types import ChunkRecord, IndexManifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local KB index for a domain.")
    parser.add_argument("--domain", required=True, help="Domain name, for example 'store_verify'.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    domain = args.domain.strip()
    cfg = load_kb_config(domain)
    docs_dir = requirements_dir(domain)
    if not docs_dir.exists():
        raise RuntimeError(
            f"Missing requirements directory: {docs_dir}. "
            f"Put .docx/.md/.txt business docs there before running build_kb."
        )

    source_docs = find_source_docs(docs_dir)
    if not source_docs:
        raise RuntimeError(
            f"No .docx/.md/.txt files found under {docs_dir}. Add business docs first."
        )

    blocks = []
    for path in source_docs:
        blocks.extend(extract_document_blocks(path))
    if not blocks:
        raise RuntimeError("No extractable text blocks were found in the source documents.")

    chunks = chunk_blocks(
        blocks,
        chunk_size_chars=cfg.chunk_size_chars,
        chunk_overlap_chars=cfg.chunk_overlap_chars,
    )
    if not chunks:
        raise RuntimeError("Chunking produced zero chunks. Check the source documents.")

    embedder = LocalSentenceTransformerEmbedder(
        model_name=cfg.embedding_model_name,
        embedding_local_path=cfg.embedding_local_path,
        local_files_only=cfg.local_files_only,
    )
    vectors = embedder.embed_texts([chunk.text for chunk in chunks])
    dimension = int(vectors.shape[1])

    backend = choose_backend(cfg.index_backend)
    out_dir = index_dir(domain)
    prepare_index_dir(out_dir)
    if backend == "faiss":
        index = build_faiss_index(vectors)
        save_faiss_index(index, out_dir / "faiss.index")
    else:
        index = build_hnsw_index(vectors)
        save_hnsw_index(index, out_dir / "hnsw.bin")

    write_meta(out_dir / "meta.jsonl", chunks)
    manifest = IndexManifest(
        domain=domain,
        backend=backend,
        embedding_model_name=cfg.embedding_model_name,
        embedding_local_path=cfg.embedding_local_path,
        dimension=dimension,
        chunk_count=len(chunks),
        doc_count=len(source_docs),
        created_at=datetime.now(timezone.utc).isoformat(),
        config_snapshot=cfg.to_dict(),
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest.__dict__, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "BUILD_REPORT.md").write_text(
        build_report(domain, source_docs, backend, cfg, chunks, manifest.created_at),
        encoding="utf-8",
    )
    print(f"KB index ready: {out_dir}")
    return 0


def find_source_docs(docs_dir: Path) -> list[Path]:
    docs = []
    for suffix in ("*.docx", "*.md", "*.txt"):
        docs.extend(docs_dir.glob(suffix))
    return sorted(path for path in docs if path.is_file())


def choose_backend(configured: str) -> str:
    backend = configured.lower()
    if backend == "faiss":
        if not faiss_available():
            raise RuntimeError(
                "config.index_backend=faiss but faiss-cpu is not installed locally."
            )
        return "faiss"
    if backend == "hnsw":
        if not hnsw_available():
            raise RuntimeError("config.index_backend=hnsw but hnswlib is not installed locally.")
        return "hnsw"
    if backend != "auto":
        raise RuntimeError("index_backend must be one of: auto, faiss, hnsw.")
    if faiss_available():
        return "faiss"
    if hnsw_available():
        return "hnsw"
    raise RuntimeError(
        "No vector backend is available. Install faiss-cpu or hnswlib locally."
    )


def prepare_index_dir(out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def write_meta(path: Path, chunks: list[ChunkRecord]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.__dict__, ensure_ascii=False) + "\n")


def build_report(
    domain: str,
    source_docs: list[Path],
    backend: str,
    cfg,
    chunks: list[ChunkRecord],
    created_at: str,
) -> str:
    lengths = [chunk.char_len for chunk in chunks]
    avg_len = sum(lengths) / len(lengths)
    report_lines = [
        f"# KB Build Report: {domain}",
        "",
        f"- Built at: {created_at}",
        f"- Backend: {backend}",
        f"- Embedding model: {cfg.embedding_local_path or cfg.embedding_model_name}",
        f"- Chunk size chars: {cfg.chunk_size_chars}",
        f"- Chunk overlap chars: {cfg.chunk_overlap_chars}",
        f"- Source doc count: {len(source_docs)}",
        f"- Chunk count: {len(chunks)}",
        f"- Avg chunk chars: {avg_len:.1f}",
        f"- Min chunk chars: {min(lengths)}",
        f"- Max chunk chars: {max(lengths)}",
        "",
        "## Source Files",
        "",
    ]
    report_lines.extend(f"- {path.name}" for path in source_docs)
    report_lines.append("")
    return "\n".join(report_lines)


if __name__ == "__main__":
    sys.exit(main())
