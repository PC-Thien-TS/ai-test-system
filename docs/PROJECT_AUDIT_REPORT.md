# Project Audit Report

Audit date: 2026-07-23  
Scope: Playwright + TypeScript automation layer for 315 Healthcare inside `C:\Users\ThienPham\Projects\ai-test-system`.

## 1. Executive Summary

The current project can continue to be used as the foundation for 315 Healthcare UI automation, but it is not yet ready to be treated as a clean official release regression framework without a short hardening pass.

The strongest parts are:
- Playwright is installed and configured with `dotenv`.
- Role-based authentication is implemented through reusable setup files and storage state.
- Credentials are read from environment variables, not hard-coded in source.
- `local-network-access` is granted for `https://devmeta.315healthcare.com`.
- The 315 MAC Address integration is no longer mocked and now has useful diagnostics.

The main risks are:
- All new Playwright framework files are currently untracked in Git.
- A Playwright example spec still exists and runs under role projects.
- The role/session project matching is too broad, so tests can execute under unintended projects.
- `LoginPage.ts` contains action logic, assertions, MAC diagnostics, network classification, and console listeners in one large class.
- TypeScript type-checking is not available because `typescript` is not installed.
- Several potentially sensitive or artifact files are tracked in Git, including `dashboard/.env.local`, `.env.wave1.example`, `merchant_state_seeds.env`, and old test artifacts.

Recommendation: Go for continued framework evolution, but No-Go for adding Patient/Reception flows until the immediate cleanup items are handled.

## 2. Current Architecture

Important top-level groups:

| Area | Role |
|---|---|
| `e2e/` | New Playwright TypeScript tests for 315 Healthcare. Contains setup, smoke, and one leftover Playwright sample spec. |
| `pages/` | Page Objects. Currently only `LoginPage.ts`. |
| `utils/` | Shared Playwright fixtures and role authentication helpers. |
| `test-data/` | Static TypeScript test metadata. Currently role code/name map. |
| `docs/` | Large existing documentation corpus for API regression, manual QA, mobile, SRS, findings, reports, and new 315 MAC precondition doc. |
| `playwright.config.ts` | Main Playwright config for the new TypeScript suite. |
| `package.json` | Node package metadata and Playwright/dotenv dependencies. No scripts yet. |
| `.env.example` | Public env template for BASE_URL, standalone login, and N13/N03/N02 role credentials. |
| `.gitignore` | Ignores `.env`, Playwright artifacts, auth state, node_modules, broad JSON artifacts, and local outputs. |

Important new Playwright files:

```text
e2e/
  example.spec.ts
  setup/
    N02.setup.ts
    N03.setup.ts
    N13.setup.ts
  smoke/
    login.spec.ts
    role-session.spec.ts
pages/
  LoginPage.ts
utils/
  auth-role.ts
  test.ts
test-data/
  roles.ts
```

The repository also contains a much larger Python-based AI/regression/manual-QA platform (`api/`, `core/`, `orchestrator/`, `scripts/`, `tests/`, `dashboard/`, `domains/`, `kb/`). That legacy platform is not structurally separated from the new 315 Playwright framework, which increases cognitive load and Git hygiene risk.

## 3. Existing Test Inventory

Playwright `--list` currently reports 19 test entries because the same spec files are collected under multiple projects.

| File | Test | Type | Notes |
|---|---|---|---|
| `e2e/setup/N13.setup.ts` | `authenticate N13` | setup | Creates `playwright/.auth/N13.json`. |
| `e2e/setup/N03.setup.ts` | `authenticate N03` | setup | Creates `playwright/.auth/N03.json`. |
| `e2e/setup/N02.setup.ts` | `authenticate N02` | setup | Creates `playwright/.auth/N02.json`. |
| `e2e/smoke/login.spec.ts` | `AUT-001 - Đăng nhập thành công` | smoke | Independent login test, explicitly clears storage state. |
| `e2e/smoke/role-session.spec.ts` | `Role session is authenticated` | smoke | Intended for role projects, skips non-role project at runtime. |
| `e2e/example.spec.ts` | `has title`, `get started link` | sample | Leftover Playwright sample against `playwright.dev`; should not be in official suite. |

