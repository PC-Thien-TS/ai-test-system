# Order Execution Findings (2026-03-19)

## Evidence
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `artifacts/test-results/api-regression/api_regression.log`
- `test-assets/seeds/order/order_seed.json`

## Run summary
- Total: `134`
- Passed: `102`
- Failed: `7`
- Skipped: `25`

## What was improved today
- `STO-010` false-pass path was removed:
  - Numeric `/store/{id}` responses are no longer accepted as uniqueId proof.
  - Additional probe now checks `/store/{id}?UniqueId=<invalid>`; when that still returns `200`, the case is kept `SEED_BLOCKER`.
- Completed-order seed diagnosis was tightened:
  - Runner now probes admin order list for completed-like candidates and verifies customer-scope visibility.
  - `ORD-CAN-003` now reports explicit `SCOPE_BLOCKER` evidence with candidate ids and `FORBIDDEN_SCOPE` checks.

## Current order outcomes
- Covered/passing:
  - `ORD-API-001`, `ORD-API-002`, `ORD-API-003`, `ORD-API-004`, `ORD-API-005`
  - `ORD-API-009`, `ORD-API-010..013`, `ORD-API-016`, `ORD-API-020`
  - `ORD-CAN-001`
  - `AORD-API-001..004`, `AORD-OPS-001..002`
- Blocked/skipped:
  - `MORD-API-001..005` and `MORD-003` (`SCOPE_BLOCKER`)
  - `ORD-API-008`, `ORD-API-017`, `ORD-API-019` (`SEED_BLOCKER`)
  - `ORD-API-018` (`RUNTIME_CONTRACT_CONFIG_BLOCKER`)
  - `ORD-CAN-002` (`RUNTIME_CONTRACT_CONFIG_BLOCKER`)
  - `ORD-CAN-003`, `ORD-CAN-004` (`SCOPE_BLOCKER`)
  - `NOTI-ORD-001..006` (seed/scope/runtime blockers)

## Order-specific blockers confirmed
1. Merchant ownership scope is still not aligned:
   - merchant list deterministic scan does not include created order id.
2. UniqueId runtime seed remains unresolved:
   - explicit GUID-like value fails not-found.
   - numeric id path is accepted as id route and cannot be used as uniqueId proof.
3. No deterministic second store with active orderable sku found in current scope.
4. No deterministic customer-scope completed order available for cancellation timeline assertions.

## Backend defects still visible during order-focused run
- `ORD-API-014` invalid store create-order path returns `500`.
- `ORD-API-015` missing/invalid store create-order path returns `500`.
- Store/member/admin-category defects remain active in same run (`STO-009`, `STO-011`, `STO-012`, `MEMBER-001`, `STCATADM-004`).
