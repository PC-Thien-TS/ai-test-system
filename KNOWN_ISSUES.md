# Known Issues - Post Recovery Baseline

Date: 2026-04-14  
Branch: `recovery/testable-baseline-v1`

## 1. Environment/Sandbox Constraints

### A) `.NET` toolchain permission issue in this execution environment

Impact:

- `scripts/run_logic_tests.ps1 -UnitOnly` can reach backend test bootstrap but fails during `dotnet restore` first-time setup with `UnauthorizedAccessException` under sandboxed user profile.

Status:

- **Not a repository code defect**.
- requires local machine permissions for `.NET` profile/tool path initialization.

Recommended local action:

1. run the script in a normal developer shell (non-sandbox),
2. ensure `dotnet --info` and `dotnet restore` work for `rankmate_be`,
3. rerun `scripts/run_logic_tests.ps1 -UnitOnly`.

### B) npm registry/network permission issue in this execution environment

Impact:

- dashboard dependency install (`npm install`) and ping to npm registry fail with `EACCES` in this sandbox.
- without install, `npm run lint` fails (`next` not found).

Status:

- **Not a confirmed dashboard code defect** in this run.
- frontend build/lint validation remains pending in unrestricted environment.

Recommended local action:

1. run `cd dashboard && npm install`,
2. run `npm run lint`,
3. run `npm run build`.

## 2. Warnings and Technical Debt (Non-blocking for baseline)

### A) UTC deprecation warnings

Impact:

- tests pass but emit many warnings due to `datetime.utcnow()` usage.

Status:

- non-blocking now, but should be migrated to timezone-aware UTC usage.

Recommended action:

1. replace `datetime.utcnow()` with `datetime.now(datetime.UTC)` gradually,
2. add focused tests for serialization compatibility during migration.

### B) Optional `evidence_sources.yaml` bootstrap

Impact:

- evidence collection scripts are tolerant, but source-backed evidence is skipped if file is missing.

Status:

- behavior is now graceful and explicit.

Recommended action:

1. provide a minimal tracked template if team wants deterministic source-backed evidence by default.

## 3. Operational Assumptions

The recovered baseline assumes:

- Python dependencies from `requirements.txt` are installed,
- smoke scripts use `.env` values (or exported environment variables),
- sibling repo layout exists for integrated backend/frontend logic script paths when those scripts are used.
