# Manual QA Phase 7D Web Playwright Readiness Report

## 1. Summary
Implemented a deterministic readiness review layer for future Web Playwright draft generation. This phase adds Web Playwright readiness and gap models, a rule-based analyzer service, JSON and Markdown export support, a CLI report command, and a small optional local UI report hook. It assesses whether web UI-like manual test cases have enough URL, selector, action, and assertion detail for future Playwright draft generation without generating scripts or executing browser automation.

## 2. Files Added / Changed
- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/web_playwright_readiness_service.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/cli.py`
- `orchestrator/manual_qa/ui_helpers.py`
- `orchestrator/manual_qa/ui_streamlit.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_web_playwright_readiness_service.py`
- `tests/manual_qa/test_exporters.py`
- `tests/manual_qa/test_cli.py`
- `tests/manual_qa/test_ui_helpers.py`
- `docs/reports/MANUAL_QA_PHASE7D_WEB_PLAYWRIGHT_READINESS_REPORT.md`

## 3. Implemented Scope
- Web Playwright readiness models
- readiness analyzer service
- gap detection
- URL/selector/action/assertion hint detection
- readiness export
- CLI command
- optional UI report hook
- tests

## 4. Intentionally Deferred
- actual Playwright script generation
- Playwright execution
- browser installation
- Appium generation
- API generation
- API routes
- production dashboard
- external AI calls

## 5. Readiness Logic
The readiness analyzer is deterministic and rule-based:
- URL detection looks for explicit full URLs or route-like paths such as `/login`, `/dashboard`, or `/admin/users`.
- Selector hint detection looks for stable identifiers and control hints such as `data-testid`, `id=`, `#selector`, `.class`, `role=`, `aria-label`, button text, or field labels.
- Action hint detection looks for concrete user actions such as `click`, `fill`, `select`, `submit`, `navigate`, `upload`, and `download`.
- Assertion hint detection looks for explicit outcomes such as `should see`, `redirects`, `URL contains`, `success message`, `validation error`, or `element visible`.
- Risk and gap detection flags:
  - missing page URL
  - missing selector hints
  - missing user action details
  - missing assertion
  - login/session dependency
  - dynamic/flaky UI dependency
  - file upload/download complexity
  - OTP/captcha/manual approval or external payment blockers
  - visual/manual judgment dependency
- Score starts at `50`, adds points for concrete automation-friendly detail, and subtracts points for missing data or unstable/manual-only risk factors.
- Status rules are:
  - `Ready` when score is at least `75` and there are no high-severity or critical gaps
  - `Needs More Data` when score is between `40` and `74`
  - `Not Suitable` when score is below `40` or a critical blocker is present

## 6. Reuse / Integration Notes
Phase 7D composes existing Manual QA artifacts rather than introducing a separate automation stack:
- `ManualTestCase` remains the primary analysis input.
- `ScriptGenerationReadiness` is used as optional upstream target and readiness context.
- `AutomationCandidate` outputs are reused as optional positive readiness signals.
- Existing exporters are extended to cover Web Playwright readiness reports.
- The CLI remains a thin adapter that reads `testcases/testcases.json`, optionally reads `reports/script_readiness.json` and `automation_candidates/candidates.json`, and writes a readiness report under `reports/`.
- The Streamlit UI only adds a local report-generation and preview hook without embedding analysis logic.

## 7. Test Results
Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase7d
```

Result:
- `196 passed in 1.65s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase7d
```

Result:
- `224 passed in 2.29s`

## 8. Risks / Notes
- readiness is rule-based
- recommendations are advisory only
- no Playwright script is generated yet
- no browser automation is executed
- selector and action inference is heuristic

## 9. Recommended Next Step
Phase 7E - Web Playwright Script Draft Generation
or
Phase 8 - Safe Script Execution Sandbox Design.
