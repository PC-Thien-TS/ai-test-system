# Order Extended Coverage Plan (2026-03-20)

## Objective
Extend Order-first regression beyond baseline contract checks while preserving deterministic classification:
- `PASS`
- `FAIL` for real backend/server defects
- `SKIPPED` with explicit blocker class for seed or scope gaps

## New API Cases Added

### Order creation depth
- `ORD-API-021` create reservation happy path
- `ORD-API-022` reservation invalid `arrivalTime` in past
- `ORD-API-023` reservation invalid `pax` out of range
- `ORD-API-024` create order with multiple items
- `ORD-API-025` create order note and null-note behavior
- `ORD-API-026` create order duplicate SKU lines
- `ORD-API-027` idempotency replay with changed payload and same key
- `ORD-API-028` create preorder happy path
- `ORD-API-029` pricing preview contract behavior

### Customer post-order actions
- `ORD-CUS-004` customer report-not-arrived returns controlled status

### Merchant and admin monitoring
- `MORD-API-008` merchant detail loads target order
- `AORD-API-005` admin list filters by store and status
- `AORD-API-006` admin dispute list visibility
- `AORD-API-007` admin dispute detail visibility
- `AORD-API-008` admin dispute resolve validation with invalid payload

### Add-on and runtime caveat tracking
- `ORD-ADDON-001` add-on request controlled status
- `ORD-ADDON-002` add-on invalid SKU behavior
- `ORD-JOB-001..004` runtime job and timeline consistency placeholders
- `ORD-CAVEAT-001..004` known implementation caveat checkpoints

## Latest Execution Snapshot
- Source: `artifacts/test-results/api-regression/api_regression.summary.json`
- Run summary: `total=166`, `passed=65`, `failed=7`, `skipped=94`

## Interpretation
- New cases are wired and visible in summary/log outputs.
- Customer and merchant login are currently blocked in this runtime (`Incorrect email or password`), so customer/merchant-dependent new cases correctly classify as blockers instead of false pass/fail.
- Admin token remains valid, so admin-dispute coverage (`AORD-API-005..008`) is executable where seed exists.

## Required Seeds To Unlock More Cases
1. Deterministic customer auth token for the current runtime host.
2. Deterministic merchant-owned order seed for full merchant lifecycle sequencing.
3. Deterministic second active SKU in same store for multi-item happy-path proof.
4. Deterministic dispute id for full admin dispute detail and resolve paths.
5. Deterministic scheduler/window hooks for timeout and auto-release job assertions.

