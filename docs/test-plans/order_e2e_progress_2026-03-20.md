# Order E2E Automation Progress (2026-03-20)

Run snapshot used for this note:
- `total=166`
- `passed=131`
- `failed=7`
- `skipped=28`

## Flow status (evidence-based)

### Order Creation
- `covered`
- Proven with scenario-owned order creation (`ORD-API-001`) and consistency checks (`ORD-API-004`, `ORD-API-009`, `ORD-API-020`).
- Negative contract coverage is broad and stable (`ORD-API-002/003/006/007/010/011/012/016`).

### Order Payment
- `partial`
- Core intent/retry/verify/wallet endpoints are executable and passing (`ORD-PAY-001..008`).
- Full payment-completion settlement lifecycle is not yet deterministic in this runner.

### Customer Actions and Cancellation
- `partial`
- `ORD-CUS-001..004` are executable with controlled-status assertions.
- `ORD-CAN-001..003` are executable; `ORD-CAN-004` remains blocked by timeline mapping determinism.

### Merchant Processing
- `partial`
- Merchant list/detail visibility is now proven (`MORD-API-005`, `MORD-API-008`).
- `accept`/`reject` are executable with controlled status (`MORD-API-001/002`).
- `mark-arrived`/`complete`/extended merchant branch remain precondition-gated until deterministic `accept=200` orchestration is proven.

### Admin Tracking and Ops
- `covered`
- Admin list/detail/visibility/support paths are passing (`AORD-API-001..004`, `AORD-OPS-001..002`).

### Notification and Runtime Jobs
- `blocked`
- Notification correlation for order lifecycle events is not deterministic (`NOTI-ORD-*`).
- Job/SLA/caveat checks remain intentional blockers (`ORD-JOB-*`, `ORD-CAVEAT-*`).

## Current blockers to unlock next
1. Deterministic second-store + SKU seed (`ORD-API-008`, `ORD-API-017`).
2. Deterministic closed/disabled store and SKU seeds (`ORD-API-018`, `ORD-API-019`).
3. Deterministic merchant lifecycle branch where `accept` returns `200`.
4. Deterministic notification correlation key (`orderId`/eventCode mapping) in payload.
5. Timeline assertion mapping for `ORD-CAN-004`.

## Defects that remain active (not blockers)
- `STO-009`, `STO-011`
- `ORD-API-014`, `ORD-API-015`, `ORD-API-022`
- `MEMBER-001`
- `STCATADM-004`
