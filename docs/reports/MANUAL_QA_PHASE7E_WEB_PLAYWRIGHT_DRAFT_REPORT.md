# Manual QA Phase 7E Web Playwright Draft Report

## 1. Summary
Implemented deterministic Web Playwright script draft generation for Manual QA. This phase adds a new draft model, a Playwright Python draft generator for eligible web UI cases, JSON/Markdown/Python export support, a CLI command to generate local draft artifacts, and a small read-only Streamlit/UI helper hook for previewing the generated files. The phase remains offline and draft-only: no Playwright execution, no browser launch, no browser installation, and no external AI calls were introduced.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/web_playwright_script_generator.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `orchestrator/manual_qa/web_playwright_readiness_service.py`
- `tests/manual_qa/test_web_playwright_script_generator.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`

## 3. Implemented Scope
- Web Playwright script draft model
- Web Playwright script generator service
- Playwright Python draft rendering
- draft export support
- CLI command
- optional UI/report hook
- tests

## 4. Intentionally Deferred
- Playwright execution
- browser installation
- browser automation
- Appium generation
- API generation changes
- API route changes
- production dashboard
- external AI calls

## 5. Generation Logic
- Page URL detection:
  Uses `WebPlaywrightReadiness.page_url` first, then deterministic route/URL detection from test text. Missing values fall back to `/TODO_PAGE_URL` with warnings.
- Selector/action/assertion rendering:
  Reuses readiness hints when present, then deterministic parsing from manual steps and expected results. Known selector formats map to `get_by_test_id`, `get_by_role`, `get_by_label`, or `locator`.
- TODO warnings:
  Missing page URL, selectors, actions, or assertions produce explicit warnings and draft placeholders instead of failing silently.
- Draft-only safeguards:
  Generated scripts include draft-only and not-executed markers in docstrings and inline comments.
- No execution guarantees:
  The generator only renders text artifacts. It does not run Playwright, launch browsers, install browsers, or validate live pages.

## 6. Reuse / Integration Notes
Phase 7E builds on Phase 7D by consuming `WebPlaywrightReadiness` outputs and on earlier phases by reusing `ManualTestCase`, workspace helpers, local JSON/Markdown artifact patterns, CLI conventions, and the existing Streamlit reports workflow. A small readiness-service hardening change was included so clearly web UI-like cases are not rejected solely because upstream generic script-readiness heuristics mislabeled them.

## 7. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase7e
```

Result:
- `214 passed`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase7e
```

Result:
- `242 passed`

## 8. Risks / Notes
- Generated scripts are drafts only.
- Drafts were not executed.
- Selectors, credentials, and assertions may require manual refinement.
- There is no live browser validation.
- No fake PASS or execution status is produced.

## 9. Recommended Next Step
Phase 7F — Web Playwright Draft Static Validation and Packaging  
or  
Phase 8 — Safe Script Execution Sandbox Design
