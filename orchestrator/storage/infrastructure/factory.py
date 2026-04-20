from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orchestrator.storage.application.services import ArtifactService, MemoryService, RunService
from orchestrator.storage.domain.models import ArtifactBackend, MemoryBackend, StorageConfig, StorageMode, VectorBackend
from orchestrator.storage.domain.repositories import ArtifactRepository, MemoryRepository, RunRepository, VectorMemoryRepository
from orchestrator.storage.infrastructure.config import load_storage_config
from orchestrator.storage.infrastructure.local import (
    LocalArtifactRepository,
    LocalMemoryRepository,
    LocalRunRepository,
    LocalVectorMemoryRepository,
)
from orchestrator.storage.infrastructure.server import (
    ServerArtifactRepositoryStub,
    ServerMemoryRepositoryStub,
    ServerRunRepositoryStub,
    UnavailableVectorMemoryRepository,
)


@dataclass(frozen=True)
class StorageProvider:
    config: StorageConfig
    run_repository: RunRepository
    artifact_repository: ArtifactRepository
    memory_repository: MemoryRepository
    vector_repository: VectorMemoryRepository
    run_service: RunService
    artifact_service: ArtifactService
    memory_service: MemoryService


def _build_local_provider(config: StorageConfig) -> StorageProvider:
    run_repo = LocalRunRepository(config.run_data_path)
    artifact_repo = LocalArtifactRepository(config.artifact_dir)
    if config.memory_backend == MemoryBackend.JSON:
        # JSON backend is intentionally deferred; sqlite is default deterministic local store.
        memory_repo = LocalMemoryRepository(config.memory_sqlite_path)
    elif config.memory_backend == MemoryBackend.SQLITE:
        memory_repo = LocalMemoryRepository(config.memory_sqlite_path)
    else:
        memory_repo = ServerMemoryRepositoryStub()

    if config.vector_backend in {VectorBackend.LOCAL_STUB, VectorBackend.FAISS_STUB}:
        vector_repo: VectorMemoryRepository = LocalVectorMemoryRepository(config.vector_index_path)
    else:
        vector_repo = UnavailableVectorMemoryRepository()

    return StorageProvider(
        config=config,
        run_repository=run_repo,
        artifact_repository=artifact_repo,
        memory_repository=memory_repo,
        vector_repository=vector_repo,
        run_service=RunService(run_repo),
        artifact_service=ArtifactService(artifact_repo),
        memory_service=MemoryService(memory_repo, vector_repo),
    )


def _build_server_provider(config: StorageConfig) -> StorageProvider:
    run_repo: RunRepository = ServerRunRepositoryStub()
    artifact_repo: ArtifactRepository = (
        LocalArtifactRepository(config.artifact_dir)
        if config.artifact_backend == ArtifactBackend.LOCAL_FS
        else ServerArtifactRepositoryStub()
    )
    memory_repo: MemoryRepository = ServerMemoryRepositoryStub()
    vector_repo: VectorMemoryRepository = UnavailableVectorMemoryRepository()
    return StorageProvider(
        config=config,
        run_repository=run_repo,
        artifact_repository=artifact_repo,
        memory_repository=memory_repo,
        vector_repository=vector_repo,
        run_service=RunService(run_repo),
        artifact_service=ArtifactService(artifact_repo),
        memory_service=MemoryService(memory_repo, vector_repo),
    )


def build_storage_provider(config: StorageConfig | None = None, repo_root: Path | None = None) -> StorageProvider:
    resolved = config or load_storage_config(repo_root=repo_root)
    if resolved.storage_mode == StorageMode.LOCAL:
        return _build_local_provider(resolved)
    return _build_server_provider(resolved)


def initialize_local_storage(config: StorageConfig | None = None, repo_root: Path | None = None) -> StorageProvider:
    resolved = config or load_storage_config(repo_root=repo_root)
    provider = build_storage_provider(resolved, repo_root=repo_root)
    # force initialization side-effects for deterministic bootstrap
    resolved.base_dir.mkdir(parents=True, exist_ok=True)
    resolved.artifact_dir.mkdir(parents=True, exist_ok=True)
    resolved.run_data_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.memory_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.vector_index_path.parent.mkdir(parents=True, exist_ok=True)
    return provider