Risk observations:
- `example.spec.ts` is not related to 315 and runs under `chromium`, `N13`, `N03`, and `N02`.
- `login.spec.ts` runs under role projects too, although it uses `storageState: undefined`.
- `role-session.spec.ts` is listed under `chromium` then skips at runtime; better to avoid collecting it for non-role projects.
- Test names are not consistently prefixed with automation IDs. `AUT-001` is good; setup and role-session names are generic.
- No tags exist yet, so targeted smoke/regression selection must rely on file paths/projects.

## 4. Configuration Review

Current config:
- `testDir: './e2e'`: correct for the new suite.
- Global timeout: not explicitly set, so Playwright default `30000ms`.
- Expect timeout: not explicitly set, so default `5000ms`.
- `fullyParallel: true`: acceptable for isolated tests, risky when storage-state setup and shared environment are involved.
- `forbidOnly: !!process.env.CI`: good.
- `retries: process.env.CI ? 2 : 0`: standard.
- `workers: process.env.CI ? 1 : undefined`: good for CI stability, local may run parallel by default.
- `reporter: 'html'`: fine locally, but CI should add `list` or `junit`.
- `use.baseURL: process.env.BASE_URL`: correct.
- `trace: 'on-first-retry'`: good.
- `screenshot: 'only-on-failure'`: good.
- `video: 'retain-on-failure'`: good, though storage cost should be monitored.
- `permissions: ['local-network-access']`: correct for Chromium local service access.
- Projects:
  - `chromium`
  - `setup-N13`, `setup-N03`, `setup-N02`
  - `N13`, `N03`, `N02` with storage state and setup dependencies.

Correct decisions:
- Only Chromium is used for now.
- Role projects depend on their own setup projects.
- Storage states use role code filenames.
- Local network access is granted both through config and origin-specific fixture.

Issues and risks:
- Setup projects use `testMatch`, but role projects have no `testIgnore` for setup files or example specs.
- Role projects will collect all normal specs in `e2e/`, including `example.spec.ts` and `login.spec.ts`.
- No CI reporter or web-friendly artifact path policy is defined for this suite.
- No explicit global timeout/expect timeout policy exists; current waits are a mix of defaults and local 30s logic.
- `fullyParallel: true` may create role setup contention later if many role session tests run at once.
- `package-lock.json` is ignored at root, which weakens reproducible Node installs.

Recommended config changes later:
- Add `testMatch`/`testIgnore` rules per project.
- Remove or ignore `e2e/example.spec.ts`.
- Add `reporter: [['list'], ['html'], ['junit', { outputFile: ... }]]` for CI.
- Add scripts for common project runs.
- Consider `fullyParallel: false` until role/session design matures, or scope parallelism by test type.

## 5. Authentication and Role Review

Files reviewed:
- `pages/LoginPage.ts`
- `utils/auth-role.ts`
- `utils/test.ts`
- `e2e/setup/*.setup.ts`
- `e2e/smoke/login.spec.ts`
- `e2e/smoke/role-session.spec.ts`
- `test-data/roles.ts`

Strengths:
- Setup files are thin and call shared `authenticateRole`.
- Credentials are read through env variables such as `N13_USERNAME`, `N13_PASSWORD`, `N13_COMPANY`, `N13_BRANCH`.
- No username/password values are hard-coded in TypeScript source.
- Diagnostics log booleans for credential presence, not secret values.
- Storage state path follows `playwright/.auth/<ROLE>.json`.
- `playwright/.auth/` is ignored.
- `login.spec.ts` uses `test.use({ storageState: undefined })`, so it remains a real login test.
- Roles are designed around role code identifiers, which is correct for 27-role expansion.

