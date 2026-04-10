# Order Execution Findings (2026-03-18)

## Evidence
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `artifacts/test-results/api-regression/api_regression.log`

## Run snapshot
- Total: `134`
- Passed: `107`
- Failed: `6`
- Skipped: `21`

## Newly unlocked today
- `ORD-PAY-005` now executable and `PASS` (`400 ORDER_INVALID_STATE`) with discovered `paidOrderId=50`.
- `ORD-PAY-006` now executable and `PASS` (`400 ORDER_INVALID_STATE`) with discovered `cancelledOrderId=43`.
- `ORD-CAN-002` now executable and `PASS` (`400 DISPUTE_WINDOW_CLOSED`) using paid-order seed.

## Current backend defects (still FAIL)
- `STO-009` invalid numeric store id returns `500` (expected `400/404`).
- `STO-011` invalid store uniqueId returns `500` (expected `400/404`).
- `ORD-API-014` invalid `storeId` in create-order returns `500` (expected `400/404/422`).
- `ORD-API-015` missing/invalid `storeId` in create-order returns `500` (expected `400/422`).
- `MEMBER-001` member list returns `500` (mapping/configuration error).
- `STCATADM-004` invalid store-category detail id returns `500` (expected `400/404`).

## Active blockers
- `STO-010`: `SEED_BLOCKER` (configured `API_STORE_UNIQUE_ID` does not resolve in runtime lookup).
- `MORD-API-001..005`: `SCOPE_BLOCKER` (merchant list does not include created customer order for store `9768`).
- `ORD-API-008`, `ORD-API-017`, `ORD-API-019`: `SEED_BLOCKER` (missing deterministic alternate/disabled/out-of-stock seeds).
- `ORD-API-018`: `RUNTIME_CONTRACT_CONFIG_BLOCKER` (no deterministic closed/ordering-disabled store seed).
- `ORD-CAN-003`, `ORD-CAN-004`: `RUNTIME_CONTRACT_CONFIG_BLOCKER` (no deterministic completed-order + timeline correlation).
- `NOTI-ORD-001..006`: seed/scope/runtime blockers due missing deterministic notification correlation keys/events.

## Seed evidence in use
- Stable create-order seed: `storeId=9768`, `skuId=14`.
- Runtime order-state discovery (customer scope):
  - `paidOrderId=50`
  - `cancelledOrderId=43`
  - `pendingOrderId=110` (latest create-order in run)
