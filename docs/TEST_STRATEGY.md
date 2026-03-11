# Test Strategy

## Objective

Add a clean, additive SRS/traceability structure to `ai_test_system` without moving, renaming, or breaking any currently working test runners.

## Current Test Layers

- API smoke:
  - `scripts/run_api_smoke.ps1`
  - `scripts/run_api_smoke.cmd`
- API regression:
  - `scripts/run_api_regression.ps1`
  - `scripts/run_api_regression.cmd`
- API full smoke:
  - `scripts/run_api_full_smoke.ps1`
  - `scripts/run_api_full_smoke.cmd`
- UI smoke:
  - `scripts/run_ui_smoke.ps1`
  - `scripts/run_ui_smoke.cmd`
- UI E2E:
  - `scripts/run_ui_e2e.ps1`
  - `scripts/run_ui_e2e.cmd`
- Logic/unit/component:
  - `scripts/run_logic_tests.ps1`
  - `scripts/run_logic_tests.sh`
  - FE source tests documented in `TEST_LOGIC_PLAN.md`

## Structure Summary

This upgrade adds structured assets around the existing runners instead of replacing them.

```text
ai_test_system/
  config/
    test-environments.json
  docs/
    TEST_STRATEGY.md
    FUNCTIONAL_MODULES.md
    KNOWN_BLOCKERS.md
    API_REGRESSION_PLAN.md
    UI_SMOKE_PLAN.md
    UI_E2E_PLAN.md
  scripts/
    run_api_smoke.ps1
    run_api_regression.ps1
    run_ui_smoke.ps1
    run_ui_e2e.ps1
    run_logic_tests.ps1
  test-assets/
    baselines/
    seeds/
      api/
      ui/
    srs/
      raw/
      normalized/
      coverage/
      mappings/
  tests/
    shared/
      config/
      fixtures/
      helpers/
    ui_smoke/
    ui_e2e/
```

## Traceability Model

The new structure separates requirement intake from test mapping:

- `test-assets/srs/raw/`
  - drop raw SRS inputs here later
  - examples: exported markdown, docx conversions, analyst notes
- `test-assets/srs/normalized/`
  - normalized requirement rows
  - initial file: `functional_requirements_template.csv`
- `test-assets/srs/coverage/`
  - requirement-level coverage matrix
  - initial file: `srs_coverage_matrix.csv`
- `test-assets/srs/mappings/`
  - requirement-to-testcase and testcase-to-script relationships
- `test-assets/seeds/`
  - stable sample payloads, ids, and UI credentials when later needed
- `test-assets/baselines/`
  - approved response/UI baselines when the team is ready to formalize them

## Current Known State

- API smoke and API regression are active and already cover `auth`, `searches`, `store`, and several admin/business modules.
- UI smoke and UI E2E exist and currently cover auth, dashboard, organization, notification, and selected user-facing modules.
- FE unit/component coverage exists in the frontend source repo and is referenced from `TEST_LOGIC_PLAN.md`.
- Current blockers are documented in `docs/KNOWN_BLOCKERS.md`.

## Non-Goals For This Upgrade

- No production application code changes.
- No test runner renames.
- No artifact output path changes.
- No forced migration of existing docs or scripts into `tests/shared/` yet.

## How To Use This Structure

1. Add or import formal requirements into `test-assets/srs/raw/`.
2. Normalize them into `test-assets/srs/normalized/functional_requirements_template.csv`.
3. Map coverage status in `test-assets/srs/coverage/srs_coverage_matrix.csv`.
4. Link requirements to concrete tests in:
   - `test-assets/srs/mappings/requirement_to_testcase.csv`
   - `test-assets/srs/mappings/testcase_to_script.csv`
5. Keep the current executable suites unchanged until the mappings stabilize.

## Current Module Coverage Direction

- Strongest current areas:
  - `auth`
  - `organization`
  - `store`
  - `searches`
- Partially covered:
  - `account`
  - `notification`
  - `posts`
  - `news`
  - `dashboard`
  - `category-admin`
- Blocked or environment-sensitive:
  - `member`
  - `store-category-admin`
- Not yet directly automated:
  - `language`
  - `folder`
  - `storages`

## Later Migration

The following is intentionally deferred:

1. Move shared script constants into `tests/shared/config/`.
2. Move reusable PowerShell helpers into `tests/shared/helpers/`.
3. Consolidate duplicate coverage docs once the CSV structure becomes the source of truth.
4. Import formal SRS identifiers instead of provisional `REQ-*` ids.
5. Add stable seed payloads and route fixtures under `test-assets/seeds/`.
