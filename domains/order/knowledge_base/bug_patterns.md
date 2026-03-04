# Known Bug Patterns

- Duplicate webhook processing that creates multiple successful payments or multiple refunds.
- Idempotency replay mismatch where the same key is reused with a different payload.
- Invalid state jumps, especially merchant skip-state updates.
- Order and payment status drift, such as `payment_status=SUCCEEDED` while order is not reconciled.
- Timeout jobs that execute after the order already moved forward.
- User cancel or merchant reject paths that forget refund side effects or audit records.
