# Framework Hardening Report

Date: 2026-07-23  
Scope: Playwright + TypeScript framework hardening before Patient/Reception automation.

## Files Changed

Created:
- `tsconfig.json`
- `docs/FRAMEWORK_HARDENING_REPORT.md`

Modified:
- `playwright.config.ts`
- `package.json`
- `package-lock.json`
- `.gitignore`
- `pages/LoginPage.ts`
- `e2e/smoke/role-session.spec.ts`

Removed from filesystem:
- `e2e/example.spec.ts`

Notes:
- No commit, push, reset, checkout, or Git history rewrite was performed.
- `.env` was not read or printed.
- No credential values were added to scripts or source.

## Project Matching Before/After

Before:
- `chromium` collected every test under `e2e`.
- `N13`, `N03`, and `N02` collected all normal specs under `e2e`, including `example.spec.ts` and `login.spec.ts`.
- `role-session.spec.ts` was also collected by `chromium` and skipped at runtime.
- `example.spec.ts` produced unrelated `playwright.dev` tests across projects.

After:
- `setup-N13` collects only `e2e/setup/N13.setup.ts`.
- `setup-N03` collects only `e2e/setup/N03.setup.ts`.
- `setup-N02` collects only `e2e/setup/N02.setup.ts`.
- `chromium` collects only:
  - `e2e/smoke/login.spec.ts`
  - future `e2e/environment/**/*.spec.ts`
- `N13`, `N03`, and `N02` collect:
  - `e2e/smoke/role-session.spec.ts`
  - future `e2e/critical-flows/**/*.spec.ts`
  - future `e2e/regression/**/*.spec.ts`
- Role projects ignore:
  - `e2e/setup/**`
  - `e2e/smoke/login.spec.ts`
- `e2e/example.spec.ts` is removed and no longer appears in test inventory.

## TypeScript Setup

Installed:
- `typescript` as a dev dependency.

Added `tsconfig.json` for Playwright + Node:
- `strict: true`
- `noEmit: true`
- `esModuleInterop: true`
- `module: NodeNext`
- `moduleResolution: NodeNext`
- `types: ["node", "@playwright/test"]`

Included:
- `e2e/**/*.ts`
- `pages/**/*.ts`
- `utils/**/*.ts`
- `test-data/**/*.ts`
- `playwright.config.ts`

Excluded:
- `node_modules`
- `playwright-report`
- `test-results`
- `artifacts`
- `dashboard/.next`

Small TypeScript-only fix:
- `pages/LoginPage.ts` changed `waitForLoginErrors()` matcher typing from `toSatisfy` to polling message count.
- `neverResolve()` now returns `Promise<never>` to avoid widening the result union.

No login behavior was intentionally changed.

## npm Scripts

Added:

```json
{
  "typecheck": "tsc --noEmit",
  "test:list": "playwright test --list",
  "test:login": "playwright test e2e/smoke/login.spec.ts --project=chromium",
  "test:N13": "playwright test e2e/smoke/role-session.spec.ts --project=N13",
  "test:N03": "playwright test e2e/smoke/role-session.spec.ts --project=N03",
  "test:N02": "playwright test e2e/smoke/role-session.spec.ts --project=N02",
  "test:headed": "playwright test --headed",
  "test:debug": "playwright test --debug",
  "report": "playwright show-report"
}
```

No credentials are embedded in scripts.

## package-lock Policy

Finding:
- Root `package-lock.json` was effectively ignored by broad ignore patterns.
- The project is now treated as an official Node/Playwright framework, so reproducible installs matter.

Change:
- `.gitignore` now keeps broad JSON artifact ignores but explicitly unignores:
  - `/package.json`
  - `/package-lock.json`
  - `/tsconfig.json`

Subproject package-lock files were not deleted or changed by policy. Existing tracked subproject files remain a separate repository hygiene decision.

## Git Risk Review

Checked with `git ls-files` only; sensitive file contents were not printed.

