# Order Runtime Contract (Proven)

## Scope
This document captures the executable runtime contract proven by live regression evidence on 2026-03-11.

## Proven Cases
- `ORD-API-001`: `PASS` `200`
- `ORD-API-002`: `PASS` `415`
- `ORD-API-003`: `PASS` `400`
- `ORD-API-004`: `PASS` `200`

## Create Order Contract
- Method: `POST /api/v1/orders`
- Headers:
  - `Authorization: Bearer <token>`
  - `Content-Type: application/json; charset=utf-8`
  - `Idempotency-Key: <unique value>`
- Minimal payload:
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

## Seed and Data Preconditions
- Preferred store for success path: `9768`
- Verified usable SKU IDs: `14, 15, 16, 17, 18, 19`
- SKU seed source: `GET /api/v1/stores/{storeId}/menu` from `data.categories[].items[].skus[].id`

## Merchant and Admin Constraints (Current Environment)
- Merchant lifecycle follow-up (`accept`, `reject`, `mark-arrived`, `complete`) currently returns `400 FORBIDDEN_SCOPE` for tested order context.
- Admin order list/detail endpoints remain role-blocked (`401`) with non-admin account.

## Evidence References
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.log`
- `artifacts/test-results/order_flow_check.json`
- `docs/traceability/order_runtime_evidence.md`
