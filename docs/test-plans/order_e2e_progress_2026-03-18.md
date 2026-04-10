# Order E2E Automation Progress (2026-03-18)

## Scope status

### Order Creation
- Covered: `ORD-API-001..007`, `ORD-API-009..013`, `ORD-API-016`, `ORD-API-020`.
- Partial/blocked: `ORD-API-008`, `ORD-API-017`, `ORD-API-018`, `ORD-API-019`.
- Defect-backed fails: `ORD-API-014`, `ORD-API-015`.

### Order Payment
- Covered: `ORD-PAY-001..006` (all executable in current run).
- Notes:
  - `ORD-PAY-001/003/004` proven with Stripe-style payment intent/session response markers.
  - `ORD-PAY-005/006` now execute against deterministic runtime seeds and return controlled `400 ORDER_INVALID_STATE`.

### Merchant Processing
- Partial:
  - Merchant endpoint reachability is proven.
  - Created customer orders are not visible to merchant list in this account context.
- Blocked:
  - `MORD-API-001..005` remain `SCOPE_BLOCKER`.

### Admin Tracking / Ops
- Covered with admin account (`admin@gmail.com`):
  - `AORD-API-001..004`
  - `AORD-OPS-001..002`

### Cancellation
- Covered/partial:
  - `ORD-CAN-001` and `ORD-CAN-002` execute with controlled responses.
  - `ORD-CAN-003` and `ORD-CAN-004` remain blocked by missing deterministic completed-order/timeline seeds.

### Notification
- Partial/blocked:
  - Notification feed endpoint is reachable.
  - Deterministic event correlation for order/payment/merchant/cancellation remains unproven.

## Current blockers to full Order E2E
1. Merchant ownership/scope mismatch for store/order context (`MORD-*`).
2. Missing deterministic seeds for:
   - alternate store + sku
   - disabled/out-of-stock sku
   - closed/ordering-disabled store
   - completed-order timeline correlation.
3. Runtime unique-id seed for `STO-010` unresolved.

## Next actions
1. Provide a merchant account that owns/manages store `9768` (or switch create-order seed to merchant-owned store).
2. Add deterministic seed values for `API_ALT_STORE_ID`, `API_ALT_SKU_ID`, `API_DISABLED_SKU_ID`, `API_OUT_OF_STOCK_SKU_ID`, `API_CLOSED_STORE_ID`, `API_ORDERING_DISABLED_STORE_ID`.
3. Add deterministic completed-order seed and timeline correlation key mapping for `ORD-CAN-003/004`.
