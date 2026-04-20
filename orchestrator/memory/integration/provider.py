from __future__ import annotations

from pathlib import Path
from typing import Optional

from orchestrator.memory.application.engine import FailureMemoryEngine
from orchestrator.memory.domain.models import MemoryEngineConfig
from orchestrator.storage.infrastructure.factory import StorageProvider, build_storage_provider


def build_failure_memory_engine(
    *,
    storage_provider: Optional[StorageProvider] = None,
    config: Optional[MemoryEngineConfig] = None,
    repo_root: Optional[Path] = None,
) -> FailureMemoryEngine:
    provider = storage_provider or build_storage_provider(repo_root=repo_root)
    return FailureMemoryEngine(
        memory_repository=provider.memory_repository,
        vector_repository=provider.vector_repository,
        config=config or MemoryEngineConfig.from_env(),
    )
