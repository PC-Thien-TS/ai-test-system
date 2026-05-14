# Manual QA Phase Readiness Review

## 1. Executive Summary

The repository is ready for a Manual QA workflow **as an additive layer**, but Phase 1 should reuse existing orchestration capabilities instead of reimplementing them. The safest next step is to add a thin Manual QA domain package that composes existing project/run, requirement, artifact, evidence, failure-memory, bug-draft, candidate-scoring, and export utilities.

Key conclusions:

- The platform already has project management, run management, storage/artifact APIs, requirement parsing/generation, failure memory, evidence handling, bug/defect generation, risk/candidate scoring, plugin execution, dashboard intelligence, mobile testing, and export scripts.
- Manual QA should not duplicate automated run orchestration or storage abstractions. It should introduce manual-specific models and services that adapt to existing repository patterns.
- The best primary location is `orchestrator/manual_qa/`, with optional `api/routes/manual_qa.py` and `scripts/manual_qa_*.py` added later when Phase 1 needs API/CLI exposure.
- Initial implementation should avoid writing workspace/run artifacts into source-controlled folders by default.
- Baseline tests are not fully reliable without environment setup: raw `pytest` cannot import local packages; `PYTHONPATH=.` gets further but is blocked by missing `appium`. A targeted non-mobile subset passes.

Recommended next step: implement Phase 1 as a small `orchestrator/manual_qa/` package with tests under `tests/manual_qa/`, reusing `orchestrator.advanced_qa`, `orchestrator.storage`, `orchestrator.failure_analysis`, `orchestrator.candidates`, and current script/export conventions.

## 2. Repository Status

- Repository root: `/workspace/ai-test-system`
- Current branch: `work`
- Initial `git status --short`: clean output before this report was created.
- Working tree after review: expected dirty state because this report file was created.
- AGENTS.md files: none found by `find .. -name AGENTS.md -print`.
- Production code changed: no.
- Feature code created/refactored: no.
- Review artifact created: `docs/reports/MANUAL_QA_PHASE_READINESS_REVIEW.md`.

## 3. Current Folder Map

| Folder | Purpose / contents observed |
|---|---|
| `api/` | FastAPI apps and route modules for health, projects, runs, storage, platform, plugins, mobile, and dashboard intelligence. Main app and dashboard app are separate entrypoints. |
| `orchestrator/` | Core orchestration domain: project service, plugin execution, requirement generation, risk prioritization, evidence analysis, storage, memory, candidates, decision policy, failure analysis, self-healing, connectors, dashboard intelligence, adapters, and compatibility. |
| `mobile_appium/` | Mobile testing service, Appium driver integration, exploration runner, journeys, navigation policy adapter, screen abstractions, and mobile run service. |
| `tests/` | Large pytest suite covering API, project service, storage, requirement generation, plugins, agentic testing, mobile, dashboard intelligence, candidates, decision policy, memory, self-healing, and Rankmate wave1 assets. |
| `docs/` | Architecture docs, findings, API plans, SRS modules, traceability, wave reports, mobile design docs, adapter guides, and now this readiness report. |
| `test-assets/` | SRS raw PDFs, normalized CSV requirements, coverage matrix, mappings, and traceability templates. |
| `scripts/` | Execution and utility scripts for API regression, UI smoke/E2E, release audit, pipeline execution, artifact collection, pytest reporting, Excel export, and notification. |
| `domains/` | Domain-specific prompt/design knowledge for order, store verification, and release audit workflows. |
| `prompts/` | General prompt templates for review, checklist, extraction, regression, and generation. |
| `kb/` | Knowledge-base build/query tooling with config and indexing helpers. |
| `schemas/` | Mobile/exploration/oracle YAML schemas. |
| `taxonomy/` | Mobile feature taxonomy, screen contracts, oracle library, and test obligation matrices. |
| `dashboard/` | Dashboard-oriented documentation/assets; separate from `api/dashboard_app.py`. |
| `.github/workflows/` | CI workflow configuration, including pytest/lark workflow. |

