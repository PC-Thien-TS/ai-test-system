# Manual QA Phase 8A Draft Package Dashboard Report

## 1. Summary
Implemented a deterministic offline dashboard layer that unifies the existing API and Web Playwright draft package manifests into a single local summary. Phase 8A adds summary models, a draft package dashboard service, JSON/Markdown export support, a new CLI command, a small Streamlit report hook, and tests. The implementation reads metadata only from the Phase 7 package manifests and validation files. It does not execute scripts, send HTTP requests, launch browsers, or introduce fake execution status.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/draft_package_dashboard_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_draft_package_dashboard_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`
- `docs/reports/MANUAL_QA_PHASE8A_DRAFT_PACKAGE_DASHBOARD_REPORT.md`

## 3. Implemented Scope
- unified draft package summary model
- group summary model
- draft package dashboard service
- API package summary
- Web Playwright package summary
- JSON/Markdown export
- CLI command
- UI summary hook
- tests

## 4. Intentionally Deferred
- script execution
- sandbox execution
- API calls
- browser launch
- Playwright execution
- Appium execution
- production API/dashboard
- external AI calls

## 5. Dashboard Logic
- group status logic:
  Reads `script_drafts/api/api_script_package_manifest.json` and `script_drafts/web_playwright/web_playwright_package_manifest.json` when present. Missing manifests become `Missing`. Known manifest statuses are preserved as `Ready for Review`, `Needs Attention`, or `Invalid`. Unknown statuses are downgraded to `Needs Attention` with an explicit note.
- overall status logic:
  `Missing` when neither manifest exists.
  `Invalid` when any group is invalid.
  `Needs Attention` when any group needs attention or when one expected group is missing while another exists.
  `Ready for Review` only when all available groups are ready and no invalid/attention groups remain.
- count aggregation:
  Aggregates total drafts, valid, invalid, warnings, ready groups, needs attention groups, invalid groups, and missing groups across API and Web Playwright package summaries.
- missing manifest handling:
  Missing package manifests still produce a stable summary entry with expected manifest and validation paths, `missing=True`, and explanatory notes.
- recommended next step logic:
  `Ready for Review` -> `Review drafts manually before sandbox execution design`
  `Needs Attention` -> `Resolve warnings and TODOs before execution planning`
  `Invalid` -> `Fix invalid draft packages before continuing`
  `Missing` -> `Generate and validate API/Web draft packages first`

## 6. Reuse / Integration Notes
Phase 8A reuses the metadata-only package outputs created in:
- Phase 7C for API draft packaging:
  `script_drafts/api/api_script_package_manifest.json`
  `script_drafts/api/api_script_validation.json`
- Phase 7F for Web Playwright draft packaging:
  `script_drafts/web_playwright/web_playwright_package_manifest.json`
  `script_drafts/web_playwright/web_playwright_validation.json`

The new dashboard layer sits on top of those existing artifacts without changing the API or Web validation/package generation flows.

## 7. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8a
```

Result:
- `261 passed in 2.52s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase8a
```

Result:
- `289 passed in 3.38s`

## 8. Risks / Notes
- dashboard is local and metadata-only
- no scripts are executed
- no live validation is performed
- missing packages are handled as `Missing` or `Needs Attention` depending on overall context
- no fake PASS or execution status is introduced

## 9. Recommended Next Step
Phase 8B — Safe Script Execution Sandbox Design
