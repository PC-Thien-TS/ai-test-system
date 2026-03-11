# UI Smoke Plan

## Objective
Run a safe, non-destructive UI smoke pass for currently validated user-facing modules, aligned with API regression coverage.

## Scope
- auth
- search
- store
- posts
- news
- organization
- notification

## Assumptions
- UI base URL is provided via `BASE_URL`.
- Optional credentials (`API_USER`, `API_PASS`) are available for auth-required UI checks.
- Route structures may vary by deployment, so tests use route candidates and skip when routes are not inferable.
- Tests must avoid destructive actions.

## Routes Under Test
- Auth candidates: `/login`, `/auth/login`, `/signin`, `/dang-nhap`
- Search candidates: `/search`, `/searches`, `/tim-kiem`
- Store candidates: `/store`, `/stores`, `/merchant`, `/merchants`
- Posts candidates: `/posts`, `/newsfeed`, `/feed`
- News candidates: `/news`, `/tin-tuc`
- Organization candidates: `/organization`, `/profile`, `/account`, `/me`
- Notification candidates: `/notification`, `/notifications`, `/thong-bao`

## Execution
1. Set environment variables:
   - Required: `BASE_URL`
   - Optional: `API_BASE_URL`, `API_USER`, `API_PASS`
2. Run:
   - PowerShell: `.\scripts\run_ui_smoke.ps1`
   - CMD: `scripts\run_ui_smoke.cmd`
3. Runner installs Playwright dependencies (if missing), runs smoke tests, and writes artifacts.

## Outputs
Under `artifacts/test-results/ui-smoke/`:
- `ui_smoke.log`
- `ui_smoke.summary.json`
- `playwright-report.json`
- `playwright-junit.xml`
- `test-output/` (screenshots/traces on failure)

## Coverage Notes
- Auth:
  - login success
  - login failure
  - logout when UI exposes a logout control
- Search:
  - open search page
  - search by keyword
  - suggestions/history check when exposed
- Store:
  - open list
  - open one detail when link is inferable
- Posts:
  - open posts/newsfeed
  - validate categories/recommend sections when inferable
- News:
  - open list
  - open detail when inferable
- Organization:
  - open organization/profile/info when inferable
- Notification:
  - open notification page
  - validate unread/list indicators when inferable

## Known Limitations
- Dynamic front-end route naming can differ between environments.
- Some checks may be reported as `SKIPPED` if routes/elements are not inferable safely.
- Auth tests may be skipped when credentials are missing.
