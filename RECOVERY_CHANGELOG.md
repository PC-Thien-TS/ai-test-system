# Recovery Changelog - Testable Baseline v1

Date: 2026-04-14  
Branch: `recovery/testable-baseline-v1`

This changelog records recovery edits grouped as logical commit units.

## 1) `chore: align python dependencies with actual imports`

Files:

- `requirements.txt`

Changes:

- Added/normalized runtime dependencies used by plugins/scripts:
  - `requests`
  - `jsonschema`
  - `PyYAML`
  - `numpy`
  - `scikit-learn`
- Added `pytest-asyncio` to test dependencies for async test execution.

Why:

- test collection and plugin imports required these packages.

## 2) `fix: correct sklearn calibration import`

Files:

- `orchestrator/plugins/model_evaluation.py`

Changes:

- Corrected import for `calibration_curve` to `sklearn.calibration`.

Why:

- previous import path caused collection/runtime import errors.

## 3) `fix: align API run routes with mounted router contract`

Files:

- `api/app.py`

Changes:

- Kept project-scoped mount under `/projects`.
- Added compatibility mount under `/runs` for run-centric clients/tests.

Why:

- existing tests and clients used both path families.

## 4) `fix: unify execution-path handling and escalation chain behavior`

Files:

- `orchestrator/execution_intelligence.py`
- `orchestrator/run_orchestrator.py`
- `orchestrator/run_registry.py`
- `orchestrator/escalation_prediction.py`

Changes:

- standardized path-selection semantics for smoke/deep/health/depth scenarios,
- default escalation policy depth now respected via `RunOrchestrationConfig`,
- improved chain traversal resolution (`parent_run_id` + `original_run_id`, chain lookup by `run_id`),
- converted engine enum outputs to API/model enum for consistent typing,
- deterministic latest-run behavior on timestamp ties,
- tuned predicted-path threshold for escalation prediction consistency.

Why:

- previous behavior produced inconsistent escalation outcomes and enum mismatch failures.

## 5) `fix: plugin framework sync/async execution compatibility`

Files:

- `orchestrator/plugins/base.py`
- `orchestrator/plugins/executor.py`
- `orchestrator/plugins/integration.py`
- `orchestrator/plugins/api_contract.py`
- `orchestrator/plugins/model_evaluation.py`
- `orchestrator/plugins/rag_grounding.py`
- `orchestrator/plugins/playwright.py`
- `orchestrator/compatibility.py`
- `tests/test_plugin_framework.py`

Changes:

- made plugin `validate_config` contract sync-compatible across built-in plugins,
- added async + sync execution entry points in plugin executor/integration,
- preserved async orchestration paths while supporting sync test scenarios,
- corrected API contract schema metrics accounting (pass/fail assertions),
- added compatibility aliases expected by existing tests,
- adjusted compatibility metadata values to match tested contract,
- fixed retry test setup to target registered plugin instance.

Why:

- tests assumed sync paths while implementation drifted toward async-only behavior.

## 6) `fix: v27 API escalation test storage isolation`

Files:

- `tests/test_v27_escalation.py`

Changes:

- set `api.deps.REPO_ROOT` to temporary test directory before app creation in API tests.

Why:

- ensured temporary registry state is isolated and deterministic during escalation endpoint tests.

## 7) `chore: bootstrap local scripts with safe defaults and actionable errors`

Files:

- `scripts/run_logic_tests.ps1`
- `scripts/run_api_smoke.ps1`
- `scripts/run_ui_smoke.ps1`

Changes:

- robust backend/frontend path resolution for sibling repo layouts,
- support for `.env` loading from repo root,
- explicit actionable error messages for missing env vars,
- windows-safe invocation using `npm.cmd`/`npx.cmd`.

Why:

- scripts were failing early with opaque setup errors.

## 8) `security: sanitize env example values`

Files:

- `.env.example`

Changes:

- replaced realistic/unsafe-looking credentials with placeholders,
- retained minimal safe local defaults (`localhost` URLs),
- added `BASE_URL` example for UI smoke script.

Why:

- reduce accidental credential misuse and improve onboarding clarity.

## 9) Recovery Documentation

Files:

- `RECOVERY_AUDIT.md`
- `RECOVERY_CHANGELOG.md`
- `KNOWN_ISSUES.md`

Changes:

- documented audit findings, verification evidence, remaining blockers, and next safe build direction.