Structure command counts recorded during review:

- Directories to depth 4: 172.
- Files to depth 4 first 500 rows captured.
- Config/entrypoint files found to depth 3: 16.
- API files to depth 5: 14.
- Orchestrator files to depth 5: 189.
- Mobile files to depth 5: 15.
- Test files to depth 5: 168.
- Docs files to depth 5: 92.
- Test-assets files to depth 5: 17.

## 4. Application Entrypoints

| Entrypoint | File | Notes |
|---|---|---|
| Main FastAPI app | `api/app.py` | Creates `Universal Testing Platform API`; registers health, projects, runs under both `/projects` and `/runs`, storage, platform, plugins, and mobile routers. Version is `3.0.0`, but the module docstring/startup message still references v2.1. |
| Dashboard intelligence FastAPI app | `api/dashboard_app.py` | Separate app registering `api.routes.dashboard_intelligence` under its own router prefix. Not included in main `api/app.py`. |
| Dashboard intelligence routes | `api/routes/dashboard_intelligence.py` | Executive summary, release readiness, failure memory, decisions, self-healing, candidates, governance, and trends. |
| API route modules | `api/routes/*.py` | Health, mobile, platform, plugins, projects, runs, storage. |
| CLI / script style entrypoints | `scripts/*.py`, `*.py` at root | Includes `scripts/run_pipeline.py`, `scripts/run_full_pipeline.py`, `scripts/run_pytest_with_report.py`, `scripts/export_excel.py`, `ai_regression_orchestrator.py`, `ai_change_aware_regression_trigger.py`, `release_decision_gate.py`, and self-healing/release audit helpers. |
| Test entrypoint | `pytest` | No `pytest.ini` found/read; raw collection needs environment setup. `PYTHONPATH=.` is required for imports in this container, and Appium dependency is missing for mobile-related collection. |

## 5. Existing Capabilities Found

