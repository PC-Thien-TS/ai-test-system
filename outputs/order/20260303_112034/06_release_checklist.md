# Order System Release Checklist

> Release gate: all 37 P0 regression cases in the provided suite must pass before release.  
> Assumption: `STATE_MACHINE_JSON` was not populated in the source prompt, so this checklist is derived from the refined testcase set and the statuses explicitly referenced there.

## Smoke Checklist

- [ ] Create a single-SKU order successfully and confirm `CREATED`, snapshot data, and totals are correct (`TC-ORDER-001`).
- [ ] Create a multi-item order and confirm subtotal and total math are correct (`TC-ORDER-002`).
- [ ] Verify snapshot price immutability after downstream catalog price change (`TC-ORDER-003`).
- [ ] Read order detail and confirm contract fields plus `meta.request_id` and `meta.server_time` are present (`TC-ORDER-012`).
- [ ] Create a payment attempt from `CREATED` and confirm transition to `PAYMENT_PENDING` with ~10 minute expiry (`TC-ORDER-014`).
- [ ] Verify order detail does not show `PAID` while payment is still pending (`TC-ORDER-021`).
- [ ] Send a valid payment success webhook and confirm `PAYMENT_PENDING -> PAID`, `paid_at` populated, and read models remain consistent (`TC-ORDER-024`).
- [ ] Verify merchant new-order notification is emitted only when the order becomes `PAID` (`TC-ORDER-053`).
- [ ] Advance a paid order through `ACCEPTED -> PREPARING -> READY -> COMPLETED` (`TC-ORDER-033`).
- [ ] Reject a paid order with a valid reason and confirm refund flow starts exactly once (`TC-ORDER-034`).
- [ ] Cancel a paid but not yet accepted order and confirm `CANCELLED` plus refund creation (`TC-ORDER-039`).
- [ ] Open admin order detail and confirm snapshot items, payment attempts, refund record, and audit timeline are all visible (`TC-ORDER-050`).

## Regression Checklist

### Order Creation & Snapshot

- [ ] Same idempotency key returns the same order and does not duplicate rows (`TC-ORDER-004`).
- [ ] Idempotency replay mismatch returns `409 IDEMPOTENCY_REPLAY_MISMATCH` (`TC-ORDER-005`).
- [ ] Missing `Idempotency-Key` is rejected with no persisted order (`TC-ORDER-006`).
- [ ] `ORDERING_ENABLED=OFF` blocks order creation (`TC-ORDER-007`).
- [ ] Unverified or inactive stores cannot create orders (`TC-ORDER-008`, `TC-ORDER-009`).
- [ ] Unavailable SKU and invalid quantity requests fail without partial persistence (`TC-ORDER-010`, `TC-ORDER-011`).
- [ ] Order detail is forbidden for a different user (`TC-ORDER-013`).
- [ ] High-concurrency create retries collapse to one logical order (`TC-ORDER-055`).

### Payment Attempt & Expiry

- [ ] Same payment idempotency key returns the same attempt (`TC-ORDER-015`).
- [ ] Payment idempotency replay mismatch is rejected (`TC-ORDER-016`).
- [ ] Missing payment `Idempotency-Key` is rejected (`TC-ORDER-017`).
- [ ] `PAYMENT_ENABLED=OFF` blocks payment creation (`TC-ORDER-018`).
- [ ] Cancelled or already-paid orders cannot start a new payment (`TC-ORDER-019`, `TC-ORDER-026`).
- [ ] Client timeout during payment creation is safe to retry (`TC-ORDER-020`).
- [ ] Payment timeout job does not expire before 10 minutes (`TC-ORDER-022`).
- [ ] Payment timeout job expires pending payments at 10 minutes and emits a single expiry outcome (`TC-ORDER-023`).
- [ ] High-concurrency payment-init retries collapse to one payment attempt (`TC-ORDER-056`).

### Webhook (Signature/Dedupe/Late)

- [ ] Success webhook moves order to `PAID` and keeps read models consistent (`TC-ORDER-024`).
- [ ] Failed webhook moves order back to `CREATED` and keeps read models consistent (`TC-ORDER-025`).
- [ ] Invalid webhook signature is rejected with no side effects (`TC-ORDER-027`).
- [ ] Event-id dedupe makes repeated success and failed webhooks no-ops (`TC-ORDER-028`).
- [ ] Failed webhook arriving after success does not regress a paid order (`TC-ORDER-029`).
- [ ] Late success webhook for terminal orders triggers exactly one immediate full refund plus alerting (`TC-ORDER-030`).
- [ ] Duplicate late success webhook does not create a second refund or second alert (`TC-ORDER-031`).
- [ ] Burst duplicate success deliveries keep a single financial outcome (`TC-ORDER-032`).
- [ ] Duplicate success webhook does not emit duplicate `ORDER_PAID` notifications (`TC-ORDER-054`).

### Merchant Operations (Accept/Reject/Status Chain)

- [ ] Happy-path fulfillment chain works end to end (`TC-ORDER-033`).
- [ ] Paid-order rejection requires reason and triggers one refund workflow (`TC-ORDER-034`).
- [ ] Reject without `reason_code` fails and creates no refund (`TC-ORDER-035`).
- [ ] Merchant cannot accept or reject an unpaid order (`TC-ORDER-036`).
- [ ] Invalid fulfillment transitions are rejected and not audited as valid transitions (`TC-ORDER-037`).
- [ ] Merchant from another store is forbidden from updating the order (`TC-ORDER-038`).

### Cancellation & Refund

