# Recovery Audit - Testable Baseline v1

Date: 2026-04-14  
Branch: `recovery/testable-baseline-v1`  
Repository: `C:\Projects\Rankmate\ai_test_system`

## 1. Scope

This audit treated the current local repository state as the only source of truth and executed a full recovery workflow:

1. inventory + architecture audit,
2. runtime reproduction of failures,
3. minimal recovery fixes,
4. rerun verification to confirm baseline.

## 2. Repository Inventory

Top-level modules inspected:

- backend/API: `api/` (10 files)
- orchestration + plugins + analytics: `orchestrator/` (23 files)
- test suite: `tests/` (27 files, 261 tests collected)
- scripts/automation: `scripts/` (27 files)
- dashboard frontend: `dashboard/` (32 files)
- domain + KB assets: `domains/`, `kb/`, `requirements/`, `schemas/`, `outputs/`

Key architecture direction confirmed present:

- orchestrator core + run/project registries,
- plugin model (playwright/api_contract/model_eval/rag),
- escalation intelligence and policies,
- dashboard (Next.js),
- advanced QA modules (`evidence_analysis`, `escalation_prediction`, `policy_templates`, `escalation_analytics`).

## 3. Verified Failures (Reproduced)

### A. Historical baseline before fixes (same recovery branch)

- `pytest --collect-only` initially failed with import/dependency blockers:
  - missing runtime deps (`jsonschema`, related import chain),
  - incorrect sklearn import location for `calibration_curve`.
- full tests previously had multiple failures around:
  - route contract mismatch (`/projects/...` vs `/runs/...`),
  - escalation chain/depth behavior,
  - enum mismatch between orchestration model and intelligence engine,
  - plugin framework sync/async execution mismatch.

### B. Script/bootstrap failures reproduced in current environment

- `scripts/run_logic_tests.ps1 -UnitOnly`
  - no longer crashes on empty path,
  - currently blocked by environment permissions during `.NET` first-time setup (`UnauthorizedAccessException` under sandboxed profile).
- `scripts/run_api_smoke.ps1`
  - exits fast with explicit missing env message (`API_BASE_URL`) and actionable `.env` guidance.
- `scripts/run_ui_smoke.ps1`
  - exits fast with explicit missing env message (`BASE_URL`) and actionable `.env` guidance.

### C. Dashboard bootstrap in this environment

- `npm run lint` in `dashboard/` fails because `next` is unavailable before dependency install.
- `npm install`/`npm ping` are blocked in this sandbox by system/network permission (`EACCES`), so frontend install/build cannot be fully executed here.

## 4. Recovery Changes Applied

Recovery edits were intentionally minimal and aligned to existing architecture:

1. dependency alignment (`requirements.txt`) for actual imports;
2. sklearn import correction in model evaluation plugin;
3. API compatibility mount so both `/projects/...` and `/runs/...` contracts work;
4. escalation and enum consistency fixes in orchestration + intelligence;
5. latest-run tie-break determinism in registry;
6. script bootstrap hardening (`run_logic_tests.ps1`, `run_api_smoke.ps1`, `run_ui_smoke.ps1`);
7. `.env.example` sanitization to placeholders/safe defaults;
8. plugin framework compatibility fixes (sync/async execution + config validation expectations).

See `RECOVERY_CHANGELOG.md` for file-level details.

## 5. Verification Runs (Post-Fix)

Executed commands and outcomes:

1. `python -m pytest --collect-only -q -p no:cacheprovider tests`  
   Outcome: `261 tests collected` (collection succeeds).
2. `python -m pytest -q -p no:cacheprovider tests`  
   Outcome: `261 passed, 364 warnings`.
3. API route contract check via app route introspection  
   Outcome: both `/projects/...` and `/runs/...` run endpoints present.
4. `powershell -File scripts/run_api_smoke.ps1`  
   Outcome: graceful env validation failure with actionable message.
5. `powershell -File scripts/run_ui_smoke.ps1`  
   Outcome: graceful env validation failure with actionable message.
6. `powershell -File scripts/run_logic_tests.ps1 -UnitOnly`  
   Outcome: progressed past path bootstrap, then blocked by sandbox `.NET` permission issue.
7. `npm run lint` (dashboard)  
   Outcome: expected failure before dependency install (`next` not found).

## 6. Recovery Baseline Decision

Baseline status: **RECOVERED / TESTABLE (backend + tests)**.

Reason:

- test collection works,
- full Python suite passes (261/261),
- known blocking defects were resolved in-code,
- scripts now fail with actionable setup diagnostics instead of opaque bootstrap crashes.

Residual limitations are environment-related (sandbox permissions/network for `.NET`/npm) and documented in `KNOWN_ISSUES.md`.

## 7. Stable Modules to Build On

Modules with strongest verification signal:

- `api/` + route layer (including run endpoint compatibility),
- `orchestrator/run_orchestrator.py`, `execution_intelligence.py`, `run_registry.py`,
- plugin framework + built-in plugins (`api_contract`, `model_evaluation`, `rag_grounding`, `playwright`),
- v2.7/v2.8/v2.9/v3.0 feature tracks covered by existing tests.

## 8. Next Safe Build Step

Recommended continuation from this recovered baseline: **Requirement-aware generation**.

Rationale:

- it builds directly on already-stable orchestrator + plugin pipeline,
- it does not require frontend package installation to start delivering backend value,
- it can be introduced incrementally with targeted tests and minimal contract risk.