Risks:
- `auth-role.ts` logs company/branch. This is not a credential, but it may still be environment-sensitive. Acceptable for now.
- Storage state can contain auth tokens; Git ignore is correct, but generated `N13.json` exists locally and must remain untracked.
- Role projects are broad and can run tests not designed for that role.
- `role-session.spec.ts` reads role env again, which is acceptable, but a future fixture could expose `role` and `roleCredentials` more cleanly.
- No central env schema exists; env validation is split between `login.spec.ts`, `auth-role.ts`, and `utils/test.ts`.

Expandability:
- Adding a role requires edits in `test-data/roles.ts`, one setup file, env variables, and Playwright config. This is manageable for 3 roles but will become repetitive around 10+ roles.
- For 27 roles, generate setup/project definitions from a single role list rather than hand-writing all projects at once.

## 6. 315 MAC Address Integration Review

Current behavior:
- The framework does not mock `http://localhost:3153/system-info`.
- Chromium local network permission is configured using `local-network-access`.
- The custom fixture grants the permission for the origin derived from `BASE_URL`.
- `LoginPage.ts` tracks `system-info` requests by Playwright `Request` object, not by URL.
- Each MAC service request now has:
  - `requestNumber`
  - `startedAt`
  - method
  - URL
  - response status
  - CORS-related headers
  - `requestfinished`
  - elapsed time
  - request failure text

Recent evidence from setup N13:
- Request 1: HTTP 200, finished, elapsed about `1145ms`.
- Request 2: HTTP 200, finished, elapsed about `264ms`.
- Login moved from `/login` to `/`.

Strengths:
- The earlier false positive was fixed.
- Pending is no longer treated as service unavailable.
- CORS/PNA, network unavailable, HTTP error, pending, and success are separated.
- Response body is not logged, avoiding IP/MAC disclosure.

Risks:
- MAC service diagnostics are embedded directly in `LoginPage.ts`, making the Page Object too large and debug-heavy.
- Console/pageerror listeners are useful now but can create noisy logs in normal runs.
- There is no preflight test/helper to verify `system-info` before auth. A failed local service is discovered during login instead of before setup.
- CI will require a self-hosted runner with the 315 MAC Address app installed, local port `3153` reachable from Chromium, and permission behavior validated.

Recommended next step:
- Extract MAC service tracking to `utils/mac-service-diagnostics.ts` or a fixture.
- Add a non-auth precondition test under `e2e/environment/mac-address.precondition.ts` that verifies browser-level access to `system-info` without logging the body.

## 7. Code Quality Findings

Page Object review:
- Locators use roles and text, no long XPath found.
- No `waitForTimeout` found in the new `e2e/pages/utils/test-data` Playwright code.
- `LoginPage.login()` performs action and validation, which is acceptable for a smoke helper but less clean for long-term Page Object design.
- `LoginPage.ts` is too large for a single login page object at about 17KB.
- Diagnostic/network classification logic should not live permanently in the page object.
- `getByText(branch, { exact: true })` can be flaky if the branch appears in multiple places or disappears after layout changes.
- `role-session.spec.ts` only asserts role name if text exists, which makes role validation optional and can hide missing role display.
- `neverResolve`/`Promise.race` is functional but non-obvious; it needs either comments or extraction.
- `utils/test.ts` auto-grants local network permission for every test using the fixture. This is convenient, but all tests using that fixture will carry auth-environment assumptions.

## 8. Test Quality Findings

Current test quality:
- Setup tests have no explicit assertions, but `authenticateRole` asserts login success and storage state is saved after success. Acceptable.
- `login.spec.ts` has clear steps and validates URL plus branch.
- `role-session.spec.ts` checks URL and branch, but role name check is optional.
- Test tags are absent.
- Sample tests are unrelated and should be removed or ignored later.
- Role/session tests are environment-dependent and require real credentials and MAC service.

Flakiness risks:
- Dynamic MUI combobox behavior can detach/re-render. Current `toBe` polling on display value helps.
- Branch assertion by exact text may fail if UI uses shortened labels or different placement.
- Local network permission and MAC app are machine-specific, so CI requires careful runner setup.
- Mixed content console errors after login were observed for `http://ip-api.com/json`, but did not block setup N13.

