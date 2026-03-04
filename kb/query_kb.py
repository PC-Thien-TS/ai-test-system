from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kb._lib.embedder import LocalSentenceTransformerEmbedder
from kb._lib.index_faiss import load_index as load_faiss_index
from kb._lib.index_hnsw import load_index as load_hnsw_index
from kb._lib.index_faiss import search as search_faiss
from kb._lib.index_hnsw import search as search_hnsw
from kb._lib.paths import index_dir, load_kb_config
from kb._lib.types import SearchHit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a local KB index.")
    parser.add_argument("--domain", required=True, help="Domain name.")
    parser.add_argument("--q", required=True, help="Search query.")
    parser.add_argument("--k", type=int, default=5, help="Number of hits to return.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hits = search_domain(args.domain, args.q, args.k)
    if args.as_json:
        print(
            json.dumps(
                [
                    {
                        "chunk_id": hit.chunk_id,
                        "score": hit.score,
                        "source_file": hit.source_file,
                        "text": hit.text,
                        "headings": hit.headings,
                    }
                    for hit in hits
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(format_hits(hits))
    return 0


def search_domain(domain: str, query: str, k: int) -> list[SearchHit]:
    cfg = load_kb_config(domain)
    manifest, meta = load_index_bundle(domain)
    embedder = LocalSentenceTransformerEmbedder(
        model_name=cfg.embedding_model_name,
        embedding_local_path=cfg.embedding_local_path,
        local_files_only=cfg.local_files_only,
    )
    query_vector = embedder.embed_texts([query])
    if manifest["backend"] == "faiss":
        index = load_faiss_index(index_dir(domain) / "faiss.index")
        scores, ids = search_faiss(index, query_vector, k)
    else:
        index = load_hnsw_index(index_dir(domain) / "hnsw.bin", int(manifest["dimension"]))
        scores, ids = search_hnsw(index, query_vector, k)

    hits: list[SearchHit] = []
    for score, idx in zip(scores, ids):
        if idx < 0 or idx >= len(meta):
            continue
        record = meta[idx]
        hits.append(
            SearchHit(
                chunk_id=str(record["chunk_id"]),
                score=float(score),
                source_file=str(record["source_file"]),
                text=str(record["text"]),
                headings=[str(item) for item in record.get("headings", [])],
            )
        )
    return hits


def load_index_bundle(domain: str) -> tuple[dict, list[dict]]:
    out_dir = index_dir(domain)
    manifest_path = out_dir / "manifest.json"
    meta_path = out_dir / "meta.jsonl"
    if not manifest_path.exists() or not meta_path.exists():
        raise RuntimeError(
            f"KB index is missing for domain '{domain}'. Run 'python kb/build_kb.py --domain {domain}' first."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    meta = [
        json.loads(line)
        for line in meta_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return manifest, meta


def format_hits(hits: list[SearchHit]) -> str:
    if not hits:
        return "No results found."
    blocks = []
    for index, hit in enumerate(hits, start=1):
        headings = " > ".join(hit.headings) if hit.headings else "(no headings)"
        blocks.extend(
            [
                f"[{index}] score={hit.score:.4f} source={hit.source_file} chunk={hit.chunk_id}",
                f"headings: {headings}",
                "---",
                hit.text,
                "",
            ]
        )
    return "\n".join(blocks).rstrip()


if __name__ == "__main__":
    sys.exit(main())
