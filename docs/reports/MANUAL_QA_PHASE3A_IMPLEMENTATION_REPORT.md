# Manual QA Phase 3A Implementation Report

## 1. Summary

Implemented Phase 3A for the existing Manual QA core under `orchestrator/manual_qa/`.
This phase adds deterministic offline support for:

- evidence metadata modeling
- bug draft modeling
- evidence attachment to manual test results/runs
- bug draft generation from failed, blocked, or retest manual results
- JSON and Markdown export support for evidence and bug drafts

The implementation remains additive and does not introduce API routes, UI, CLI scripts, dashboard integration, mobile/Appium dependencies, external AI calls, failure memory, similar-failure lookup, automation candidate scoring, Jira/Azure DevOps integration, or remote upload/storage backends.

## 2. Files Added / Changed

Added:

- `orchestrator/manual_qa/evidence_service.py`
- `orchestrator/manual_qa/bug_service.py`
- `tests/manual_qa/test_evidence_service.py`
- `tests/manual_qa/test_bug_service.py`
- `docs/reports/MANUAL_QA_PHASE3A_IMPLEMENTATION_REPORT.md`

Changed:

- `orchestrator/manual_qa/models.py`
- `orchestrator/manual_qa/exporters.py`
- `orchestrator/manual_qa/__init__.py`
- `tests/manual_qa/test_exporters.py`

## 3. Implemented Scope

- Evidence metadata model
- BugDraft model
- Evidence attachment service
- Bug draft generation service
- JSON/Markdown export extension

## 4. Intentionally Deferred

- API routes
- UI
- CLI scripts
- failure memory
- similar failure lookup
- automation candidate scoring
- mobile/Appium integration
- dashboard integration
- Jira/Azure DevOps integration
- real file upload/storage backend

## 5. Reuse / Integration Notes

- Phase 3A builds directly on Phase 1 models such as `ManualTestCase` and the existing exporter pattern.
- Phase 3A builds directly on Phase 2 `TestRun` and `TestResult` objects by attaching evidence references into `metadata` rather than changing run/result persistence or introducing storage abstractions.
- The new `Evidence` and `BugDraft` models follow the same lightweight dataclass style used in Phases 1 and 2.
- Export support was extended inside the existing `orchestrator/manual_qa/exporters.py` module so evidence and bug drafts share the same stable JSON/Markdown conventions as bundles, suites, runs, and summaries.
- Bug draft generation is deterministic and rule-based: it derives title, severity, priority, environment, build, actual result, expected result, steps, and evidence IDs without external AI calls or external trackers.

## 6. Test Results

Commands run:

```powershell
New-Item -ItemType Directory -Force artifacts\pytest_tmp | Out-Null
$env:PYTHONPATH="."
pytest -q tests/manual_qa --maxfail=10 --basetemp=artifacts/pytest_tmp/manual_qa_phase3a
```

Result:

- `56 passed in 0.31s`

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
  --basetemp=artifacts/pytest_tmp/safe_subset_phase3a
```

Result:

- `84 passed in 0.92s`

## 7. Risks / Notes

- Evidence is metadata-only in Phase 3A. The service records references such as local paths, URLs, log handles, or notes, but it does not verify existence, copy files, or upload content.
- Evidence references are attached through `TestResult.metadata` and `TestRun.metadata` rather than new first-class storage fields, which keeps the model additive but leaves richer evidence querying to a later phase.
- Bug drafts are deterministic and rule-based. They do not perform triage, deduplication, failure-memory lookups, or external tracker synchronization.
- Bug IDs and evidence IDs are deterministic within a service instance or module-level wrapper, not globally coordinated across processes.

## 8. Recommended Phase 3B

Recommended next small phase:

- Failure Memory Adapter for Manual QA
