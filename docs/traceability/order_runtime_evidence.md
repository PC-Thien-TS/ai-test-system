# Order Runtime Evidence Snapshot (2026-03-20)

## Source artifacts
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.log`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `test-assets/seeds/order/order_seed.json`

## Latest validated run summary
- `total=166`
- `passed=131`
- `failed=7`
- `skipped=28`

## Deterministic runtime base
- `storeId=9768`
- `skuId=14`
- Scenario-created order ids in latest run:
  - J1/J7 detail anchor: `225`
  - J2 payment: `227`
  - J3 customer actions: `228`
  - J5 merchant visibility/action: `229`

## Critical evidence rows

| Testcase ID | Endpoint | Outcome | Status | Evidence |
|---|---|---|---|---|
| `ORD-API-001` | `POST /api/v1/orders` | PASS | 200 | Create-order succeeds with runtime-required JSON + idempotency contract. |
| `ORD-API-004` | `GET /api/v1/orders/{id}` | PASS | 200 | Detail is retrievable for scenario-created order. |
| `ORD-API-009` | `GET /api/v1/orders` | PASS | 200 | Customer list contains created order id. |
| `ORD-PAY-001` | `POST /api/v1/orders/{id}/payments` | PASS | 200 | Payment intent/session markers are returned. |
| `ORD-PAY-005` | `POST /api/v1/orders/{id}/payments` | PASS | 400 | Already-paid guard returns controlled state (`ORDER_INVALID_STATE`). |
| `ORD-PAY-006` | `POST /api/v1/orders/{id}/payments` | PASS | 400 | Cancelled-order guard returns controlled state (`ORDER_INVALID_STATE`). |
| `MORD-API-005` | `GET /api/v1/merchant/orders` | PASS | 200 | Merchant list visibility is proven for scenario-created order context. |
| `MORD-API-008` | `GET /api/v1/merchant/orders/{id}` | PASS | 200 | Merchant detail loads target order. |
| `MORD-API-003` | `POST /api/v1/merchant/orders/{id}/mark-arrived` | SKIPPED | - | Accept precondition was not met (`accept` did not return `200`). |
| `AORD-API-003` | `GET /api/v1/admin/orders` | PASS | 200 | Admin list visibility for created order is proven via deterministic page scan/filter. |
| `AORD-API-004` | `GET /api/v1/admin/orders/{id}` | PASS | 200 | Admin detail includes items and timeline markers. |
| `ORD-API-022` | `POST /api/v1/orders` (past arrivalTime) | FAIL | 200 | Past arrivalTime accepted; classified as backend defect against validation expectation. |

## Active blockers (still deterministic)
- `STO-010`: unresolved real uniqueId-compatible seed.
- `ORD-API-008`, `ORD-API-017`: missing second store + active SKU.
- `ORD-API-018`: missing closed/ordering-disabled store seed.
- `ORD-API-019`: missing disabled/out-of-stock SKU seed.
- `ORD-CAN-004`: timeline key mapping for successful cancellation is not deterministic.
- `NOTI-ORD-001..006`: notification payload has no deterministic order-event correlation keys.

## Confirmed defect list from this run
- `STO-009`, `STO-011`
- `ORD-API-014`, `ORD-API-015`, `ORD-API-022`
- `MEMBER-001`
- `STCATADM-004`
