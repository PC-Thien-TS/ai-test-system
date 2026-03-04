# Order API Contract (v1 - Minimum)

Chuẩn response:
- Success: { data, meta(request_id, server_time) }
- Error: { error(code, message, details?), request_id } :contentReference[oaicite:17]{index=17}

---

## A. Public (User)

### 1) Create Order Snapshot
POST /orders
Headers:
- Idempotency-Key (required)

Request:
- store_id
- items: [{ sku_id, quantity, note? }]

Success data:
- order_id
- status = CREATED
- snapshot_items: [{ sku_id, name, unit_price, quantity, note, line_total }]
- totals: { subtotal, fees_total(0), total_amount }
- created_at

Errors (examples):
- ORDERING_DISABLED / WHITELIST_REQUIRED / STORE_NOT_VERIFIED / STORE_INACTIVE 
- ITEM_UNAVAILABLE / INVALID_QUANTITY / ITEM_PRICE_CHANGED 

Notes:
- Snapshot uses SKU price & availability at creation. 

---

### 2) Create Payment Attempt (Stripe)
POST /orders/{id}/payments
Headers:
- Idempotency-Key (required)

Pre-condition:
- order.status == CREATED

Success data:
- payment_attempt_id
- payment_status = PENDING
- order_status = PAYMENT_PENDING
- expires_at = now + 10 minutes
- stripe_client_secret (or checkout_url)

Errors (examples):
- PAYMENT_DISABLED 
- ORDER_INVALID_STATE / PAYMENT_EXPIRED / PAYMENT_ALREADY_SUCCEEDED :contentReference[oaicite:22]{index=22}
- IDEMPOTENCY_REPLAY_MISMATCH :contentReference[oaicite:23]{index=23}

---

### 3) Get Order Detail
GET /orders/{id}

Success data (minimum):
- order_id, store_id, user_id
- status
- snapshot_items, totals
- created_at, paid_at?, expires_at?
- payment_status (latest)
- refund_status?

Client rules:
- UI show “paid” only when status=PAID. 
- PAYMENT_PENDING polling nhanh hơn (3–5s). :contentReference[oaicite:25]{index=25}

---

### 4) Cancel Order (User)
POST /orders/{id}/cancel
Headers:
- Idempotency-Key (khuyến nghị, hoặc backend idempotent by order_id)

Pre-condition:
- order.status == PAID
- order NOT ACCEPTED

Success:
- status = CANCELLED
- refund_status updated (REQUESTED/SUCCEEDED/FAILED)

Errors:
- ORDER_INVALID_STATE
- REFUND_ALREADY_DONE 

---

## B. Merchant

### 1) Accept Order
POST /merchant/orders/{id}/accept
Pre-condition:
- order.status == PAID

Success:
- status = ACCEPTED

Errors:
- ORDER_NOT_PAID / ORDER_INVALID_STATE 

---

### 2) Reject Order (Reason required)
POST /merchant/orders/{id}/reject
Request:
- reason_code (required)
- note? (optional)

Pre-condition:
- order.status == PAID

Success:
- status = REJECTED
- refund 100% triggered

Errors:
- REJECT_REASON_REQUIRED
- ORDER_NOT_PAID / ORDER_INVALID_STATE 

---

### 3) Update Fulfillment Status
POST /merchant/orders/{id}/status
Request:
- next_status in { PREPARING, READY, COMPLETED }

Pre-condition:
- Only chain: ACCEPTED→PREPARING→READY→COMPLETED (no skip)

Errors:
- STATUS_SEQUENCE_INVALID
- STORE_SCOPE_FORBIDDEN 

---

## C. Webhooks

### Stripe Webhook
POST /webhooks/stripe
Rules:
- Verify signature header (invalid -> 400). :contentReference[oaicite:30]{index=30}
- Dedupe by stripe_event_id (duplicate -> 200 OK no-op). :contentReference[oaicite:31]{index=31}
- Success: PAYMENT_PENDING -> set payment SUCCEEDED + order PAID. :contentReference[oaicite:32]{index=32}
- Failed: PAYMENT_PENDING -> set payment FAILED + order CREATED. :contentReference[oaicite:33]{index=33}

Late webhook:
- If order terminal -> auto refund 100% + audit + alert. 

---

## D. Admin/Ops (Read-only + Controls)

GET /admin/orders
- filters: date range, store_id, status, payment status, refund status, keyword q
- columns: order_id/code, store_id, status, total_amount, created_at, paid_at, refund_status 

GET /admin/orders/{id}
- must show: snapshot items/totals, payment attempts, refund record, audit timeline 

(Optional) Runtime controls (pilot):
- POST /admin/flags (ORDERING_ENABLED, PAYMENT_ENABLED)
- POST /admin/whitelist (store_ids, user_ids, whitelist_mode)
All changes must be audited. 