| Capability | Existing files/modules | Can reuse? | Notes |
|---|---|---:|---|
| Project management | `api/routes/projects.py`, `orchestrator/project_service.py`, `orchestrator/project_registry.py`, `orchestrator/models.py`, `tests/test_project_service.py`, `tests/test_project_registry.py` | Yes | Reuse concepts for Manual QA project profiles. Avoid duplicating platform project registry unless manual projects need separate local workspace metadata. |
| Run management | `api/routes/runs.py`, `api/routes/storage.py`, `orchestrator/run_registry.py`, `orchestrator/storage/application/services.py`, `orchestrator/storage/domain/models.py` | Yes | Manual runs can reuse storage run concepts but likely need manual-specific `TestRun` and `TestResult` fields. |
| Requirement parsing | `orchestrator/advanced_qa/requirement_parser.py`, `orchestrator/requirement_ingestion.py`, `test-assets/srs/normalized/*.csv`, `docs/srs/modules/*.md` | Yes | Strong reuse target. Manual import should call/adapter-wrap existing parser and normalization patterns. |
| Test case generation | `orchestrator/advanced_qa/requirement_generator.py`, `orchestrator/advanced_qa/requirement_outputs.py`, `tests/test_requirement_generator.py`, `tests/testcase_generator.py`, `core/orchestrator.py`, `core/schema_validator.py` | Yes | Manual QA should generate manual test cases from existing normalized requirement outputs, not duplicate generation rules. |
| Checklist generation | `prompts/checklist.md`, domain prompt packs such as `domains/*/prompts/06_release_checklist.md`, docs release checklist artifacts | Partial | Prompt assets exist, but a dedicated deterministic manual checklist generator service is not obvious. Add manual-specific checklist service that can reuse prompts and requirement model. |
| Coverage mapping | `docs/FUNCTIONAL_MODULES.md`, `docs/SRS_COVERAGE_MATRIX.md`, `test-assets/srs/coverage/srs_coverage_matrix.csv`, `test-assets/srs/mappings/*.csv`, `orchestrator/advanced_qa/requirement_mapper.py` | Yes | Manual QA should integrate with existing SRS-to-test traceability and coverage gap conventions. |
| Storage/artifacts | `api/routes/storage.py`, `orchestrator/storage/*`, `orchestrator/candidates/infrastructure/artifact_writer.py`, `scripts/collect_release_evidence.py` | Yes | Do not invent a parallel artifact store. Add manual evidence records that can be serialized through storage/artifact services. |
| Evidence handling | `orchestrator/evidence_analysis.py`, `orchestrator/evidence_collector.py`, `orchestrator/mobile_evidence_adapter.py`, `orchestrator/adapters/evidence_context.py`, `docs/traceability/*` | Yes | Manual evidence should reuse/extend evidence concepts and artifact metadata. Avoid mixing screenshots/logs directly into source folders. |
| Failure memory | `api/routes/storage.py`, `orchestrator/storage/application/services.py`, `orchestrator/memory/*`, `docs/FAILURE_MEMORY_ENGINE_V1.md`, `tests/test_storage_persistence_layer.py` | Yes | Future `remember-failure` and `find-similar-failure` map directly to existing exact/similar lookup concepts. |
| Bug/defect reporting | `orchestrator/bug_report_generator.py`, `orchestrator/failure_analysis/*`, `orchestrator/candidates/*`, `tests/test_bug_report_generator.py`, `tests/test_candidate_generation_system.py` | Yes | Manual `generate-bug` should produce a `BugDraft` that can feed candidate/defect generation instead of creating a disconnected format. |
| Plugin execution | `orchestrator/plugins/*`, `orchestrator/compatibility.py`, `api/routes/plugins.py`, plugin tests | Yes, later | Manual QA Phase 1 likely should not execute plugins, but automation-candidate scoring can reference plugin capability metadata. |
| Mobile testing | `mobile_appium/*`, `api/routes/mobile.py`, `orchestrator/mobile_failure_classifier.py`, mobile tests | Reuse carefully | Manual QA can attach mobile evidence and classify failures, but tests require Appium package in this environment. Do not couple Phase 1 core to Appium imports. |
| Dashboard/reporting | `api/routes/platform.py`, `api/routes/dashboard_intelligence.py`, `api/dashboard_app.py`, `ai_qa_lead_dashboard.py`, dashboard tests | Yes, later | Manual status summaries can eventually feed dashboard intelligence, but Phase 1 should keep reporting as file exports unless API scope is explicit. |
| Agentic testing | `orchestrator/agentic_testing.py`, `orchestrator/ai_testing_flow.py`, `tests/test_agentic_testing.py` | Yes | Existing flow already selects requirement/test generation, failure analysis, locator healing, bug report, and mobile failure analysis actions. Manual layer should wrap deterministic pieces without taking over all agentic behavior. |
| Export to Excel/Markdown/JSON | `scripts/export_excel.py`, `scripts/export_release_audit_report.py`, `orchestrator/advanced_qa/requirement_outputs.py`, docs/report artifacts, many JSON artifact writers | Yes | Add manual exporters using existing script conventions. Prefer JSON/Markdown first; Excel can reuse/export via existing script patterns. |

## 6. Overlap With Planned Manual QA Phases

