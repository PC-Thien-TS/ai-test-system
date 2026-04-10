# Order Runtime Contract (Latest Proven)

## Scope
This document reflects the latest full regression evidence on **2026-03-20** against `http://192.168.1.103:19066`.

## Create-order contract (proven)
- Endpoint: `POST /api/v1/orders`
- Required headers:
  - `Authorization: Bearer <customerToken>`
  - `Content-Type: application/json; charset=utf-8`
  - `Idempotency-Key: <unique-per-request>`
- Required payload fields:
  - `storeId`
  - `items[]`
  - `items[].skuId`
  - `items[].quantity` (`>= 1`)
- Deterministic base payload:
```json
{
  "storeId": 9768,
  "items": [
    {
      "skuId": 14,
      "quantity": 1
    }
  ]
}
```

## Scenario-driven orchestration now used
- The regression runner now creates fresh orders per journey instead of reusing a single historical order:
  - `J2-Payment`
  - `J3-CustomerAction`
  - `J5-Merchant`
- Journey context from latest run:
  - `detailOrderId=225`
  - `paymentOrderId=227`
  - `customerActionOrderId=228`
  - `merchantOrderId=229`
  - `adminOrderId=225`

## Payment contract (proven)
- Core endpoint: `POST /api/v1/orders/{id}/payments`
- Required header: `Idempotency-Key`
- Current runtime behavior proven:
  - intent/session creation returns `200` (`ORD-PAY-001`)
  - replay/retry returns controlled status (`ORD-PAY-003`)
  - verify endpoint returns controlled status (`ORD-PAY-008`)
  - wallet endpoint returns controlled status (`ORD-PAY-007`)

## Lifecycle/transition contract observations
- Merchant list/detail visibility is proven (`MORD-API-005`, `MORD-API-008`).
- Merchant accept/reject are executable and currently return controlled `400` business-state responses (`MORD-API-001`, `MORD-API-002`).
- `mark-arrived` and `complete` are currently gated by accept-precondition (`MORD-API-003`, `MORD-API-004` skipped deterministically when accept != 200).
- Customer cancellation/dispute guards are executable with controlled statuses (`ORD-CAN-001..003`).

## Known defects still failing (must remain visible)
- `STO-009`: `GET /api/v1/store/999999999` -> `500` (expected `400/404`)
- `STO-011`: `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA?UniqueId=...` -> `500` (expected `400/404`)
- `ORD-API-014`: invalid `storeId` create-order -> `500` (expected controlled `4xx`)
- `ORD-API-015`: missing/zero `storeId` create-order -> `500` (expected controlled `4xx`)
- `MEMBER-001`: `GET /api/v1/member/list` -> `500` mapping/config issue
- `STCATADM-004`: invalid store-category detail id -> `500`
- `ORD-API-022`: reservation `arrivalTime` in past accepted as `200` instead of controlled validation reject

## Active deterministic blockers
- `STO-010`: no deterministic runtime `uniqueId` seed is proven.
- `ORD-API-008`, `ORD-API-017`: no deterministic second store + active SKU.
- `ORD-API-018`: no deterministic closed/ordering-disabled store seed.
- `ORD-API-019`: no deterministic disabled/out-of-stock SKU seed.
- `ORD-CAN-004`: cancellation timeline assertion key mapping not deterministic.
- `NOTI-ORD-*`: notification payload has no deterministic event correlation for order lifecycle.

## Evidence references
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.log`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `test-assets/seeds/order/order_seed.json`
- `docs/findings/order_execution_findings_2026-03-20.md`