## 9. Security and Secret Review

Rules followed during audit:
- `.env` content was not read or printed.
- Only env variable names and existence were considered.

Env variables in `.env.example`:
- `BASE_URL`
- `TEST_USERNAME`, `TEST_PASSWORD`, `TEST_COMPANY`, `TEST_BRANCH`
- `N13_USERNAME`, `N13_PASSWORD`, `N13_COMPANY`, `N13_BRANCH`
- `N03_USERNAME`, `N03_PASSWORD`, `N03_COMPANY`, `N03_BRANCH`
- `N02_USERNAME`, `N02_PASSWORD`, `N02_COMPANY`, `N02_BRANCH`

Issues:
- `.env.example` currently contains only 315 Playwright variables. It replaced earlier API env template content, which may be a repo-wide breaking change if legacy scripts depended on `.env.example`.
- `.env.*` is ignored, then `!.env.example` is unignored. Good.
- `dashboard/.env.local` is tracked. This is a high-risk pattern even if contents are harmless.
- `merchant_state_seeds.env` is tracked. It may contain seed/runtime env data and should be reviewed.
- `.env.wave1.example` is tracked. It is an example, but should be reviewed for accidental secrets.
- Generated storage state `playwright/.auth/N13.json` exists locally but is ignored.

Recommendation:
- Add a secret scanning step before any commit.
- Review tracked env-like files without printing secrets in public logs.
- Split examples: `.env.315.example` and `.env.api.example`, or clearly document ownership.

## 10. Git and Repository Health

Branch:
- `main`

Working tree:
- Dirty.
- Modified: `.env.example`, `.gitignore`
- Untracked: `docs/PLAYWRIGHT_AUTH_PRECONDITIONS.md`, `e2e/**`, `pages/**`, `playwright.config.ts`, `test-data/**`, `utils/**`

Tracked sensitive/artifact-risk paths reported by `git ls-files`:
- `.env.example`
- `.env.wave1.example`
- `dashboard/.env.local`
- `merchant_state_seeds.env`
- `artifacts/test-results/api-regression/README.md`
- `artifacts/test-results/ui-e2e/test-output/admin_e2e-ADMIN-E2E-001-login-success/error-context.md`
- `tests/ui_smoke/package-lock.json`

Commit history:
- Recent commits are regular feature commits around manual QA phases.
- No commit/reset/push was performed during this audit.

Repository risk:
- The new Playwright framework is not tracked yet, so it can be lost or omitted from PRs.
- Some ignored files are intentionally or accidentally tracked already; `.gitignore` does not affect files already in Git.

## 11. Documentation Review

Docs are extensive but mostly about the broader AI/manual QA/API regression platform.

Existing relevant docs:
- `docs/PLAYWRIGHT_AUTH_PRECONDITIONS.md`: covers 315 MAC Address precondition.
- `docs/UI_SMOKE_PLAN.md`: older generic UI smoke plan using `API_USER/API_PASS`.
- `docs/UI_E2E_PLAN.md`: older admin UI plan targeting `http://192.168.1.7:19068/en/login`.
- `docs/TEST_STRATEGY.md`: broad test strategy for legacy runners.
- `docs/KNOWN_BLOCKERS.md`, `docs/FUNCTIONAL_MODULES.md`, `docs/API_REGRESSION_PLAN.md`: useful but not specific to current 315 Playwright TS role framework.

Missing docs:
- Installation guide for the new Playwright TypeScript suite.
- `.env` setup guide for N13/N03/N02.
- Role model guide and how to add a role.
- Running tests by project and by smoke/regression intent.
- Debugging guide for local-network-access and 315 MAC Address.
- CI/self-hosted runner setup guide.
- Artifact/report usage guide for HTML report, trace, screenshot, video.

## 12. Findings Table