| Planned Manual QA Feature | Already exists? | Existing location | Recommendation |
|---|---:|---|---|
| create-project | Yes | `api/routes/projects.py`, `orchestrator/project_service.py`, `orchestrator/project_registry.py` | Add Manual QA `ProjectProfile` wrapper only if manual projects need tester-facing fields; otherwise map to existing platform project. |
| import-requirements | Yes | `orchestrator/advanced_qa/requirement_parser.py`, `orchestrator/requirement_ingestion.py`, `test-assets/srs/*` | Reuse parser and normalized requirement patterns. Add importer adapters for CSV/Markdown/PDF-derived text only. |
| generate-checklist | Partial | `prompts/checklist.md`, `domains/*/prompts/06_release_checklist.md`, checklist docs | Implement a manual checklist generator, but reuse existing prompt assets and requirement model. |
| generate-testcases | Yes | `orchestrator/advanced_qa/requirement_generator.py`, `orchestrator/advanced_qa/requirement_outputs.py` | Reuse requirement-aware generator; add formatting/mapping into `ManualTestCase`. |
| export-testcases | Partial | `scripts/export_excel.py`, `scripts/export_release_audit_report.py`, JSON/Markdown report patterns | Add manual exporters for Markdown/JSON/CSV/Excel, reusing script conventions and not changing existing export scripts in Phase 1 unless needed. |
| create-suite | Partial | `orchestrator/adapters/*/suite_registry.py`, plugin suite concepts, docs test plans | Add manual `TestSuite` model/service. Do not reuse automated adapter suite registry directly because manual suites need tester assignment/status fields. |
| create-run | Yes | `api/routes/runs.py`, `api/routes/storage.py`, `orchestrator/storage/application/services.py` | Reuse run storage patterns but maintain manual run semantics separately from automated execution paths. |
| update-result | Partial | Storage run status update, quality gate result models | Add manual `TestResult` records with step/case status. Map aggregate status to existing run status only at boundary. |
| attach-evidence | Yes | `api/routes/storage.py`, `orchestrator/evidence_collector.py`, `orchestrator/evidence_analysis.py`, `orchestrator/mobile_evidence_adapter.py` | Reuse artifact/evidence model concepts. Add manual evidence metadata for screenshots, notes, logs, links. |
| generate-bug | Yes | `orchestrator/bug_report_generator.py`, `orchestrator/failure_analysis/*`, `orchestrator/candidates/*` | Manual failures should create `BugDraft` using existing bug report generator/candidate services. |
| remember-failure | Yes | `api/routes/storage.py`, `orchestrator/storage/application/services.py`, `orchestrator/memory/*` | Directly wrap existing failure memory exact/similar lookup services. |
| find-similar-failure | Yes | `api/routes/storage.py`, `orchestrator/storage/application/services.py`, `orchestrator/memory/*` | Reuse similar lookup and vector/local memory repository; add manual-friendly query creation. |
| score-automation-candidates | Yes/Partial | `orchestrator/candidates/*`, `orchestrator/advanced_qa/risk_prioritizer.py`, `orchestrator/plugins/compatibility.py`, `docs/DECISION_POLICY_ENGINE_V2.md` | Build a manual automation candidate scorer by composing risk prioritizer, candidate models, and plugin capability metadata. |

## 7. Recommended Location for Manual QA Layer

Compared options:

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| `src/manual_qa/` | Common in packaged Python projects | Repository does not currently use a `src/` layout; would introduce a new import style and likely require config changes. | Do not use. |
| `manual_qa/` | Clear standalone product layer; easy CLI imports | Existing domain packages mostly live under `orchestrator/`; standalone package may duplicate orchestration abstractions and need new packaging/test conventions. | Acceptable only if Manual QA is intended as an independent app. |
| `orchestrator/manual_qa/` | Matches current package layout; can reuse `orchestrator.advanced_qa`, `storage`, `memory`, `candidates`, `failure_analysis`; avoids new package root; easiest for tests with existing import style. | Must keep boundaries clear so manual workflow does not become tangled with automated plugin execution. | **Recommended primary location.** |
| `api/routes/manual_qa.py` | Natural API exposure point | API should be a thin adapter, not the first home for domain logic; adding it in Phase 1 may force route decisions too early. | Add later after domain service stabilizes. |
| `scripts/manual_qa_*.py` | Useful for local tester workflows and smoke usage | Scripts are not a maintainable home for domain logic. | Add later as thin CLI wrappers. |

Primary recommendation: place Manual QA domain/application code in `orchestrator/manual_qa/`. Add `api/routes/manual_qa.py` only when API exposure is explicitly in scope. Add `scripts/manual_qa_*.py` only as thin wrappers over the package.

