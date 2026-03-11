# QA_EXECUTION_PLAN

Scope: weekly execution plan for the smoke pack in [SMOKE_MUST_PASS.md](c:/Users/PC-Thien/ai_test_system/SMOKE_MUST_PASS.md), based only on `FEATURE_MAP.md`, `ROUTES.md`, `API_LIST.md`, `TEST_SUGGESTIONS.md`.

## Run Model

### R0: Smoke
- Target: `SMK-01` to `SMK-24` (execute all `P0` first, then `P1`).
- Focus modules: Authentication, Search, Store / merchant features, Menu / catalog, Admin panel.

### R1: Regression
- Target: re-run failed smoke tests after fixes + broader module checks from `TEST_SUGGESTIONS.md` for the same priority modules.
- Include retest of all resolved defects from R0.

## Entry Criteria

### R0 entry
- Test environment is deployed and reachable for app and web admin routes in `ROUTES.md`.
- API endpoints under target modules are reachable as listed in `API_LIST.md`.
- At least one valid admin account and one valid end-user account are available.
- Test data exists for store verification and catalog objects, or can be created during run.
- Evidence capture is ready: screenshot, network/API log, console log.

### R1 entry
- R0 exit criteria are met.
- Fix build is deployed with defect IDs linked to change list.
- Impacted smoke tests are mapped for retest.

## Exit Criteria

### R0 exit
- 100% of `P0` smoke tests executed.
- 0 open Blocker defects.
- `P0` pass rate >= 95%.
- All failed cases have reproducible evidence package attached.
- All `UNKNOWN` flows in smoke have explicit evidence request outcome documented.

### R1 exit
- 100% of failed/blocked R0 tests are retested.
- 0 open Blocker defects.
- Regression pass rate >= 95% on selected regression scope.
- No unresolved defect without owner, severity, and ETA.

## Bug Severity and Go/No-Go Policy

### Severity policy
- S0 Blocker: system unusable or release gate broken (example: cannot login, cannot submit/approve/reject store verify, core admin pages unavailable, severe data corruption).
- S1 Critical: major feature broken with no acceptable workaround.
- S2 Major: functional issue with workaround available.
- S3 Minor: cosmetic/content/non-blocking issue.

### Go/No-Go rule
- NO-GO: any open S0 Blocker.
- Conditional GO: no S0, and all S1 issues have approved risk acceptance, owner, and committed fix timeline.
- GO: no open S0 and no unresolved high-risk unknown in P0 evidence.

## Day-by-Day Schedule (Day1-Day3)

### Day1
- Execute all `P0` smoke tests first (`SMK-01`, `SMK-02`, `SMK-04`, `SMK-06`, `SMK-07`, `SMK-09`, `SMK-11`, `SMK-13`, `SMK-15`, `SMK-16`, `SMK-19`, `SMK-20`, `SMK-23`, `SMK-24`).
- Triage defects within 2 hours of detection.
- Deliverable: Day1 smoke status report + defect list.

### Day2
- Execute remaining `P1` smoke tests and collect UNKNOWN-flow evidence requests.
- Verify fixes for Day1 blockers/criticals.
- Deliverable: Updated execution sheet + fix verification notes.

### Day3
- Run R1 regression scope (retest failed cases + impacted module checks).
- Final triage and release decision.
- Deliverable: Go/No-Go summary with residual risk register.

## Required Artifacts Per Test Run

- Test execution sheet with testcase ID, status, tester, timestamp.
- Screenshot for each failed step (before/after if fix retest).
- API evidence: request payload, response payload/status, endpoint path.
- Browser/app logs: console errors and network capture (HAR or equivalent).
- Defect tickets linked to testcase IDs and severity.
- Final run summary (`R0` and `R1`) with explicit Go/No-Go decision.
