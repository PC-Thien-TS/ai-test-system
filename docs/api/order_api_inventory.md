# Order API Inventory

## Evidence Sources

- Live Swagger: `GET /swagger/v1/swagger.json` (retrieved on 2026-03-10)
- Regression artifacts:
  - `artifacts/test-results/api-regression/api_regression.log`
  - `artifacts/test-results/api-regression/api_regression.summary.json`

## Endpoint Inventory (Evidence-backed)

| Area | Method | Path | Role | Purpose | Request Contract | Expected Status |
|---|---|---|---|---|---|---|
| payments | GET | `/api/v1/payments/methods` | authenticated user (runtime) | Retrieve payment methods for ordering | No request body. | `200` |
| admin_orders | GET | `/api/v1/admin/orders` | admin | Admin list orders | Query params (optional): `storeId`, `status`, `dateFrom`, `dateTo`, `pageNumber`, `pageSize`. | `200` |
| admin_orders | GET | `/api/v1/admin/orders/{id}` | admin | Admin order detail | Path param: `id` (integer, required). | `200` |
| merchant_orders | GET | `/api/v1/merchant/orders` | merchant | Merchant list orders | Query params (optional): `storeId`, `status`, `pageNumber`, `pageSize`. | `200` |
| merchant_orders | GET | `/api/v1/merchant/orders/{id}` | merchant | Merchant order detail | Path param: `id` (integer, required). | `200` |
| merchant_orders | POST | `/api/v1/merchant/orders/{id}/accept` | merchant | Merchant accept order | Path param: `id` (integer, required). No request body in Swagger contract. | `200` |
| merchant_orders | POST | `/api/v1/merchant/orders/{id}/reject` | merchant | Merchant reject order | Path param: `id` (integer, required). No request body in Swagger contract. | `200` |
| merchant_orders | POST | `/api/v1/merchant/orders/{id}/mark-arrived` | merchant | Merchant mark-arrived transition | Path param: `id` (integer, required). No request body in Swagger contract. | `200` |
| merchant_orders | POST | `/api/v1/merchant/orders/{id}/complete` | merchant | Merchant complete transition | Path param: `id` (integer, required). No request body in Swagger contract. | `200` |
| orders | POST | `/api/v1/orders` | customer/authenticated actor | Create order | Content types: `application/json`, `text/json`, `application/*+json`; schema: `CreateOrderCommand`; top-level required fields: `storeId`, `items`; item schema `CreateOrderItemCommandModel` requires `skuId` (`quantity`, `note` optional by Swagger). Runtime additionally requires `Idempotency-Key` header and enforces `quantity >= 1`. | `200` |
| orders | GET | `/api/v1/orders/{id}` | customer/authenticated actor | Customer order detail | Path param: `id` (integer, required). | `200` |
| orders | POST | `/api/v1/orders/{id}/payments` | customer/authenticated actor | Order payment | Path param: `id` required; request body contract in Swagger. | `200` |
| orders | POST | `/api/v1/orders/{id}/addons` | customer/authenticated actor | Add addons to order | Path param: `id` required; request body contract in Swagger. | `200` |
| orders | POST | `/api/v1/orders/{id}/disputes` | customer/authenticated actor | Create dispute for order | Path param: `id` required; request body contract in Swagger. | `200` |
| ordering_policy | GET | `/api/v1/ordering-policy/store/{storeId}` | role-based | Read store ordering policy | Path param: `storeId` (integer, required). | `200` |
| ordering_policy | POST | `/api/v1/ordering-policy/store/{storeId}` | role-based | Upsert store ordering policy | Path param: `storeId` + body contract from Swagger. | `200` |
| ordering_policy_admin | GET | `/api/v1/ordering-policy-admin/defaults` | admin | Read default ordering policy | No body. | `200` |
| ordering_policy_admin | POST | `/api/v1/ordering-policy-admin/defaults` | admin | Upsert default ordering policy | Body contract from Swagger. | `200` |
| ordering_policy_admin | GET | `/api/v1/ordering-policy-admin/store/{storeId}` | admin | Read store ordering policy (admin) | Path param: `storeId` required. | `200` |
| ordering_policy_admin | POST | `/api/v1/ordering-policy-admin/store/{storeId}` | admin | Upsert store ordering policy (admin) | Path param: `storeId` + body contract from Swagger. | `200` |
| order_addons | POST | `/api/v1/order-addons/{addonId}/payments` | authenticated actor | Pay addon | Path param: `addonId` required; body contract from Swagger. | `200` |
| seed | POST | `/api/v1/seed/ordering-pilot` | restricted/admin | Seed ordering pilot data | No request body in Swagger. | `200` |

## Create Order Contract (Focused)

- Method/path: `POST /api/v1/orders`
- Tag: `Orders`
- Content type (Swagger): `application/json`, `text/json`, `application/*+json`
- Request schema: `CoreV2.Application.Features.Ordering.Commands.CreateOrderCommand`
- Required fields:
  - `storeId`
  - `items`
- `items[]` schema: `CreateOrderItemCommandModel`
  - required: `skuId`
  - optional: `quantity`, `note`
- Declared response: `200`

### Final Executable Runtime Contract (Current Environment)
- Endpoint: `POST /api/v1/orders`
- Headers:
  - `Authorization: Bearer <token>`
  - `Content-Type: application/json; charset=utf-8`
  - `Idempotency-Key: <unique value>`
- Minimal executable payload:
  - `storeId` (verified usable store currently `9768`)
  - `items` with at least one object:
    - `skuId` (seeded from `data.categories[].items[].skus[].id`)
    - `quantity` (`>= 1`, baseline `1`)

## Observed Runtime Requirements and Blockers

- `POST /api/v1/orders` returns `415` for unsupported media types; covered by `ORD-API-002`.
- Missing `Idempotency-Key` returns `400` (runtime validation).
- Missing/invalid `quantity` returns `400` (runtime validation).
- Current success-path blocker in test environment: `POLICY_NOT_CONFIGURED` for otherwise valid create-order request.
- Merchant transition observations:
  - `POST /merchant/orders/{id}/accept` and `POST /merchant/orders/{id}/reject` can return `400` when order state is not eligible.
  - These are currently treated as lifecycle-precondition outcomes, not transport/auth contract failures.

## Notes

- Swagger `security` is not explicitly declared per operation for these endpoints, but runtime behavior clearly enforces role/authorization (`401/403` observed on admin/merchant/customer paths).
- Role assumptions in tests are based on runtime evidence from current regression artifacts.