## 8. Proposed Target Structure for Phase 1

Suggested Phase 1 target structure based on this repository:

```text
orchestrator/
  manual_qa/
    __init__.py
    models.py
    project_service.py
    requirement_importer.py
    requirement_normalizer.py
    checklist_generator.py
    testcase_generator.py
    suite_service.py
    run_service.py
    result_service.py
    evidence_service.py
    bug_service.py
    failure_memory_service.py
    automation_candidate_scorer.py
    exporters.py
    prompts/
      checklist_prompt.md
      testcase_prompt.md

scripts/
  manual_qa_generate.py          # optional later, thin wrapper only
  manual_qa_export.py            # optional later, thin wrapper only

api/routes/
  manual_qa.py                   # optional later, thin API adapter only

tests/
  manual_qa/
    test_project_service.py
    test_requirement_importer.py
    test_checklist_generator.py
    test_testcase_generator.py
    test_suite_service.py
    test_run_service.py
    test_result_service.py
    test_evidence_service.py
    test_bug_service.py
    test_failure_memory_service.py
    test_automation_candidate_scorer.py
    test_exporters.py
```

Notes:

- Do not add `workspaces/` as source-controlled runtime storage unless it contains only a README or `.gitkeep`; actual manual QA workspace artifacts should be ignored or written under existing artifact/storage conventions.
- Keep API and scripts as adapters over domain/application services, not the source of business rules.
- Keep mobile/Appium-dependent imports out of the Manual QA core package so non-mobile Manual QA tests can run without Appium installed.

## 9. Data Model Recommendation

Minimal high-level models/schemas for Phase 1:

| Model | Suggested fields / purpose |
|---|---|
| `ProjectProfile` | `project_id`, `name`, `source_type`, `product_type`, `description`, `owner`, `tags`, `created_at`, `updated_at`, `metadata`, optional link to existing platform project. |
| `NormalizedRequirement` | `requirement_id`, `title`, `description`, `module`, `submodule`, `priority`, `acceptance_criteria`, `business_rules`, `roles`, `dependencies`, `risk_hints`, `source_ref`, `traceability_links`. Align with `orchestrator.advanced_qa.requirement_models.Requirement`. |
| `ManualTestCase` | `test_case_id`, `requirement_ids`, `title`, `preconditions`, `steps`, `expected_result`, `priority`, `type`, `module`, `tags`, `automation_candidate_score`, `metadata`. |
| `TestSuite` | `suite_id`, `name`, `project_id`, `test_case_ids`, `scope`, `owner`, `created_at`, `tags`, `metadata`. Keep separate from automated adapter suite registries. |
| `TestRun` | `run_id`, `suite_id`, `project_id`, `tester`, `status`, `started_at`, `completed_at`, `environment`, `summary`, `metadata`. Map aggregate status to existing storage run only at integration boundary. |
| `TestResult` | `result_id`, `run_id`, `test_case_id`, `status`, `actual_result`, `notes`, `defect_ids`, `evidence_ids`, `updated_at`, `duration`, `metadata`. |
| `Evidence` | `evidence_id`, `run_id`, `test_case_id`, `type`, `path_or_url`, `content_type`, `description`, `created_at`, `metadata`, optional artifact storage reference. |
| `BugDraft` | `bug_id`, `title`, `severity`, `priority`, `environment`, `steps_to_reproduce`, `expected_result`, `actual_result`, `evidence_ids`, `failure_signature`, `owner_suggestion`, `confidence`, `metadata`. Align with existing bug/candidate generation. |
| `FailureSignature` | `signature_id`, `module`, `error_type`, `symptom`, `normalized_message`, `stack_or_signal`, `environment`, `fingerprint`, `confidence`, `metadata`. Align with existing storage/memory failure signature concepts. |

## 10. Implementation Risks

