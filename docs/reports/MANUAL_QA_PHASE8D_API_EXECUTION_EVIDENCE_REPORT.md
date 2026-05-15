# Manual QA Phase 8D API Execution Evidence Report

## 1. Summary
Phase 8D integrates API sandbox execution results from Phase 8C into metadata-only evidence and reporting artifacts. The implementation adds deterministic API execution evidence and summary models, a dedicated evidence service that converts `APIExecutionResult` records into separate evidence outputs, summary generation, draft bug suggestions for failed or error outcomes, optional metadata-only failure signatures, exporter support, a CLI command, and a small read-only Streamlit preview hook. Manual QA run and result state remains unchanged.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/api_execution_evidence_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_api_execution_evidence_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`

## 3. Implemented Scope
- API execution evidence model
- API execution summary model
- evidence service
- summary service
- bug suggestion from Failed/Error execution
- failure signature from Failed/Error execution
- export support
- CLI command
- UI preview hook
- tests

## 4. Intentionally Deferred
- Web Playwright execution
- browser launch
- Appium execution
- CI/CD integration
- automatic Jira/Azure DevOps push
- Manual TestResult overwrite
- real credential management

## 5. Evidence Logic
- Each `APIExecutionResult` is converted into one `APIExecutionEvidence` item with metadata-only fields.
- Evidence preserves execution identifiers, HTTP metadata, assertion outcome, response excerpt, and error details.
- Evidence artifacts are written separately under `evidence/` and do not replace or mutate Manual QA `runs/`, `testcases/`, or `TestResult` state.
- No files are copied or uploaded, and no network activity is introduced by this phase.

## 6. Summary / Bug / Failure Logic
- Summary counts sandbox execution statuses across `Passed`, `Failed`, `Blocked`, `Dry Run`, `Error`, and `Not Run`.
- `pass_rate` is `passed / total * 100`, and `failure_rate` is `(failed + error) / total * 100`.
- Summary status rules:
  - `No Results` when no execution results exist
  - `All Dry Run` when all results are dry runs
  - `Failed` when any result is `Failed` or `Error`
  - `Blocked` when any result is `Blocked` and there are no failed/error results
  - `Passed` when all results are passed
  - `Needs Review` otherwise
- Bug suggestions are only generated for `Failed` or `Error` results and remain `Draft` metadata-only bug artifacts.
- Failure signatures are only generated for `Failed` or `Error` results and stay metadata-only without writing persistent failure memory records beyond the exported signature artifacts.

## 7. Reuse / Integration Notes
Phase 8D reuses `APIExecutionResult` artifacts produced by Phase 8C and maps them into the existing Evidence, Bug Draft, and Failure Signature concepts already present in the Manual QA package. It also optionally enriches those artifacts with existing `APITestScriptDraft` and `ManualTestCase` metadata when available in the workspace.

## 8. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8d
```

Result:
- `334 passed in 3.35s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase8d
```

Result:
- `362 passed in 4.06s`

Additional focused checks run during implementation:
- `pytest -q tests/manual_qa/test_api_execution_evidence_service.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8d_target_service` -> `14 passed in 0.29s`
- `pytest -q tests/manual_qa/test_exporters.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8d_target_exporters` -> `60 passed in 0.62s`
- `pytest -q tests/manual_qa/test_cli.py tests/manual_qa/test_ui_helpers.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8d_target_cli_ui` -> `73 passed in 2.20s`

## 9. Risks / Notes
- Execution evidence depends on sandbox execution results already produced by Phase 8C.
- Bug suggestions are drafts only.
- Failure signatures are metadata-only.
- No real tracker integration was added.
- No fake PASS is introduced; this phase only reports the statuses already present in sandbox execution results.

## 10. Recommended Next Step
Phase 8E — API Execution History and Trend Report
