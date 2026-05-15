# Manual QA Phase 8E API Execution History Report

## 1. Summary
Phase 8E adds metadata-only API execution history and trend reporting on top of the Phase 8D evidence and summary artifacts. The implementation introduces deterministic history entry and trend summary models, a history service that reads saved local API execution summary/evidence artifacts, repeated failure and flaky-candidate detection using metadata only, JSON/Markdown export support, a CLI command, and a small read-only Streamlit preview hook. No scripts are executed and Manual QA run/result state remains unchanged.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/api_execution_history_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_api_execution_history_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`

## 3. Implemented Scope
- API execution history entry model
- API execution trend summary model
- history service
- trend aggregation
- repeated failure detection
- flaky candidate detection
- export support
- CLI command
- UI preview hook
- tests

## 4. Intentionally Deferred
- script execution
- HTTP calls
- Web Playwright execution
- browser launch
- CI/CD integration
- automatic Jira/Azure DevOps push
- Manual TestResult overwrite

## 5. History / Trend Logic
- History entries are created directly from saved `APIExecutionSummary` artifacts and preserve counts, rates, status, related evidence IDs, bug suggestion IDs, and failure signature IDs.
- Trend aggregation computes total runs, total executions, status totals, average pass rate, average failure rate, and the latest saved summary status.
- Trend status rules are deterministic:
  - `No History` when no entries exist
  - `All Dry Run` when every entry is `All Dry Run`
  - `Regressing` when the latest failure rate rises above earlier averages or a latest `Failed` result follows earlier `Passed`/`Needs Review`
  - `Improving` when the latest pass rate rises above earlier averages and latest failed/error counts decrease
  - `Stable` when pass/failure rates are roughly unchanged
  - `Needs Review` otherwise
- Repeated failure detection uses metadata-only keys such as endpoint/method, test case ID, error type, and HTTP status mismatch patterns.
- Flaky candidate detection flags test cases or endpoint/method combinations that have both passed and failed/error outcomes in saved evidence.

## 6. Reuse / Integration Notes
Phase 8E reuses `APIExecutionSummary`, `APIExecutionEvidence`, bug suggestion artifacts, and failure signature artifacts produced in Phase 8D. The history service reads those local JSON files and produces separate history/trend artifacts without mutating manual QA run state or sandbox execution results.

## 7. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8e
```

Result:
- `357 passed in 3.42s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase8e
```

Result:
- `385 passed in 4.00s`

Additional focused checks run during implementation:
- `pytest -q tests/manual_qa/test_api_execution_history_service.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8e_target_service` -> `12 passed in 0.39s`
- `pytest -q tests/manual_qa/test_exporters.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8e_target_exporters` -> `64 passed in 0.73s`
- `pytest -q tests/manual_qa/test_cli.py tests/manual_qa/test_ui_helpers.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8e_target_cli_ui` -> `80 passed in 2.47s`

## 8. Risks / Notes
- Trend reporting is metadata-only.
- History depends on saved local artifacts and does not infer missing runs.
- Flaky detection is heuristic and intentionally simple.
- No execution is performed in this phase.
- No fake PASS is introduced; history reflects only saved sandbox/evidence artifacts.

## 9. Recommended Next Step
Phase 9A — Web Playwright Execution Sandbox Design
