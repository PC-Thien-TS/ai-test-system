# RANKMATE Wave 1 Runnable Matrix

## A. Findings
- Total API cases in Wave 1 suite: **49**.
- Current runtime blocker is upstream connectivity:
  - `API_BASE_URL=http://localhost:5209` is not reachable in this session.
- Because connectivity is blocked, **no case is runnable now**.

## B. Runnable Classification Rules
- `Runnable now`: backend reachable + required env/data for that case exists.
- `Blocked`: missing connectivity and/or missing env/data/seed prerequisites.

## C. Current Environment Summary
- `.env` missing in `ai_test_system`.
- No role credentials present.
- No seed IDs present.
- No Stripe/MoMo callback secrets present.
- Local backend launch ports (`5209`, `5985`, `7005`) unreachable.

## D. Case Matrix (Current Session)

| Case ID(s) | Domain | Runnable Now | Blocked | Primary Block Reason | Minimum required to unblock | Recommended order |
|---|---|---|---|---|---|---|
| `AUTH-API-001,002,007,008,009,010` | Auth/Permission/Session | No | Yes | Backend unreachable + missing user creds | Reachable `API_BASE_URL` + `API_USER` + `API_PASS` | Phase A |
| `AUTH-API-003,004,005` | Merchant Auth | No | Yes | Backend unreachable + missing merchant creds | Reachable backend + `API_MERCHANT_USER` + `API_MERCHANT_PASS` (+ valid merchant store mapping) | Phase A |
| `AUTH-API-006` | Admin Auth | No | Yes | Backend unreachable + missing admin creds | Reachable backend + `API_ADMIN_USER` + `API_ADMIN_PASS` | Phase A |
| `ORD-API-001,002,003,004,006,007,008,009,010` | Order/Idempotency | No | Yes | Backend unreachable + missing user creds/store+sku seeds | Phase A prerequisites + `API_ORDER_STORE_ID` + `API_ORDER_SKU_ID` | Phase B |
| `ORD-API-005` | Order Validation | No | Yes | Backend unreachable + missing unavailable SKU seed | Phase B prerequisites + `API_DISABLED_SKU_ID` or `API_OUT_OF_STOCK_SKU_ID` | Phase B |
| `ORD-API-011` | Retry Replacement | No | Yes | Backend unreachable + missing terminal seed | Phase B prerequisites + `API_CANCELLED_ORDER_ID` | Phase B |
| `PAY-API-001,002` | Payment Init/Verify | No | Yes | Backend unreachable + missing order bootstrap data | Phase B prerequisites | Phase C |
| `PAY-API-005,006,010` | Callback Negative | No | Yes | Backend unreachable | Reachable backend only | Phase C |
| `PAY-API-003,004,007,008,011` | Stripe Callback + Consistency | No | Yes | Backend unreachable + missing Stripe secret + missing role/seed data | Phase B prerequisites + `API_STRIPE_WEBHOOK_SECRET` + merchant mapping/seeds | Phase C |
| `PAY-API-009` | MoMo Callback | No | Yes | Backend unreachable + missing MoMo callback config | Reachable backend + all `API_MOMO_*` values | Phase C |
| `MER-API-001..010` | Merchant Lifecycle | No | Yes | Backend unreachable + missing merchant creds/mapping + missing seeded state IDs | Merchant auth + `API_MERCHANT_STORE_ID` + state IDs (`API_PAID_ORDER_ID`, `API_ACCEPTED_ORDER_ID`, etc.) | Phase D |
| `CONS-API-001..007` | Cross-surface Consistency | No | Yes | Backend unreachable + missing user/admin/merchant creds and shared order data | Full auth + merchant mapping + `API_CONSISTENCY_ORDER_ID` or auto-create prerequisites | Phase D |

## E. “Runnable with Minimal Prereqs” View (When backend is reachable)
- Minimal executable subset target:
  - `AUTH-API-001`
  - `AUTH-API-002`
  - `AUTH-API-008`
  - `AUTH-API-009`
- Required minimum:
  - `RANKMATE_WAVE1_ENABLED=1`
  - reachable `API_BASE_URL`
  - `API_USER`, `API_PASS`

## F. Decision
- Stop escalation to Phase B/C/D for now.
- Unblock backend connectivity and base credentials first, then re-run Phase A only.