| ID | Severity | Area | File(s) | Description | Risk | Recommendation | Fix now? |
|---|---|---|---|---|---|---|---|
| AUD-001 | High | Git | `e2e/**`, `pages/**`, `utils/**`, `playwright.config.ts`, `test-data/**` | New Playwright framework files are untracked. | Official framework may not be committed or reviewed. | Stage/review these files intentionally in the next implementation turn. | Yes |
| AUD-002 | High | Security | `dashboard/.env.local`, `merchant_state_seeds.env` | Env-like files are tracked. | Secret leakage or unsafe config history. | Review contents locally, rotate secrets if needed, remove from Git history if sensitive. | Yes |
| AUD-003 | High | Test Selection | `playwright.config.ts`, `e2e/example.spec.ts` | Sample tests are collected across all projects. | Role projects run irrelevant tests and setups. | Remove or ignore `example.spec.ts`; add project-specific `testMatch`/`testIgnore`. | Yes |
| AUD-004 | High | Test Selection | `playwright.config.ts`, `e2e/smoke/login.spec.ts` | Independent login spec is collected by role projects. | Wasted setup and confusing test matrix. | Restrict `chromium` to standalone smoke or tag/filter projects. | Yes |
| AUD-005 | Medium | Page Object | `pages/LoginPage.ts` | Page Object contains MAC diagnostics, network tracking, action, assertion, and error classification. | Harder maintenance and reuse. | Extract diagnostics/preconditions into helper or fixture. | Soon |
| AUD-006 | Medium | TypeScript | `package.json` | `typescript` is not installed; `npx tsc --noEmit` cannot run. | No reliable type-check gate. | Add `typescript`, `tsconfig.json`, and `typecheck` script. | Yes |
| AUD-007 | Medium | Package | `package.json` | No npm scripts. | Commands are tribal knowledge and harder for CI. | Add `test:smoke`, `test:N13`, `test:headed`, `report`, `typecheck`. | Yes |
| AUD-008 | Medium | CI | `playwright.config.ts`, docs | CI needs self-hosted runner with 315 MAC Address app and local network permission. | Cloud CI will fail auth setup. | Document self-hosted runner requirements and preflight. | Yes |
| AUD-009 | Medium | Env | `.env.example` | 315-only env example may have overwritten broader API env guidance. | Legacy scripts/users may lose reference variables. | Split or restore multiple example files by subsystem. | Soon |
| AUD-010 | Medium | Auth | `role-session.spec.ts` | Role text assertion is optional. | Missing role display may not fail. | Decide whether role text is a contract; if yes, assert mandatory per role. | Soon |
| AUD-011 | Medium | Diagnostics | `pages/LoginPage.ts` | Console/pageerror listeners can be noisy in every auth run. | Harder log triage; potential performance/noise issue. | Gate verbose diagnostics with env flag after stabilization. | Later |
| AUD-012 | Low | Naming | `e2e/setup/*.setup.ts`, `role-session.spec.ts` | Test names lack standardized IDs/tags. | Reporting less traceable. | Add IDs/tags such as `@setup`, `@smoke`, `AUT-ROLE-001`. | Soon |
| AUD-013 | Low | Git Ignore | `.gitignore` | Root `package-lock.json` ignored. | Non-reproducible npm installs for official framework. | Track root lockfile or intentionally document why not. | Soon |
| AUD-014 | Low | Docs | `docs/` | Many legacy docs; new 315 Playwright docs are thin. | Onboarding friction. | Add concise `docs/PLAYWRIGHT_315_GUIDE.md`. | Soon |
| AUD-015 | Low | Runtime | Post-login console | Mixed content error for `http://ip-api.com/json` observed after login. | Could become future flake if UI depends on it. | Track as app-side observation; not a blocker for setup. | Later |

## 13. Recommended Target Structure

Do not create all of this during audit. This is the next-phase target:

