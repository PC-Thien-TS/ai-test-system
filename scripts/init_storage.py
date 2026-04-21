from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.storage.infrastructure.factory import initialize_local_storage


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize local-first storage layout")
    parser.add_argument("--storage-mode", choices=["local", "server"], default=None)
    parser.add_argument("--artifact-backend", choices=["local_fs", "s3_stub"], default=None)
    parser.add_argument("--memory-backend", choices=["json", "sqlite", "postgres_stub"], default=None)
    parser.add_argument("--vector-backend", choices=["local_stub", "faiss_stub", "qdrant_stub"], default=None)
    parser.add_argument("--base-dir", default=None, help="Override STORAGE_BASE_DIR")
    parser.add_argument("--adapter", default=None, help="Override AI_TESTING_ADAPTER")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.storage_mode:
        os.environ["STORAGE_MODE"] = args.storage_mode
    if args.artifact_backend:
        os.environ["ARTIFACT_BACKEND"] = args.artifact_backend
    if args.memory_backend:
        os.environ["MEMORY_BACKEND"] = args.memory_backend
    if args.vector_backend:
        os.environ["VECTOR_BACKEND"] = args.vector_backend
    if args.base_dir:
        os.environ["STORAGE_BASE_DIR"] = args.base_dir
    if args.adapter:
        os.environ["AI_TESTING_ADAPTER"] = args.adapter

    provider = initialize_local_storage(repo_root=REPO_ROOT)
    config = provider.config
    payload = {
        "storage_mode": config.storage_mode.value,
        "artifact_backend": config.artifact_backend.value,
        "memory_backend": config.memory_backend.value,
        "vector_backend": config.vector_backend.value,
        "adapter_id": config.adapter_id,
        "base_dir": str(config.base_dir),
        "artifact_dir": str(config.artifact_dir),
        "run_data_path": str(config.run_data_path),
        "memory_sqlite_path": str(config.memory_sqlite_path),
        "vector_index_path": str(config.vector_index_path),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print("[storage-init] initialized local-first persistence")
    for key, value in payload.items():
        print(f"[storage-init] {key}={value}")


if __name__ == "__main__":
    main()