| File | Tracked? | Risk Type | Recommendation |
|---|---:|---|---|
| `dashboard/.env.local` | Yes | Possible local secret/config file | Review manually; remove from tracking if sensitive. |
| `merchant_state_seeds.env` | Yes | Env-like seed/runtime data | Review manually; rename to example or remove from tracking if sensitive. |
| `.env.wave1.example` | Yes | Example env file | Keep only if verified as placeholder-only; otherwise sanitize. |
| `artifacts/test-results/api-regression/README.md` | Yes | Artifact path tracked | Keep only if intentional documentation; otherwise move under docs or remove tracking. |
| `artifacts/test-results/ui-e2e/test-output/admin_e2e-ADMIN-E2E-001-login-success/error-context.md` | Yes | Test artifact tracked | Remove from tracking in a dedicated cleanup. |

No `git rm`, secret rotation, or history rewrite was performed.

## Commands Run

```powershell
git status --short --branch
git diff --stat
npm.cmd install --save-dev typescript
npm.cmd run typecheck
npm.cmd run test:list
npx.cmd playwright test e2e/smoke/login.spec.ts --project=chromium --list
npx.cmd playwright test e2e/smoke/role-session.spec.ts --project=N13 --list
npx.cmd playwright test --list
git ls-files dashboard/.env.local merchant_state_seeds.env .env.wave1.example artifacts/test-results/api-regression/README.md artifacts/test-results/ui-e2e/test-output/admin_e2e-ADMIN-E2E-001-login-success/error-context.md
git check-ignore -v package.json package-lock.json tsconfig.json tests/ui_smoke/package-lock.json
git status --short --untracked-files=all
```

Results:
- `npm.cmd run typecheck`: passed.
- `npm.cmd run test:list`: passed.
- `npx.cmd playwright test e2e/smoke/login.spec.ts --project=chromium --list`: passed.
- `npx.cmd playwright test e2e/smoke/role-session.spec.ts --project=N13 --list`: passed.
- `npx.cmd playwright test --list`: passed.

No Patient/Reception test and no destructive workflow was run.

## Test Inventory After Hardening

Total listed entries: 7 tests in 5 files.

```text
[setup-N02] setup/N02.setup.ts -> authenticate N02
[setup-N03] setup/N03.setup.ts -> authenticate N03
[setup-N13] setup/N13.setup.ts -> authenticate N13
[chromium] smoke/login.spec.ts -> AUT-001 - Đăng nhập thành công
[N13] smoke/role-session.spec.ts -> AUT-002 - Sử dụng lại phiên đăng nhập theo vai trò @smoke @auth
[N03] smoke/role-session.spec.ts -> AUT-002 - Sử dụng lại phiên đăng nhập theo vai trò @smoke @auth
[N02] smoke/role-session.spec.ts -> AUT-002 - Sử dụng lại phiên đăng nhập theo vai trò @smoke @auth
```

Checks:
- `example.spec.ts`: removed; no longer listed.
- `login.spec.ts`: listed only under `chromium`.
- `role-session.spec.ts`: listed under role projects only. When listing `--project=N13`, Playwright also lists `setup-N13` because it is a project dependency, which is expected.
- Setup files: each setup file is collected only by its matching setup project.

## Remaining Risks

- Playwright framework files are still untracked until intentionally staged/committed.
- Tracked env-like and artifact files need a separate cleanup decision.
- `LoginPage.ts` remains large and includes diagnostics; this was intentionally not refactored in this hardening pass.
- CI still requires a self-hosted runner with 315 MAC Address available and browser local network access working.
- Tags are currently embedded in the test title. If the team wants Playwright's structured tag API later, update after confirming the preferred version and reporter conventions.

## Go/No-Go for Patient/Reception

Recommendation: Go after Git review/staging and env-risk review.

The blocking framework issues from the audit are mostly addressed:
- Sample test removed.
- Project matching hardened.
- TypeScript typecheck added and passing.
- npm scripts added.
- Root package lock can now be tracked.

Remaining non-code blockers are repository hygiene items:
- Review tracked env-like files.
- Intentionally add the new framework files to Git in a controlled commit/PR.