```text
e2e/
  environment/
    mac-address.precondition.ts
    app-health.spec.ts
  setup/
    N13.setup.ts
    N03.setup.ts
    N02.setup.ts
  smoke/
    login.spec.ts
    role-session.spec.ts
  critical-flows/
    reception/
    patient/
  regression/
    reception/
    patient/
pages/
  LoginPage.ts
  components/
    AppHeader.ts
    BranchSelector.ts
fixtures/
  base.ts
  role-fixtures.ts
utils/
  auth-role.ts
  env.ts
  mac-service-diagnostics.ts
  storage-state.ts
test-data/
  roles.ts
  environments.ts
docs/
  PLAYWRIGHT_315_GUIDE.md
  PLAYWRIGHT_AUTH_PRECONDITIONS.md
  ROLE_AUTH_GUIDE.md
  CI_SELF_HOSTED_RUNNER_GUIDE.md
```

## 14. Prioritized Action Plan

Before writing Patient/Reception tests:
1. Remove/ignore `e2e/example.spec.ts`.
2. Restrict project test matching so role projects only run intended specs.
3. Add `typescript`, `tsconfig.json`, and `npm run typecheck`.
4. Add npm scripts for common Playwright commands.
5. Review tracked env-like files for secrets.
6. Extract MAC diagnostics or at least mark them as temporary debug code.

This week:
1. Add `docs/PLAYWRIGHT_315_GUIDE.md` with setup, env, roles, MAC app, and commands.
2. Add `utils/env.ts` with typed env validation.
3. Add a browser-level MAC precondition test under `e2e/environment`.
4. Add test tags and IDs.
5. Decide whether role text must be mandatory in `role-session.spec.ts`.

After 10-15 smoke tests:
1. Introduce fixtures for authenticated role pages.
2. Split Page Objects by domain and shared components.
3. Add critical-flow and regression layering.
4. Introduce non-destructive data strategy for patient/reception workflows.
5. Add reporting conventions and trace review workflow.

For CI/self-hosted runner:
1. Use a Windows self-hosted runner with 315 MAC Address installed and started.
2. Add preflight check for `localhost:3153/system-info` from Chromium.
3. Add secure secret storage for role credentials.
4. Add CI reporters and artifact retention.
5. Run setup projects explicitly before smoke role projects, or rely on Playwright dependencies after project selection is corrected.

## 15. Go/No-Go Recommendation for Patient/Reception Automation

Recommendation: Conditional Go.

The project is good enough to continue, but Patient/Reception automation should not start until the immediate blockers are addressed:
- Commit/review the Playwright framework files.
- Remove sample tests from official project collection.
- Fix project matching so tests cannot run under unintended roles.
- Add type-checking.
- Review tracked env-like files.

There is no need to create a new project. The right move is a small hardening pass in this repo, followed by Patient/Reception flows under `e2e/critical-flows` or `e2e/smoke` depending on risk.

## Commands Run During Audit

```powershell
rg --files -g '!node_modules/**' -g '!test-results/**' -g '!playwright-report/**' -g '!artifacts/**' -g '!outputs/**' -g '!dashboard/.next/**' -g '!*.pyc'
git status --short --branch
git status --short --untracked-files=all
git diff --stat
npx.cmd playwright test --list
npx.cmd tsc --noEmit
npm.cmd audit --omit=dev
git branch --show-current
git ls-files | Select-String -Pattern '(^|/)(\.env$|\.env\.|.*\.env$|playwright/\.auth|test-results|playwright-report|node_modules|\.webm$|\.png$|trace\.zip$|storageState|auth.*\.json|package-lock\.json)'
git log --oneline -5
rg -n "waitForTimeout|xpath=|//|getByRole|getByLabel|getByTestId|storageState|grantPermissions|local-network-access|system-info|console\.log|password|token" e2e pages utils test-data playwright.config.ts .env.example .gitignore
```

Results:
- `npx.cmd playwright test --list`: passed; 19 tests listed.
- `npx.cmd tsc --noEmit`: failed because TypeScript compiler is not installed; npm warned about unsupported `tsc@2.0.4`.
- `npm.cmd audit --omit=dev`: passed; 0 vulnerabilities.
- No destructive tests or data-writing business flows were run.

