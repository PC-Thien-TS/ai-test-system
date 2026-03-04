from __future__ import annotations

from pathlib import Path


def is_available() -> bool:
    try:
        import hnswlib  # noqa: F401
    except ImportError:
        return False
    return True


def _module():
    try:
        import hnswlib
    except ImportError as exc:
        raise RuntimeError(
            "hnswlib backend requested but hnswlib is not installed. Install it locally or switch to faiss."
        ) from exc
    return hnswlib


def build_index(vectors):
    hnswlib = _module()
    index = hnswlib.Index(space="cosine", dim=vectors.shape[1])
    index.init_index(max_elements=len(vectors), ef_construction=200, M=16)
    index.add_items(vectors, list(range(len(vectors))))
    index.set_ef(max(50, min(200, len(vectors))))
    return index


def save_index(index, path: Path) -> None:
    index.save_index(str(path))


def load_index(path: Path, dimension: int):
    hnswlib = _module()
    index = hnswlib.Index(space="cosine", dim=dimension)
    index.load_index(str(path))
    index.set_ef(50)
    return index


def search(index, query_vector, k: int):
    ids, distances = index.knn_query(query_vector, k=k)
    scores = [1.0 - float(distance) for distance in distances[0].tolist()]
    return scores, ids[0].tolist()
