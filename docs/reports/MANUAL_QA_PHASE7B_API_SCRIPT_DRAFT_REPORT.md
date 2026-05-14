# Manual QA Phase 7B API Script Draft Report

## 1. Summary
Implemented deterministic API test script draft generation for Manual QA. This phase adds an API draft model, a rule-based pytest plus requests draft generator, JSON and Markdown export support, Python draft file export, a CLI command for workspace draft generation, and a small local UI report hook. Generated artifacts are explicitly marked as drafts only and are never executed.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/api_script_generator.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_api_script_generator.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`
- `docs/reports/MANUAL_QA_PHASE7B_API_SCRIPT_DRAFT_REPORT.md`

## 3. Implemented Scope
- API script draft model
- API script generator service
- pytest + requests draft rendering
- draft export support
- CLI command
- optional UI/report hook
- tests

## 4. Intentionally Deferred
- script execution
- Playwright generation
- Appium generation
- web/mobile automation
- API route changes
- production dashboard
- external AI calls

## 5. Generation Logic
The API draft generator is deterministic and rule-based:
- HTTP method is detected from explicit method names and common action hints such as create, update, delete, fetch, and search.
- Endpoint detection looks for endpoint-like paths or full URLs and normalizes them to a request path.
- Expected status code detection prioritizes explicit codes in expected results and steps.
- Missing method, endpoint, status code, or payload details fall back to safe defaults and add warnings:
  - method defaults to `GET`
  - endpoint defaults to `/TODO_ENDPOINT`
  - status code defaults to `200`
  - payload placeholders are inserted for write operations when input data is missing
- Draft-only safeguards are built into every script:
  - script content is marked as `Manual QA API script draft`
  - the source `test_case_id` and requirement IDs are embedded
  - the docstring states `Draft only. Not executed / not verified.`
  - generation never executes `requests` calls or validates live endpoints

## 6. Reuse / Integration Notes
Phase 7B builds on existing Manual QA artifacts instead of introducing a separate automation stack:
- `ManualTestCase` remains the primary source artifact.
- `ScriptGenerationReadiness` is reused to gate generation for API-ready and API-like cases.
- Existing exporter infrastructure is extended for draft JSON, Markdown, and Python file output.
- The CLI remains a thin adapter that reads `testcases/testcases.json`, optionally consumes `reports/script_readiness.json`, and writes draft artifacts under `script_drafts/api/`.
- The Streamlit UI only adds a small local hook to generate and preview draft artifacts without taking over generation logic.

## 7. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase7b
```

Result:
- `154 passed in 1.34s`

Command run:

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase7b
```

Result:
- `182 passed in 1.97s`

## 8. Risks / Notes
- Generated scripts are drafts only.
- Drafts were not executed.
- Endpoint, payload, and auth details may still require manual completion.
- No live API validation is performed.
- No generated artifact is marked as passed.

## 9. Recommended Next Step
Phase 7C - API Script Draft Validation and Packaging
or
Phase 7C - Web Playwright Script Draft Readiness Review.
