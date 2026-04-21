from __future__ import annotations

from pathlib import Path

from orchestrator.storage.domain.models import StorageConfig


def load_storage_config(repo_root: Path | None = None) -> StorageConfig:
    return StorageConfig.from_env(repo_root=repo_root)
