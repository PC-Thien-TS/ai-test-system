# Order State Machine (v1 - Source of Truth)

Tài liệu này mô tả FSM (finite state machine) cho Order và các chuyển trạng thái hợp lệ.
Backend là source of truth. PAID chỉ được set từ webhook. :contentReference[oaicite:1]{index=1}

---

## A. Order Status (Core)

### States
- CREATED
- PAYMENT_PENDING
- PAID
- ACCEPTED
- PREPARING
- READY
- COMPLETED
- CANCELLED
- REJECTED
- EXPIRED

> Ghi chú:
- “PAID only from webhook” (client không thể set PAID). 
- Merchant app chỉ thao tác đơn đã PAID và không được skip state. 

---

## B. Payment Attempt Status (per order)

### States
- PENDING
- SUCCEEDED
- FAILED
- EXPIRED

### Constraints
- One successful payment per order (unique). :contentReference[oaicite:4]{index=4}
- Payment amount = order.total_amount snapshot. :contentReference[oaicite:5]{index=5}

---

## C. Refund Status (v1)

### States
- NONE
- REQUESTED
- SUCCEEDED
- FAILED

### Constraints
- v1 refund: 100% only. :contentReference[oaicite:6]{index=6}
- One refund record per order (unique). :contentReference[oaicite:7]{index=7}

---

## D. Valid Transitions (Order)

### User flow
1) CREATED
   - -> PAYMENT_PENDING (user creates payment attempt)
2) PAYMENT_PENDING
   - -> PAID (webhook success)
   - -> CREATED (webhook failed)
   - -> EXPIRED (job timeout 10')
3) PAID
   - -> CANCELLED (user cancel hợp lệ: PAID & not ACCEPTED)
   - -> ACCEPTED (merchant accept)
   - -> REJECTED (merchant reject + reason)
   - -> CANCELLED (job SLA 15' auto cancel + refund)
4) ACCEPTED -> PREPARING -> READY -> COMPLETED (merchant status chain only)

### Terminal states
- COMPLETED
- CANCELLED
- REJECTED
- EXPIRED

---

## E. Transition Rules (Guards)

### Eligibility guard (before side-effects)
- Eligibility must be enforced by backend (flags/whitelist/verified/active). 

### Idempotency guard (side-effects)
- POST /orders requires Idempotency-Key (required). 
- POST /orders/{id}/payments requires Idempotency-Key (required). :contentReference[oaicite:10]{index=10}
- Cancel/reject/refund phải idempotent theo order_id hoặc (order_id + action). 

### No skip state (merchant)
- Allowed chain only: ACCEPTED→PREPARING→READY→COMPLETED. 

### PAID truth rule (client rendering)
- UI chỉ show “Đã thanh toán” khi GET order status=PAID. 

---

## F. Background Jobs (System transitions)

### Job 10' payment timeout
- PAYMENT_PENDING older than expires_at -> order EXPIRED, payment EXPIRED. 

### Job 15' merchant SLA auto cancel/refund
- PAID older than paid_at + 15' and not ACCEPTED -> order CANCELLED + refund 100%. 

---

## G. Late Webhook Rule (Critical)
Nếu webhook success đến sau khi order đã terminal (EXPIRED/CANCELLED/REJECTED/COMPLETED):
- Record payment SUCCEEDED
- Create refund 100% immediately (idempotent)
- Emit audit + alert. 