- [ ] User can cancel a paid but unaccepted order and trigger one refund (`TC-ORDER-039`).
- [ ] User cannot cancel `CREATED` or `ACCEPTED` orders (`TC-ORDER-040`).
- [ ] Retried user cancel does not create duplicate refunds or side effects (`TC-ORDER-041`).
- [ ] Retried merchant reject does not create a second refund (`TC-ORDER-042`).
- [ ] Cancel after refund already succeeded is rejected (`TC-ORDER-043`).
- [ ] Refund failure is reflected on the order and captured in audit (`TC-ORDER-047`).
- [ ] Refund notifications emit one requested event and one terminal outcome only (`TC-ORDER-048`).

### SLA Jobs (10', 15')

- [ ] 10-minute payment expiry boundary is enforced exactly (`TC-ORDER-022`, `TC-ORDER-023`).
- [ ] 15-minute merchant acceptance SLA auto-cancels paid orders and triggers one refund (`TC-ORDER-044`).
- [ ] 15-minute SLA does not fire before the boundary (`TC-ORDER-045`).
- [ ] Scheduler jobs skip orders already `ACCEPTED` or `CANCELLED` and do not introduce races (`TC-ORDER-046`).

### Admin/Ops Observability Checks

- [ ] Admin order list combined filters return only matching orders (`TC-ORDER-049`).
- [ ] Admin order detail matches underlying order, payment, refund, and audit records (`TC-ORDER-050`).
- [ ] Non-admin access to admin endpoints is forbidden with no data leakage (`TC-ORDER-051`).
- [ ] Runtime control changes are audited and take effect immediately (`TC-ORDER-052`).
- [ ] Merchant new-order notification timing is correct (`TC-ORDER-053`).
- [ ] Duplicate webhook notification suppression is working (`TC-ORDER-054`).

## Data Verification Checklist

- [ ] Verify each API success and error response includes `meta.request_id`.
- [ ] Correlate `request_id` across application logs, API gateway logs, audit entries, and job logs.
- [ ] Correlate `order_id` across order, payment attempt, refund, notification, audit, and admin read models.
- [ ] Verify order record fields: `order_id`, `store_id`, `user_id`, `status`, `snapshot_items`, `totals.subtotal`, `totals.fees_total`, `totals.total_amount`, `created_at`, `paid_at`, and terminal timestamps when applicable.
- [ ] Verify payment attempt fields: `payment_attempt_id`, `order_id`, `payment_status`, `expires_at`, provider reference or event id, idempotency key, and amount.
- [ ] Verify refund record fields: `refund_id`, `order_id`, `refund_status`, refund reason or source action, provider reference, and created or terminal timestamps.
- [ ] Verify webhook dedupe storage uses stable provider `event_id` and links back to the correct `order_id` or payment attempt.
- [ ] Verify audit records capture actor, action, previous status, next status, reason code where applicable, and timestamp.
- [ ] Verify notification records include event type, `order_id`, dedupe key, delivery outcome, and timestamp.
- [ ] Verify no duplicate logical rows exist after idempotent retries or duplicate webhook deliveries.
- [ ] Verify admin read models match source-of-truth tables for snapshot items, payment attempts, refund data, and timeline events.
- [ ] Verify scheduled job executions are traceable by `job_run_id` or equivalent and can be joined back to affected `order_id` values.

## Monitoring Checklist

- [ ] Alert exists for elevated order-create failures, payment-init failures, and webhook processing failures.
- [ ] Alert exists for invalid webhook signatures and for spikes in deduped duplicate events.
- [ ] Alert exists for late webhook incidents that trigger refund compensation.
- [ ] Alert exists for payment expiry job delay, merchant SLA job delay, and scheduler backlog.
- [ ] Alert exists for refund failures, stuck refunds, and abnormal refund volume.
- [ ] Alert exists for order/read-model inconsistency or audit-write failures.
- [ ] Dashboard shows order funnel by status: `CREATED`, `PAYMENT_PENDING`, `PAID`, `ACCEPTED`, `PREPARING`, `READY`, `COMPLETED`, `CANCELLED`, `EXPIRED`, `REJECTED`.
- [ ] Dashboard shows payment outcomes, webhook outcomes, refund outcomes, and notification delivery outcomes.
- [ ] Dashboard allows drill-down by `request_id`, `order_id`, and provider event id.
- [ ] Runbook documents how to identify affected orders, reconcile payment vs order state, and verify refund status.
- [ ] Runbook includes immediate operational controls for `ORDERING_ENABLED`, `PAYMENT_ENABLED`, and whitelist changes.
- [ ] Runbook includes owner or escalation path for payments, webhooks, refunds, scheduler failures, and admin control issues.

## Risks & Rollback Notes

- [ ] State-machine source data was missing in the prompt input; confirm actual transition rules before sign-off, especially around terminal states and compensation paths.
- [ ] Highest release risk is money movement: idempotency failures, duplicate webhook handling, late success compensation, and duplicate refund prevention.
- [ ] Secondary risk is scheduler boundary behavior at 10 and 15 minutes, including clock skew and repeated job execution.
- [ ] Secondary risk is read-model drift between order, payment, refund, audit, and admin views after retries or asynchronous webhook processing.
- [ ] If order creation is unstable, set `ORDERING_ENABLED=OFF` to stop new orders.
- [ ] If payment initiation or webhook handling is unstable, set `PAYMENT_ENABLED=OFF` and hold payment-related processing until reconciliation is complete.
- [ ] If rollout scope must be reduced, enable whitelist-only mode for controlled stores or users.
- [ ] Reconcile all in-flight `PAYMENT_PENDING`, recently `PAID`, and recently refunded orders before reopening traffic.
- [ ] Confirm no duplicate refunds, no orphaned successful payments, and no terminal orders missing audit evidence before rollback is considered complete.