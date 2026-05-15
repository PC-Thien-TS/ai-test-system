# Manual QA Phase 9A Web Execution Sandbox Design Report

## 1. Summary
Phase 9A adds a static Web Playwright execution sandbox design and preflight layer for Manual QA. The implementation introduces deterministic web execution safety policy, target, issue, result, and plan models; a web safety policy service; a web preflight service that reads existing Web Playwright draft package artifacts; evidence capture plan metadata for future browser sandbox work; JSON/Markdown export support; a CLI command; and a small read-only Streamlit summary hook. No Web Playwright draft is executed and no browser is launched.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/web_execution_safety_service.py`
- `orchestrator/manual_qa/web_execution_preflight_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_web_execution_safety_service.py`
- `tests/manual_qa/test_web_execution_preflight_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`

## 3. Implemented Scope
- Web execution safety policy model
- Web execution target model
- Web preflight issue/result models
- Web execution plan model
- Web safety policy service
- Web preflight service
- evidence capture plan metadata
- JSON/Markdown export support
- CLI command
- UI hook
- tests

## 4. Intentionally Deferred
- actual Playwright execution
- browser launch
- browser installation
- real screenshot/trace/video capture
- real Pass/Fail browser result creation
- Appium execution
- CI/CD integration
- production execution
- real credential management

## 5. Safety Policy Logic
- Localhost allowlists and production/live/payment-style blocklists are enforced through deterministic URL checks.
- Default policy is dry-run only and keeps browser execution disabled.
- Human approval is required by policy.
- Headless-only policy is encoded in the policy model and evidence capture plan metadata.
- File upload, file download, and external navigation are blocked by default.
- Payment flows and captcha/OTP flows are blocked by default and classified as critical risks.
- Evidence capture planning is metadata-only and includes screenshot, trace, video, console log, and network log flags.

## 6. Preflight Logic
- Targets are discovered from existing Web Playwright draft package manifest, validation, and draft JSON artifacts.
- Risk classification is static and based on metadata/script-content signals such as TODO placeholders, login dependency, upload/download usage, payment flows, captcha/OTP, base URL scope, and package validity.
- Decision rules return `Allowed`, `Blocked`, `Needs Human Approval`, or `Dry Run Only`, with the default design-only policy yielding `Dry Run Only` or `Needs Human Approval`.
- Issue detection covers missing/invalid packages, package attention flags, blocked base URLs, TODO page/selector/assertion markers, missing approval, login/session dependency, file upload/download restrictions, external navigation, payment flows, and captcha/OTP flows.
- No browser execution occurs; the service reads JSON artifacts only and does not import generated scripts, run pytest, or launch Playwright.

## 7. Reuse / Integration Notes
Phase 9A reuses Web Playwright drafts, static validation results, and package manifests produced in earlier Web Playwright phases. The new services layer on top of:
- `script_drafts/web_playwright/web_playwright_script_drafts.json`
- `script_drafts/web_playwright/web_playwright_validation.json`
- `script_drafts/web_playwright/web_playwright_package_manifest.json`

The design also mirrors the generic execution safety/preflight patterns already established for API work, while staying web-specific and browser-free.

## 8. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase9a
```

Result:
- `382 passed in 3.80s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase9a
```

Result:
- `410 passed in 4.45s`

Additional focused checks run during implementation:
- `pytest -q tests/manual_qa/test_web_execution_safety_service.py tests/manual_qa/test_web_execution_preflight_service.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase9a_target_services` -> `16 passed in 0.55s`
- `pytest -q tests/manual_qa/test_exporters.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase9a_target_exporters` -> `67 passed in 0.80s`
- `pytest -q tests/manual_qa/test_cli.py tests/manual_qa/test_ui_helpers.py --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase9a_target_cli_ui` -> `86 passed in 2.65s`

## 9. Risks / Notes
- This is design/preflight only.
- No browser execution happens yet.
- No live validation is performed.
- Policies are conservative by default and intentionally bias toward blocking risky browser flows.
- No fake PASS or browser execution result is introduced.

## 10. Recommended Next Step
Phase 9B — Web Playwright Execution Sandbox Prototype with strict safety gates.
