# Order Execution Findings (2026-03-13)

## Scope
This note separates live Order execution findings into backend defects vs non-defect blockers for today's focused rerun.

## Backend Defects
- No new Order backend defect was confirmed in today's run.

## Scope / Account Blockers
- `MORD-API-001` `POST /api/v1/merchant/orders/37/accept` -> `400 FORBIDDEN_SCOPE`
- `MORD-API-002` `POST /api/v1/merchant/orders/38/reject` -> `400 FORBIDDEN_SCOPE`
- `MORD-API-003` `POST /api/v1/merchant/orders/37/mark-arrived` -> `400 FORBIDDEN_SCOPE`
- `MORD-API-004` `POST /api/v1/merchant/orders/37/complete` -> `400 FORBIDDEN_SCOPE`
- `AORD-API-001` `GET /api/v1/admin/orders?pageNumber=1&pageSize=5` -> `401`
- `AORD-API-002` `GET /api/v1/admin/orders/37` -> `401`

Interpretation:
- Current account can create customer orders but cannot operate merchant lifecycle transitions for the created store/order context.
- Current account also lacks admin role for admin order APIs.
- These are not backend defects by current evidence.

## Seed / Data Findings
- Stable working seed was re-established:
  - `storeId=9768`
  - `skuId=14`
- `storeId=9608` remains unusable as a success-path seed because `/api/v1/stores/9608/menu` returned zero categories.

## Runtime Contract / Config Findings
- Create-order succeeds when the request uses:
  - `application/json; charset=utf-8`
  - `Idempotency-Key`
  - `storeId=9768`
  - `items[0].skuId=14`
  - `items[0].quantity=1`
- Negative contract checks remain valid and controlled:
  - wrong media type -> `415`
  - missing items -> `400`

## Runner / Framework Findings
- No runner or framework defect was observed in today's focused Order rerun.

## Evidence
- `test-assets/seeds/order/order_seed.json`
- `artifacts/test-results/order/order_execution_2026-03-13.json`
- `artifacts/test-results/order/order_critical_rerun_2026-03-13.json`
