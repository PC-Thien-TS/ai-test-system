# Order Execution Findings (2026-03-20)

## Evidence
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.log`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `scripts/run_api_regression.ps1`
- `tests/api/order/order_api_critical_cases.json`

## Latest full regression summary
- Total: `166`
- Passed: `131`
- Failed: `7`
- Skipped: `28`

## Scenario-refactor status
- Runner now uses journey-owned order setup instead of single-order reuse:
  - `J2-Payment`, `J3-CustomerAction`, `J5-Merchant` each creates its own order.
- Cross-branch state pollution is reduced:
  - customer-cancel flow no longer drives merchant accept/complete checks on the same order.
- Admin list/detail checks now consume scenario-created orders with deterministic list scan.

## What is now proven
- Customer create/detail/history:
  - `ORD-API-001`, `ORD-API-004`, `ORD-API-009` -> `PASS`
- Payment path and guards:
  - `ORD-PAY-001..008` -> `PASS`
- Customer actions:
  - `ORD-CUS-001..004` -> `PASS` with controlled statuses
- Merchant visibility:
  - `MORD-API-005`, `MORD-API-008` -> `PASS`
- Admin monitoring/support:
  - `AORD-API-001..004`, `AORD-OPS-001..002` -> `PASS`

## Remaining fails (true defects in this run)
- `STO-009` -> `500` on invalid numeric store id
- `STO-011` -> `500` on invalid uniqueId path
- `ORD-API-014` -> `500` on invalid `storeId`
- `ORD-API-015` -> `500` on missing/zero `storeId`
- `ORD-API-022` -> `200` accepted for past `arrivalTime` (expected controlled reject)
- `MEMBER-001` -> `500` mapping/config error
- `STCATADM-004` -> `500` on invalid store-category id

## Remaining blocked/skipped areas
- Seed blockers:
  - `STO-010`
  - `ORD-API-008`, `ORD-API-017`, `ORD-API-019`
  - `NEWS-003`
- Runtime-contract/config blockers:
  - `ORD-API-018`
  - `ORD-CAN-004`
  - `NOTI-ORD-002/003/006`
  - `ORD-JOB-*`, `ORD-CAVEAT-001/003/004`
- Scope blockers:
  - `NOTI-ORD-004/005`
  - `ORD-CAVEAT-002`

## Interpretation
- The suite is now materially closer to manual-proven runtime journeys.
- Defect visibility is preserved; no known `500` defect expectation was weakened.
- Further skip reduction now depends on deterministic second-store/notification seeds and deeper merchant lifecycle orchestration where `accept=200` can be proven.
