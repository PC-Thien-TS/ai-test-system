# Merchant Orders Module SRS Skeleton

## Module Overview

Merchant order operations including list/detail and lifecycle transition actions.

## Actors / Roles

- Merchant user

## Feature List

- Merchant order list/detail
- Accept/reject order
- Mark arrived
- Complete order

## Functional Requirements

- `MORD-REQ-001`: Merchant can list own-store orders.
- `MORD-REQ-002`: Merchant can view order detail by ID.
- `MORD-REQ-003`: Merchant can accept an eligible order.
- `MORD-REQ-004`: Merchant can reject an eligible order.
- `MORD-REQ-005`: Merchant can mark arrival on eligible order.
- `MORD-REQ-006`: Merchant can complete eligible order.
- `MORD-REQ-007`: Unauthorized/non-merchant access is denied safely.
- `MORD-REQ-008`: Invalid order IDs and invalid transitions do not produce 5xx responses.

## Business Rules

- Merchant can only act on orders linked to owned/managed store.
- Transition actions are constrained by current order status.
- Invalid transition attempts should return controlled non-5xx errors.

## Assumptions / Dependencies

- Merchant account is linked to verified store.
- Order exists in a state eligible for tested transition.

## Open Questions

- Detailed status transition map and guard conditions.
- Conflict/duplicate action semantics (e.g., repeated accept).

## Placeholder Traceability IDs

- `MORD-REQ-001` -> `MORD-001`
- `MORD-REQ-002` -> `MORD-002` (planned)
- `MORD-REQ-003` -> `MORD-003`
- `MORD-REQ-004` -> `MORD-004` (planned)
- `MORD-REQ-005` -> `MORD-005` (planned)
- `MORD-REQ-006` -> `MORD-006` (planned)
- `MORD-REQ-007` -> `MORD-007` (planned)
- `MORD-REQ-008` -> `MORD-008` (planned)