- **Duplicating existing orchestrator logic:** Requirement parsing/generation, run storage, failure memory, bug generation, and candidate scoring already exist. Manual QA should compose these instead of forking them.
- **Mixing manual workflow with automated run management:** Manual `TestRun` and automated execution `Run` have different semantics. Integrate at storage/reporting boundaries only.
- **Breaking current tests:** Main test collection is already environment-sensitive. Keep Phase 1 core tests independent from Appium and external services.
- **Inconsistent import style:** Repository currently imports from root packages such as `orchestrator` and `api`; do not introduce `src/` layout without packaging changes.
- **Workspace files accidentally committed:** Manual QA will create artifacts. Default output should go under ignored artifact/workspace locations or existing storage services, not docs/source folders.
- **Dashboard router inconsistency:** Dashboard intelligence is in `api/dashboard_app.py`, not the main app. Decide later whether Manual QA dashboard views belong in main API or dashboard app.
- **Version label inconsistency:** `api/app.py` still says v2.1 in docstring/startup text while FastAPI version is `3.0.0`.
- **Environment/test dependency issues:** Raw pytest cannot import local packages in this container; `PYTHONPATH=.` fixes local imports but exposes missing `appium` dependency for mobile-related tests.
- **Manual vs AI-generated content traceability:** Generated manual checklists/test cases should keep requirement source IDs and prompt/version metadata to preserve auditability.
- **Evidence privacy/security:** Manual evidence can include screenshots or logs with sensitive data; storage paths and export formats need sanitization rules.

## 11. Test Baseline Result

### Command 1

```bash
pytest -q --maxfail=10
```

Result: **failed during collection** with 10 errors in 1.61s.

Notable failures:

- `ModuleNotFoundError: No module named 'orchestrator'`
- `ModuleNotFoundError: No module named 'mobile_appium'`
- `ModuleNotFoundError: No module named 'api.app'`

Likely reason: local repository root is not on `PYTHONPATH` in this container's pytest invocation.

### Command 2

```bash
PYTHONPATH=. pytest -q --maxfail=10
```

Result: **failed during collection** with 8 errors in 4.41s.

Notable failure:

- `ModuleNotFoundError: No module named 'appium'`

Likely reason: local imports work with `PYTHONPATH=.`, but the environment lacks the Appium Python dependency required by `mobile_appium/driver.py` and any tests importing the mobile package.

### Command 3

```bash
PYTHONPATH=. pytest -q tests/test_requirement_generator.py tests/test_storage_persistence_layer.py tests/test_bug_report_generator.py tests/test_candidate_generation_system.py --maxfail=10
```

Result: **passed**.

Summary:

- `28 passed in 0.42s`

Baseline reliability: partial. The non-mobile requirement/storage/bug/candidate subset is reliable enough to guide Manual QA Phase 1, but full-suite baseline is not reliable until import path and Appium dependency setup are resolved.

Suggested smaller command for future Manual QA implementation:

```bash
PYTHONPATH=. pytest -q tests/test_requirement_generator.py tests/test_storage_persistence_layer.py tests/test_bug_report_generator.py tests/test_candidate_generation_system.py tests/manual_qa --maxfail=10
```

## 12. Recommended Next Step

Next Codex task for Phase 1:

> Implement the initial Manual QA domain package under `orchestrator/manual_qa/` with no API routes yet. Add data models, project profile creation, requirement import/normalization adapters over `orchestrator.advanced_qa`, checklist generation, manual test case generation, JSON/Markdown exporters, and focused tests under `tests/manual_qa/`. Keep all runtime outputs in temporary/test directories or existing artifact/storage abstractions. Do not import `mobile_appium` from the Manual QA core package.

Phase 1 acceptance criteria should include:

- `ProjectProfile` can be created in-memory/local test storage.
- Requirements can be imported from dict/list/JSON/YAML/Markdown-style text via existing parser where possible.
- Checklist and manual test cases preserve requirement IDs.
- Exports support JSON and Markdown at minimum.
- Tests run with `PYTHONPATH=.` and do not require Appium.
- No production API behavior changes unless separately requested.

