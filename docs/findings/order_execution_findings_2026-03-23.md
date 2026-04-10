# Order Execution Findings (2026-03-23)

## Evidence used
- `artifacts/test-results/api-regression/api_regression.log`
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `scripts/run_api_regression.ps1`
- `scripts/run_api_seed_precheck.ps1`

## Live runs executed today
- Seed precheck (host `192.168.1.103`):
  - `customer_login`: `400 Incorrect email or password`
  - `merchant_login`: `400 Incorrect email or password`
  - `admin_login`: `200`
  - `store_exists`: blocked (`401`) because customer token is unavailable
  - `admin_scope_orders/category_admin/dashboard`: `PASS`
  - `admin_scope_member`: blocked (`500` mapping defect)
- Full regression (while host was reachable):
  - `total=166`
  - `passed=65`
  - `failed=7`
  - `skipped=94`
- Focus runs:
  - `CORE`: `total=109`, `passed=64`, `failed=7`, `skipped=38`
  - `JOURNEYS`: `total=33`, `passed=1`, `failed=0`, `skipped=32`

## Mission target check (2026-03-23)
- Target: `CORE` only known defects as fail, `JOURNEYS` `0 FAIL` and `<=2 SKIP`, at least one merchant happy path `accept -> arrived -> complete`.
- Actual:
  - `JOURNEYS` fail target is met (`0 FAIL`).
  - Skip target is not met (`32` skips) due runtime auth blocker (`API_USER` and `API_MERCHANT_USER` credentials rejected).
  - Merchant happy path is not executable because merchant login is blocked, then runtime host became unreachable during follow-up probes.

## Code change completed today
- `scripts/run_api_regression.ps1`
  - `AORD-API-003` admin list visibility query was hardened:
    - added bounded multi-page deterministic scan (`pageSize=50`, page walk up to `lastPage` with cap `50`).
    - keeps explicit query-attempt notes.
    - reduces false `QUERY_BLOCKER` when target order exists but is not in early pages.

## Classification updates
- `ORD-API-022`:
  - Current runner classification logic is `CONTRACT_REVIEW` when runtime accepts past `arrivalTime` with `200`.
  - In today run it remained `SKIPPED` because customer auth was unavailable.
  - Final state: keep as `partial / contract-review` until customer-scope execution is restored.

## Confirmed backend defects still visible
- `STO-009`
- `STO-011`
- `STO-012`
- `ORD-API-014`
- `ORD-API-015`
- `MEMBER-001`
- `STCATADM-004`

## New blocker found during execution window
- Runtime host availability instability after the successful regression window:
  - `192.168.1.103:19066` became unreachable (`DestinationHostUnreachable`) during additional merchant-scope probes.

## Next actions
1. Restore a valid customer credential (`API_USER`/`API_PASS`) and merchant credential (`API_MERCHANT_USER`/`API_MERCHANT_PASS`) for the current host.
2. Re-run `JOURNEYS` first and verify skip collapse from auth-driven blockers.
3. Re-test `AORD-API-003` after host recovery to confirm paging hardening changed `QUERY_BLOCKER` to `PASS`.
4. Re-run merchant sequence (`MORD-API-001 -> 003 -> 004`) on a merchant-visible order once merchant auth is restored.
