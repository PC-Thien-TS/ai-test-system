# Manual QA Phase 7F Web Playwright Validation Report

## 1. Summary
Implemented static validation and metadata-only packaging for Web Playwright draft artifacts generated in Phase 7E. This phase adds validation issue/result models, a deterministic static validation service, a package manifest model, a packaging service, export support, a CLI command, and a small local UI/report hook for reviewing Web Playwright validation outputs. The implementation stays offline and does not execute Playwright, launch browsers, install browsers, or validate live pages.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/web_playwright_validation_service.py`
- `orchestrator/manual_qa/web_playwright_packaging_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_web_playwright_validation_service.py`
- `tests/manual_qa/test_web_playwright_packaging_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`

## 3. Implemented Scope
- validation issue/result models
- static validation service
- package manifest model
- package builder service
- validation/package export support
- CLI command
- optional UI/report hook
- tests

## 4. Intentionally Deferred
- Playwright execution
- browser launch
- browser installation
- live page validation
- Appium generation
- API generation
- API route changes
- production dashboard
- external AI calls

## 5. Validation Logic
- Syntax check:
  Uses `ast.parse` on generated draft content only.
- Draft-only marker check:
  Requires explicit draft wording such as `Draft only`.
- No-execution marker check:
  Requires explicit `Not executed` or equivalent wording.
- Playwright import check:
  Requires a safe Playwright sync API import pattern such as `from playwright.sync_api import Page, expect`.
- Test function check:
  Requires a pytest-style `def test_*` function.
- `page.goto` / TODO page check:
  Detects missing navigation and separately flags TODO page URL placeholders as warnings.
- Locator/action/assertion / TODO check:
  Detects locator presence, supported action calls, assertion presence, and TODO selector/assertion placeholders.
- Valid/invalid rules:
  Validation is invalid for syntax errors, missing draft marker, missing no-execution marker, missing Playwright import, or missing test function. TODO placeholders remain warnings unless structural validity is already broken.

## 6. Packaging Logic
- Draft count:
  Counts all provided Web Playwright draft artifacts.
- Valid/invalid/warning counts:
  Derives counts from validation results and issue severities.
- Package status:
  `Ready for Review` when all drafts are syntax-valid and have no error issues.
  `Needs Attention` when warnings exist but no error issues exist.
  `Invalid` when any error issues or syntax failures exist.
- No zip/no execution/no browser launch:
  Packaging is metadata only. No archives are built and no drafts are executed.

## 7. Reuse / Integration Notes
Phase 7F builds directly on Phase 7E by consuming `WebPlaywrightScriptDraft` artifacts from `script_drafts/web_playwright/`. It follows the same architectural pattern used in the API validation and packaging phases, reusing existing exporter conventions, workspace artifact structure, CLI style, and Streamlit report preview flow.

## 8. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase7f
```

Result:
- `240 passed`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase7f
```

Result:
- `268 passed`

## 9. Risks / Notes
- Validation is static only.
- Scripts are not executed.
- There is no browser validation.
- Package manifest is metadata only.
- No fake PASS or execution status is produced.

## 10. Recommended Next Step
Phase 8A — Safe Script Execution Sandbox Design  
or  
Phase 8A — Unified Draft Package Dashboard
