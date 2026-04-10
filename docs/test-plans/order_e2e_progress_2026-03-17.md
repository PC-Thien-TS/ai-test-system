# Order E2E Automation Progress (2026-03-17)

## Scope completed today
- Reviewed and corrected Order-first regression wiring in `scripts/run_api_regression.ps1`
- Re-ran full API regression and captured fresh evidence
- Expanded executable Order creation validation coverage
- Unlocked payment success/retry/pending checks using live runtime contract behavior
- Updated findings and SRS coverage status based on actual run outcomes

## Current flow status

### 1) Order Creation
- Covered:
  - `ORD-API-001..007`
  - `ORD-API-009`
  - `ORD-API-010..013`
  - `ORD-API-016`
  - `ORD-API-020`
- Partial/blocked:
  - `ORD-API-008`, `ORD-API-017` (cross-store seed blocker)
  - `ORD-API-018`, `ORD-API-019` (closed/disabled/out-of-stock deterministic seed blocker)
- Defect candidates:
  - `ORD-API-014`, `ORD-API-015` return `500`

### 2) Order Payment
- Covered:
  - `ORD-PAY-001` success
  - `ORD-PAY-002` missing idempotency validation
  - `ORD-PAY-003` retry
  - `ORD-PAY-004` pending markers
- Partial/blocked:
  - `ORD-PAY-005` already-paid guard
  - `ORD-PAY-006` cancelled-order guard

### 3) Merchant Processing
- Partial:
  - `MORD-001` merchant list endpoint reachable
- Blocked:
  - `MORD-API-001..004` remain `FORBIDDEN_SCOPE`
  - `MORD-API-005` created order not visible in merchant list

### 4) Admin Tracking / Ops
- Blocked:
  - `AORD-API-001..004`, `AORD-OPS-001..002` return `401` with current account
- Unlock path:
  - provide `API_ADMIN_USER` + `API_ADMIN_PASS` with actual admin role

### 5) Cancellation / Notification / Support
- Cancellation:
  - `ORD-CAN-001` contract path reachable (controlled non-5xx)
  - `ORD-CAN-002..004` still blocked by lifecycle determinism
- Notification:
  - `NOTI-ORD-001` executed but no deterministic order event in feed
  - `NOTI-ORD-002..006` blocked by event/lifecycle determinism

## Next unlock actions
1. Provide admin-capable credentials via env (`API_ADMIN_USER`, `API_ADMIN_PASS`) and rerun admin slice.
2. Provide merchant account that owns created-order store context for transition success-path.
3. Add deterministic second store+sku seed to unlock cross-store tests (`ORD-API-008`, `ORD-API-017`).
4. Capture deterministic paid/cancelled order seeds to unlock `ORD-PAY-005/006` and deeper cancellation checks.
