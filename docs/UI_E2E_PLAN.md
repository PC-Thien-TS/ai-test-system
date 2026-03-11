# UI E2E Plan

## Objective
Run a focused, safe Playwright end-to-end suite for the admin web at `http://192.168.1.7:19068/en/login` without modifying production code.

## Scope
- login success
- dashboard load
- sidebar navigation
- organization page access
- simple organization interaction
- notification page access
- logout

## Safety Rules
- No destructive write flows.
- No create, update, or delete business actions.
- If a route, selector, or control is not stable in the deployed UI, the test is marked `SKIPPED` instead of forcing brittle logic.

## Credentials And URL
- `BASE_URL`
  - optional
  - default: `http://192.168.1.7:19068`
- `API_USER`
  - required
- `API_PASS`
  - required
- `UI_LOGIN_PATH`
  - optional
  - default: `/en/login`

## Covered Flows
1. Login with valid credentials from the localized login page.
2. Dashboard renders after login and does not show fatal error content.
3. Sidebar navigation can open organization and return to dashboard when the links are exposed.
4. Organization page can be opened via sidebar or direct route fallback.
5. Organization search interaction is exercised when the search input is stable.
6. Notification page can be opened via admin notification routes or direct route fallback.
7. Logout returns the session to a login URL when the user menu and logout control are stable.

## Execution
- PowerShell:
  - `.\scripts\run_ui_e2e.ps1`
- CMD:
  - `scripts\run_ui_e2e.cmd`

Example:

```powershell
$env:BASE_URL = "http://192.168.1.7:19068"
$env:API_USER = "your_user"
$env:API_PASS = "your_pass"
.\scripts\run_ui_e2e.ps1
```

## Outputs
Artifacts are written under `artifacts/test-results/ui-e2e/`:
- `ui_e2e.log`
- `ui_e2e.summary.json`
- `playwright-report.json`
- `playwright-junit.xml`
- `test-output/`
  - screenshots on failure
  - traces on failure

## Known Limitations
- The deployed admin UI may expose notification functionality through `notification-template` or `notification-policy` rather than a generic `notification` route.
- Some controls depend on authenticated role visibility. Missing admin links are treated as `SKIPPED`, not `FAILED`.
- The suite assumes the target environment is reachable from the test runner machine.
