# Manual QA Phase 7A Script Readiness Report

## 1. Summary
Implemented a deterministic script draft readiness review layer for Manual QA. This phase adds readiness and gap models, a rule-based analyzer service, JSON and Markdown export support, a CLI report command, and a small optional UI report hook. It evaluates whether existing manual test cases are ready for future script drafting without generating or executing any scripts.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/script_readiness_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_script_readiness_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`
- `docs/reports/MANUAL_QA_PHASE7A_SCRIPT_READINESS_REPORT.md`

## 3. Implemented Scope
- readiness models
- readiness analyzer service
- gap detection
- target type classification
- readiness export
- CLI command
- tests

## 4. Intentionally Deferred
- actual script generation
- Playwright generator
- Appium generator
- API test generator
- automation execution
- API routes
- production dashboard
- external AI calls

## 5. Readiness Logic
The readiness analyzer is deterministic and rule-based:
- Target type is classified as `api`, `web_ui`, `mobile`, `integration`, `unit`, `manual_only`, or `unknown` from module, title, steps, and expected result hints.
- Readiness starts from a baseline score of `50`.
- Positive signals add score for clear steps, explicit expected results, requirement traceability, `Should Automate` automation recommendations, known target type, and detectable test data.
- Negative signals subtract score for missing steps, missing expected result, vague expected result, manual judgment, external dependency, environment dependency, missing endpoint hints for API cases, and missing selector hints for Web UI cases.
- Readiness status is:
  - `Ready` when score is at least `75` and there are no high-severity gaps
  - `Needs More Data` when score is between `40` and `74`
  - `Not Suitable` when score is below `40` or a critical manual-only gap is present
- Suggested next steps remain advisory only:
  - `Proceed to script draft generation`
  - `Add missing test data/selectors/endpoints/assertions before generation`
  - `Keep as manual test or redesign test for automation`

## 6. Reuse / Integration Notes
Phase 7A builds on existing Manual QA artifacts rather than replacing them:
- `ManualTestCase` remains the primary analysis input.
- `AutomationCandidate` outputs are used as optional positive readiness signals.
- Existing exporters are extended to cover readiness gaps and readiness reports.
- The CLI remains a thin adapter that reads `testcases.json`, optionally reads `automation_candidates/candidates.json`, and writes a readiness report under `reports/`.
- The Streamlit UI only exposes the report as a local read-only/report-generation convenience and does not contain readiness business logic.

## 7. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase7a
```

Result:
- `135 passed in 1.17s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase7a
```

Result:
- `163 passed in 1.91s`

## 8. Risks / Notes
- Readiness is rule-based.
- Recommendations are advisory only.
- No script is generated yet.
- Target classification is heuristic.

## 9. Recommended Next Step
Phase 7B - API Test Script Draft Generation.