## 13. Commands Executed

```bash
pwd && git status --short && git branch --show-current && find .. -name AGENTS.md -print
```

```bash
find . -maxdepth 4 -type d | sort > /tmp/ai_dirs.txt
find . -maxdepth 4 -type f | sort | sed -n '1,500p' > /tmp/ai_files_500.txt
find . -maxdepth 3 -type f \( -name "README.md" -o -name "pyproject.toml" -o -name "requirements*.txt" -o -name "pytest.ini" -o -name "Makefile" -o -name "*.yml" -o -name "*.yaml" \) | sort > /tmp/ai_configs.txt
sed -n '1,220p' README.md > /tmp/ai_readme_220.txt
sed -n '1,220p' api/app.py 2>/dev/null > /tmp/ai_api_app_220.txt || true
sed -n '1,220p' api/dashboard_app.py 2>/dev/null > /tmp/ai_dashboard_app_220.txt || true
sed -n '1,220p' pytest.ini 2>/dev/null > /tmp/ai_pytest_ini_220.txt || true
find api -maxdepth 5 -type f | sort 2>/dev/null > /tmp/ai_api_files.txt || true
find orchestrator -maxdepth 5 -type f | sort 2>/dev/null > /tmp/ai_orchestrator_files.txt || true
find mobile_appium -maxdepth 5 -type f | sort 2>/dev/null > /tmp/ai_mobile_files.txt || true
find tests -maxdepth 5 -type f | sort 2>/dev/null > /tmp/ai_tests_files.txt || true
find docs -maxdepth 5 -type f | sort 2>/dev/null > /tmp/ai_docs_files.txt || true
find test-assets -maxdepth 5 -type f | sort 2>/dev/null > /tmp/ai_test_assets_files.txt || true
wc -l /tmp/ai_dirs.txt /tmp/ai_files_500.txt /tmp/ai_configs.txt /tmp/ai_api_files.txt /tmp/ai_orchestrator_files.txt /tmp/ai_mobile_files.txt /tmp/ai_tests_files.txt /tmp/ai_docs_files.txt /tmp/ai_test_assets_files.txt
```

```bash
rg -n "requirement|testcase|test case|checklist|coverage|evidence|artifact|failure|memory|storage|bug|defect|run|suite|agentic|plugin|dashboard|mobile" . -g '!*.pyc' -g '!__pycache__/**' -g '!.git/**' -g '!.venv/**' | sed -n '1,300p' > /tmp/ai_overlap_search.txt
find . -maxdepth 4 -type f -name "__init__.py" | sort > /tmp/ai_init_files.txt
rg -n "from orchestrator|from api|import orchestrator|import api" . -g '!__pycache__/**' -g '!.git/**' -g '!.venv/**' | sed -n '1,120p' > /tmp/ai_import_style.txt
wc -l /tmp/ai_overlap_search.txt /tmp/ai_init_files.txt /tmp/ai_import_style.txt
sed -n '1,60p' /tmp/ai_configs.txt
printf '\ninit sample\n'; sed -n '1,80p' /tmp/ai_init_files.txt
```

```bash
pytest -q --maxfail=10
```

```bash
PYTHONPATH=. pytest -q --maxfail=10
```

```bash
PYTHONPATH=. pytest -q tests/test_requirement_generator.py tests/test_storage_persistence_layer.py tests/test_bug_report_generator.py tests/test_candidate_generation_system.py --maxfail=10
```

```bash
rg -n "excel|xlsx|markdown|json|export|Bug|bug|FailureSignature|Evidence|artifact|suite|TestSuite|candidate|automation" orchestrator api scripts tests docs -g '!__pycache__/**' | sed -n '1,240p'
```

```bash
mkdir -p docs/reports
cat > docs/reports/MANUAL_QA_PHASE_READINESS_REVIEW.md
```
