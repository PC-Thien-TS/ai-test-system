# Manual QA Phase 8B Safe Execution Sandbox Design Report

## 1. Summary
Implemented a deterministic, offline safety policy and execution preflight layer for Manual QA draft packages. Phase 8B adds safety policy models, execution target and preflight models, a static safety policy service, a static preflight planning service, JSON/Markdown export support, an `execution-preflight` CLI command, a small Streamlit/UI helper hook, and tests. The implementation is design-only and does not execute scripts, import generated drafts, send HTTP requests, launch browsers, or create real execution outcomes.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/execution_safety_service.py`
- `orchestrator/manual_qa/execution_preflight_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_execution_safety_service.py`
- `tests/manual_qa/test_execution_preflight_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`
- `docs/reports/MANUAL_QA_PHASE8B_SAFE_EXECUTION_SANDBOX_DESIGN_REPORT.md`

## 3. Implemented Scope
- safety policy models
- execution target model
- preflight issue/result models
- execution plan model
- safety policy service
- preflight service
- JSON/Markdown export support
- CLI command
- UI hook
- tests

## 4. Intentionally Deferred
- actual script execution
- API execution
- Playwright execution
- browser launch
- live HTTP calls
- real Pass/Fail result creation
- production API/dashboard
- external AI calls

## 5. Safety Policy Logic
- allowlist/blocklist:
  Localhost defaults are allowlisted via `http://localhost` and `http://127.0.0.1`. Production-style keywords such as `production`, `prod`, `live`, `payment-live`, and `real-bank` are blocked.
- dry-run only default:
  The default and strict policies both disable execution and remain `dry_run_only=True`.
- human approval requirement:
  Policies require human approval before any future execution phase could be considered.
- write/delete method blocking:
  `POST`, `PUT`, and `PATCH` are treated as write methods and are blocked by default. `DELETE` is blocked more aggressively and classified as critical when disallowed.
- production/live/payment blocking:
  Non-local or blocked-keyword URLs are surfaced before execution planning. Production/live/payment-like URLs are classified as critical.
- package validity requirements:
  Policies require valid package metadata and no critical TODO placeholders before a target could ever move beyond static planning.

## 6. Preflight Logic
- target discovery:
  Reads `api_script_package_manifest.json`, `api_script_validation.json`, `api_script_drafts.json`, `web_playwright_package_manifest.json`, `web_playwright_validation.json`, and `web_playwright_script_drafts.json` when present.
- risk classification:
  Computes `Low`, `Medium`, `High`, or `Critical` risk from script type, base URL, package/validation status, TODO markers, HTTP method, and policy requirements.
- decision rules:
  Produces target-level decisions of `Allowed`, `Blocked`, `Needs Human Approval`, or `Dry Run Only`, and plan-level decisions of `Ready for Sandbox Design Review`, `Needs Attention`, `Blocked`, or `Missing Draft Packages`.
- issue detection:
  Detects missing packages, invalid package/validation state, blocked or non-local URLs, write/delete method restrictions, critical TODO placeholders, missing human approval, disallowed script types, execution-disabled policy state, and dry-run-only policy state.
- no execution guarantees:
  Preflight works from JSON metadata and embedded `script_content` only. It does not import generated scripts, read generated `.py` files from disk, run pytest, send network traffic, or launch browsers.

## 7. Reuse / Integration Notes
Phase 8B builds directly on the existing draft package outputs from previous phases:
- API draft package manifests and validation metadata from Phase 7C
- Web Playwright draft package manifests and validation metadata from Phase 7F
- Unified draft package/report flow from Phase 8A

The new preflight layer reuses those artifacts as static inputs and adds safety/risk analysis on top without changing any earlier generation or validation behavior.

## 8. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8b
```

Result:
- `284 passed in 2.62s`

Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q `
  tests/test_requirement_generator.py `
  tests/test_storage_persistence_layer.py `
  tests/test_bug_report_generator.py `
  tests/test_candidate_generation_system.py `
  tests/manual_qa `
  --maxfail=10 `
  --basetemp=artifacts/pytest_tmp/safe_subset_phase8b
```

Result:
- `312 passed in 3.35s`

## 9. Risks / Notes
- this is design/preflight only
- no script execution yet
- no live validation
- policies are conservative by default
- no fake PASS

## 10. Recommended Next Step
Phase 8C — API Execution Sandbox Prototype with strict safety gates.
