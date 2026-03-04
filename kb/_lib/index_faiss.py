from __future__ import annotations

from pathlib import Path


def is_available() -> bool:
    try:
        import faiss  # noqa: F401
    except ImportError:
        return False
    return True


def _module():
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError(
            "FAISS backend requested but faiss-cpu is not installed. Install it locally or switch to hnsw."
        ) from exc
    return faiss


def build_index(vectors):
    faiss = _module()
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors.astype("float32"))
    return index


def save_index(index, path: Path) -> None:
    faiss = _module()
    faiss.write_index(index, str(path))


def load_index(path: Path):
    faiss = _module()
    return faiss.read_index(str(path))


def search(index, query_vector, k: int):
    scores, ids = index.search(query_vector.astype("float32"), k)
    return scores[0].tolist(), ids[0].tolist()
