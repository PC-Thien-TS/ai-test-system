# Storage Architecture: Local-First, Central-Ready

## 1. Layering Model

This implementation introduces a storage boundary with three layers:

- `orchestrator/storage/domain`
  - pure models and repository contracts
  - no filesystem/database logic
- `orchestrator/storage/application`
  - service layer orchestration (`RunService`, `ArtifactService`, `MemoryService`)
  - deterministic business logic entrypoint for API/dashboard/agents
- `orchestrator/storage/infrastructure`
  - concrete backends (local filesystem/sqlite/vector stub)
  - server-ready stubs for PostgreSQL/object store/vector DB

The business logic now depends on repository interfaces, not direct JSON paths.

## 2. Local Mode vs Server Mode

Config-driven via environment:

- `STORAGE_MODE=local|server`
- `ARTIFACT_BACKEND=local_fs|s3_stub`
- `MEMORY_BACKEND=json|sqlite|postgres_stub`
- `VECTOR_BACKEND=local_stub|faiss_stub|qdrant_stub`

### Local mode
- Run metadata: local JSON (`.platform_storage/runs/run_records.json`)
- Artifacts: local filesystem (`.platform_storage/artifacts/...`)
- Failure memory: sqlite (`.platform_storage/memory/failure_memory.sqlite3`)
- Semantic memory: local vector stub (`.platform_storage/memory/vector_memory.json`)

### Server mode (current v1 behavior)
- returns server stubs for run/memory backends
- keeps architecture ready for PostgreSQL/object storage/vector DB
- no rewrite needed in application logic when real server adapters are implemented

## 3. File / Folder Structure

```text
orchestrator/storage/
  domain/
    models.py
    repositories.py
    errors.py
  application/
    services.py
  infrastructure/
    config.py
    factory.py
    local/
      run_repository.py
      artifact_repository.py
      memory_repository.py
      vector_memory_repository.py
    server/
      stubs.py
scripts/
  init_storage.py
api/routes/
  storage.py
```

## 4. API Integration Pattern

FastAPI dependencies now expose service-layer access:

- `api/deps.py`
  - `get_storage_provider()`
  - `get_storage_run_service()`
  - `get_storage_artifact_service()`
  - `get_storage_memory_service()`

New route module:

- `api/routes/storage.py`
  - run CRUD/status/release decision reference
  - artifact store/list
  - exact and semantic memory lookup

This enforces API/service access over direct file reads.

## 5. Migration Notes

### Current state
- intelligence components write local artifacts and adapter-isolated evidence
- historical behavior often reads JSON files directly

### Migration path (non-breaking)
1. keep existing artifact writes running (no destructive rewrite)
2. add repository writes in parallel through storage services
3. switch API/dashboard read paths to storage service APIs
4. deprecate direct JSON reads after parity validation
5. in server rollout, replace infrastructure stubs with:
   - PostgreSQL repositories (`RunRepository`, `MemoryRepository`)
   - object-storage artifact repository (`ArtifactRepository`)
   - vector DB repository (`VectorMemoryRepository`)

### Key compatibility point
- application services and route handlers remain unchanged when backend swaps.

## 6. Bootstrap Utility

Initialize storage layout:

```powershell
python scripts/init_storage.py
python scripts/init_storage.py --storage-mode local --memory-backend sqlite --vector-backend local_stub
```

## 7. Example Usage Flow

1. create provider
2. create run
3. store artifact
4. upsert failure memory
5. exact signature lookup
6. semantic lookup

```python
from orchestrator.storage.infrastructure.factory import build_storage_provider
from orchestrator.storage.domain.models import FailureSignature

provider = build_storage_provider()

run = provider.run_service.create_run(adapter_id="rankmate", project_id="order_core")
provider.artifact_service.store_text(
    run_id=run.run_id,
    adapter_id=run.adapter_id,
    artifact_name="run.log",
    text="sample log",
)

sig = FailureSignature(
    fingerprint="ORD-API-014",
    error_type="HTTP_500",
    component="order_api",
    endpoint="/api/v1/orders/{id}/retry-payment",
)

memory = provider.memory_service.remember_failure(
    adapter_id="rankmate",
    project_id="order_core",
    signature=sig,
    root_cause="Unhandled invalid state transition",
    severity="P1",
    confidence=0.9,
    recommended_actions=["Add state guard before retry-payment"],
)

exact = provider.memory_service.exact_lookup(adapter_id="rankmate", signature=sig)
similar = provider.memory_service.similar_lookup(
    adapter_id="rankmate",
    query_text="retry payment invalid state guard",
    top_k=3,
)
```
