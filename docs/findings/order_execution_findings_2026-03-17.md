# Order Execution Findings (2026-03-17)

## Evidence
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.log`

## Run snapshot
- Total: `134`
- Passed: `80`
- Failed: `4`
- Skipped: `50`

## Newly proven in this run
- `ORD-API-009` order history/list consistency: `PASS`
- `ORD-API-016` missing items field validation: `PASS`
- `ORD-API-020` create-order to detail consistency: `PASS`
- `ORD-PAY-001` payment success: `PASS`
- `ORD-PAY-003` payment retry behavior: `PASS`
- `ORD-PAY-004` pending markers (`paymentAttemptId`, `stripeClientSecret`, `expiresAt`): `PASS`

## Active Order-related backend defect candidates
- `ORD-API-014`: invalid `storeId` create-order path returns `500`
- `ORD-API-015`: missing `storeId` create-order path returns `500`

## Active blockers
- Scope blocker:
  - `MORD-API-001..005` (`FORBIDDEN_SCOPE` or created order not visible in merchant list)
- Account blocker:
  - `AORD-API-001..004`, `AORD-OPS-001..002` (`401`)
- Seed blocker:
  - `ORD-API-008`, `ORD-API-017` (no deterministic second store+sku)
- Runtime contract/config blocker:
  - `ORD-PAY-005`, `ORD-PAY-006` (already-paid/cancelled order seeds not deterministic)
  - `ORD-CAN-002..004`, `NOTI-ORD-002..006`

## Confirmed contracts/seeds
- Stable creation seed: `storeId=9768`, `skuId=14`
- Create-order requires:
  - `Content-Type: application/json; charset=utf-8`
  - `Idempotency-Key`
  - `items[].quantity >= 1`
- Payment endpoint:
  - `POST /api/v1/orders/{id}/payments`
  - no requestBody schema declared in Swagger
  - executable with `Idempotency-Key` and `{}` payload
