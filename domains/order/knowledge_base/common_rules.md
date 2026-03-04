# Common Rules

- Backend is the source of truth for state transitions and payment truth.
- `PAID` can only be produced by webhook processing, not by direct client input.
- Merchant fulfillment must follow the exact chain `ACCEPTED -> PREPARING -> READY -> COMPLETED`.
- Payment expiry is 10 minutes from payment creation.
- Merchant SLA auto-cancel is 15 minutes after `paid_at` when the order is still not accepted.
- Refunds in v1 are full refunds only.
- Late payment success after a terminal order must trigger immediate refund, audit, and alert handling.
