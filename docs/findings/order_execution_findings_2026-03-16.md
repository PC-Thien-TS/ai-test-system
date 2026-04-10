# Order Execution Findings (2026-03-16)

## Scope
Order-first API expansion run using the existing regression framework in `scripts/run_api_regression.ps1`.

## Execution Snapshot
- Source artifact: `artifacts/test-results/api-regression/api_regression.summary.json`
- Run totals: `total=109`, `passed=69`, `failed=2`, `skipped=38`
- Non-order failures remain: `STO-009`, `STO-011`

## Newly Added/Executed Order Cases
- `ORD-API-005` create order idempotency with same key
- `ORD-API-006` create order rejects empty items
- `ORD-API-007` create order rejects invalid sku
- `ORD-API-008` cross-store cart rule
- `ORD-API-009` order history contains created order
- `ORD-PAY-001..004` order payment validation/success/retry/pending coverage
- `MORD-API-005` merchant list contains created order
- `AORD-API-003` admin list contains created order
- `AORD-API-004` admin detail contains items and timeline

## Classification Summary

PASS:
- `ORD-API-001` create order happy path (`200`) with `storeId=9768`, `skuId=14`, `quantity=1`
- `ORD-API-005` idempotency same key (`200`, same `orderId=45`)
- `ORD-API-006` empty items rejected (`400`)
- `ORD-API-007` invalid sku rejected (`400 ITEM_UNAVAILABLE`)
- `ORD-API-004` order detail (`200`)
- `ORD-PAY-002` payment invalid-path validation (`400`, `Idempotency-Key` required)

SCOPE_BLOCKER:
- `MORD-API-001`, `MORD-API-002` blocked by `FORBIDDEN_SCOPE` and classified as `SKIPPED`
- `MORD-API-005` merchant list does not include seeded order id in current merchant context
- `AORD-API-003`, `AORD-API-004` blocked by admin role (`401`)

SEED_BLOCKER:
- `ORD-API-008` cross-store rule cannot run deterministically (no alternate store+sku seed)
- `ORD-API-009` order list endpoint returned `200` but did not include seeded order id

RUNTIME_CONTRACT_CONFIG_BLOCKER:
- `ORD-PAY-001`, `ORD-PAY-003`, `ORD-PAY-004` remain blocked until deterministic payment payload contract is auto-resolved

BACKEND_DEFECT:
- No new Order backend defect in this run
- Existing non-order backend defects remain: `STO-009`, `STO-011`

## Confirmed Reusable Seeds/Contracts
- Stable order creation seed:
  - `storeId=9768`
  - `skuId=14`
- Runtime contract:
  - `Content-Type: application/json; charset=utf-8`
  - `Idempotency-Key` required
  - `items[0].quantity >= 1`

## Next Actions
1. Add deterministic second store seed to unlock `ORD-API-008`.
2. Resolve customer history/list seed strategy for `ORD-API-009` (order id visibility in list payload).
3. Auto-resolve payment request schema fields from Swagger to unlock `ORD-PAY-001/003/004`.
4. Re-run merchant/admin tracking with scope-capable accounts for `MORD-API-001..005`, `AORD-API-003`, `AORD-API-004`.
