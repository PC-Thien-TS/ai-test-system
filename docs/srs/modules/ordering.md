# Ordering Module SRS Skeleton

## Module Overview

Order creation and order lifecycle operations from customer and merchant perspectives.

## Actors / Roles

- End user (order creator)
- Merchant user (order fulfiller)
- Admin user (oversight)

## Feature List

- Create order
- View order detail
- Addons/payment/dispute endpoints
- Merchant order acceptance and subsequent lifecycle actions

## Functional Requirements

- `ORDER-REQ-001`: System creates order when preconditions are satisfied.
- `ORDER-REQ-002`: System returns order detail for valid order ID.
- `ORDER-REQ-003`: Merchant can accept eligible order.
- `ORDER-REQ-004`: Non-eligible actions return controlled non-5xx responses.
- `ORDER-REQ-005`: Missing/invalid order IDs do not trigger server errors.

## Business Rules

- Ordering requires store/catalog readiness and valid actor permissions.
- Merchant lifecycle actions depend on current order status.
- Invalid transitions must be rejected safely.

## Assumptions / Dependencies

- Verified store exists.
- Merchant account is linked to target store.
- Catalog has active/published orderable entities.

## Open Questions

- Required payload fields for order creation in current environment.
- Full order state machine and transition guard conditions.
- Expected status codes for invalid order transitions.

## Placeholder Traceability IDs

- `ORDER-REQ-001` -> `ORD-001`
- `ORDER-REQ-002` -> `ORD-003`
- `ORDER-REQ-003` -> `MORD-003`
- `ORDER-REQ-004` -> `MORD-004`, `MORD-005`, `MORD-006` (planned)
- `ORDER-REQ-005` -> `ORD-TBD-NEG-001` (planned)

## Evidence-Based API Notes

- Contract evidence source: `docs/api/order_api_inventory.md`.
- `POST /api/v1/orders` Swagger schema:
  - required: `storeId`, `items`
  - item required: `items[].skuId`
  - content types: `application/json`, `text/json`, `application/*+json`
- Runtime observation from regression artifacts:
  - unsupported payload/content-type combinations can return `415 Unsupported Media Type`.

## Critical Automated Mapping (Current)

- `ORDER-REQ-001` -> `ORD-API-001`
- `ORDER-REQ-002` -> `ORD-API-002`
- `ORDER-REQ-003` -> `ORD-API-003`
- `ORDER-REQ-004` -> `ORD-API-004`
