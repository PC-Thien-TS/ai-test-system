# UAT Feature Execution Findings (2026-03-20)

## Evidence
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `artifacts/test-results/api-regression/api_regression.log`

## Latest Run Snapshot
- `total=166`
- `passed=65`
- `failed=7`
- `skipped=94`

## Newly Registered Coverage (this phase)
- Order creation depth: `ORD-API-021..029`
- Customer action extension: `ORD-CUS-004`
- Merchant detail: `MORD-API-008`
- Admin disputes: `AORD-API-005..008`
- Add-on checks: `ORD-ADDON-001..002`
- Runtime caveat trackers: `ORD-JOB-001..004`, `ORD-CAVEAT-001..004`

## Confirmed Backend Defects (still FAIL)
- `STO-009` invalid store id returns `500`
- `STO-011` invalid unique id returns `500`
- `STO-012` store collections returns `500`
- `ORD-API-014` invalid `storeId` returns `500`
- `ORD-API-015` missing `storeId` returns `500`
- `MEMBER-001` member list mapping/config returns `500`
- `STCATADM-004` invalid store-category detail id returns `500`

## Non-defect Blockers

### Config/Auth blockers
- `AUTH-001` currently returns `400 Incorrect email or password`.
- Customer-token-dependent modules (`ORD-*`, `ORG-*`, `NOTI-*`) are largely skipped with explicit seed or config blockers.
- Merchant login also returns `400 Incorrect email or password` in this run, so merchant lifecycle remains scope/config blocked.

### Seed blockers
- `STO-010` still lacks deterministic valid uniqueId seed.
- `NEWS-003` remains blocked due empty list seed for slug.
- Cross-store and store-gating seeds remain unresolved:
  - `ORD-API-008`, `ORD-API-017`, `ORD-API-018`, `ORD-API-019`

### Runtime contract/config blockers
- Notification event correlation and job-window assertions remain non-deterministic:
  - `NOTI-ORD-*`
  - `ORD-JOB-*`
  - `ORD-CAVEAT-*`

## UAT Mapping Implication
- Admin read/reporting modules are relatively stable when admin token is valid.
- Customer and merchant critical UAT flows are currently blocked by runtime auth availability, not by missing test registration.
- Added cases are now traceable and ready to execute once auth and seeds are restored.

## Next Actions
1. Restore deterministic customer and merchant credentials for `192.168.1.103`.
2. Re-run regression to convert `ORD-API-021..029`, `MORD-API-008`, and `ORD-ADDON-*` from blocked to executable.
3. Keep backend-defect assertions unchanged until server behavior changes with evidence.

