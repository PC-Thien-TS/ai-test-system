# Manual QA Phase 8C API Execution Sandbox Report

## 1. Summary
Phase 8C adds a tightly gated API sandbox execution prototype for Manual QA draft packages. The implementation introduces deterministic API execution request/result models, a sandbox execution service that extracts safe request metadata from API drafts, policy and preflight gates before any HTTP call, dry-run-first CLI and UI support, and JSON/Markdown result exports. Actual execution is only possible for explicitly approved localhost override targets and never updates Manual QA `TestResult` records.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/api_execution_sandbox_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_api_execution_sandbox_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`

## 3. Implemented Scope
- API execution request/result models
- sandbox execution service
- safety gate integration
- dry-run mode
- mocked execution tests
- export support
- CLI command
- UI result preview hook

## 4. Intentionally Deferred
- Web Playwright execution
- browser launch
- Appium execution
- CI/CD integration
- production execution
- real credential management
- parallel execution
- retry engine

## 5. Safety Logic
- Default behavior is dry-run only and does not send a request when `policy.allow_execution` is false.
- Actual execution requires explicit CLI approval plus localhost allowlisting and a localhost override base URL.
- Base URLs containing `production`, `prod`, `live`, `payment-live`, or `real-bank` are blocked.
- `DELETE` is blocked by default.
- `POST`, `PUT`, and `PATCH` are blocked by default unless the policy explicitly allows write methods.
- Invalid API validation results, TODO endpoints, blocked preflight outcomes, and missing human approval block execution.
- Sandbox results are written as separate artifacts and do not overwrite `ManualTestCase`, `TestRun`, or `TestResult` state.

## 6. Execution Logic
- Request extraction prefers API draft metadata and falls back to deterministic parsing of `script_content` for method, base URL, endpoint, expected status, headers, and payload.
- The sandbox service supports injected requests-like sessions so tests can run entirely with mocked clients.
- Timeout values come from the execution safety policy and are passed into the request call only when execution is actually allowed.
- Result statuses are limited to `Not Run`, `Dry Run`, `Passed`, `Failed`, `Blocked`, and `Error`.
- `Passed` only occurs after a real allowed sandbox call and a matching expected HTTP status assertion.
- Response excerpts are truncated to 1000 characters.
- Request exceptions are captured into `APIExecutionResult` with `Error` status instead of being raised to the caller.

## 7. Reuse / Integration Notes
Phase 8C reuses the API draft package artifacts from earlier phases:
- `script_drafts/api/api_script_drafts.json` from API draft generation
- `script_drafts/api/api_script_validation.json` from API static validation
- `reports/execution_preflight_plan.json` from Phase 8B execution preflight when available

The sandbox service uses these artifacts as read-only inputs and writes separate execution result artifacts:
- `script_drafts/api/api_execution_results.json`
- `script_drafts/api/api_execution_results.md`

## 8. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8c
```

Result:
- `308 passed in 2.87s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase8c
```

Result:
- `336 passed in 3.51s`

Additional focused checks run during implementation:
- `pytest -q tests/manual_qa/test_api_execution_sandbox_service.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8c_target_api` -> `15 passed in 0.20s`
- `pytest -q tests/manual_qa/test_exporters.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8c_target_exporters` -> `56 passed in 0.67s`
- `pytest -q tests/manual_qa/test_cli.py tests/manual_qa/test_ui_helpers.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase8c_target_cli_ui` -> `65 passed in 2.13s`

## 9. Risks / Notes
- Actual execution remains tightly gated behind policy, approval, and localhost restrictions.
- Default behavior is dry-run only.
- Live execution should only be used with local or staging-style allowlisted URLs, and this phase only permits explicit localhost execution through the CLI safety gates.
- No browser execution was added.
- No fake PASS status is introduced; `Passed` only comes from an actual allowed mocked-or-real sandbox request with a matching expected status.

## 10. Recommended Next Step
Phase 8D — API Execution Result Evidence Integration
