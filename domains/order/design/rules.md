# Order Rules (v1)

---

## A. Gating / Eligibility (Hard Guard)
Backend MUST enforce eligibility, không dựa client. 

### Reason codes (standard)
- ORDERING_DISABLED
- PAYMENT_DISABLED
- STORE_NOT_VERIFIED
- STORE_INACTIVE
- WHITELIST_REQUIRED
- (optional) STORE_CLOSED_NOW :contentReference[oaicite:39]{index=39}

---

## B. Menu / SKU Rules (Downstream safety)
- Price chỉ tồn tại ở SKU; create order snapshot lấy unit_price từ SKU tại thời điểm tạo. 
- Nếu bất kỳ SKU unavailable -> reject ITEM_UNAVAILABLE. 
- qty integer >=1 (<=99 ở UI). 

---

## C. Idempotency (must-have)
- POST /orders và POST /orders/{id}/payments: Idempotency-Key required. 
- Idempotency record lưu fingerprint để phát hiện mismatch (IDEMPOTENCY_REPLAY_MISMATCH). :contentReference[oaicite:44]{index=44}
- “Retry network” phải safe, không tạo double order/payment. 

---

## D. Payment Consistency (money safety)
- One successful payment per order. :contentReference[oaicite:46]{index=46}
- PAID only from webhook; client không set. 
- Payment pending expiry = 10 minutes (expires_at). 
- Job payment timeout: PAYMENT_PENDING quá hạn -> EXPIRED. :contentReference[oaicite:49]{index=49}

---

## E. Cancellation / Refund (v1)
- User cancel chỉ hợp lệ khi order PAID và chưa ACCEPTED. 
- Merchant reject yêu cầu reason_code (bắt buộc). 
- Refund v1: 100% only; unique refund record per order. :contentReference[oaicite:52]{index=52}

---

## F. Merchant SLA
- Nếu PAID quá 15 phút và chưa ACCEPTED -> auto cancel + refund. 

---

## G. Late Webhook (critical incident prevention)
Nếu order đã terminal nhưng webhook success đến:
- record payment SUCCEEDED
- auto refund 100% immediately (idempotent)
- audit + alert. 

---

## H. Notification Model (minimum transactional)
- Event types tối thiểu: ORDER_CREATED, PAYMENT_INITIATED, ORDER_PAID, PAYMENT_FAILED, ORDER_ACCEPTED, ORDER_REJECTED, ORDER_CANCELLED, ORDER_EXPIRED, REFUND_REQUESTED, REFUND_SUCCEEDED, REFUND_FAILED. :contentReference[oaicite:55]{index=55}
- Merchant “New order” push chỉ phát khi ORDER_PAID (không phát khi chưa PAID). 
- Notification at-least-once; client phải dedupe bằng dedupe_key. :contentReference[oaicite:57]{index=57}