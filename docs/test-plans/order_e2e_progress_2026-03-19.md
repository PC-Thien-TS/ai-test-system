# Order E2E Automation Progress (2026-03-19)

## Flow coverage status

### Order Creation
- `covered`
- Proven in live run with deterministic seed (`storeId=9768`, `skuId=14`), JSON content type, and `Idempotency-Key`.
- Remaining defect checks still fail correctly (`ORD-API-014`, `ORD-API-015`).

### Order Payment
- `partial`
- Payment intent/retry/pending checks are covered.
- Guard checks requiring paid/cancelled deterministic customer-scope seeds remain blocked (`ORD-PAY-005`, `ORD-PAY-006`).

### Merchant Processing
- `partial`
- Endpoints are reachable, but created customer orders are not visible in merchant list for current account/store context.
- `MORD-*` remains `SCOPE_BLOCKER`.

### Admin Tracking / Ops
- `covered`
- `AORD-API-001..004` and `AORD-OPS-001..002` pass with admin account.

### Cancellation
- `partial`
- `ORD-CAN-001` covered with controlled status.
- `ORD-CAN-002` blocked by missing paid seed in customer scope.
- `ORD-CAN-003/004` blocked by completed-order visibility/timeline prerequisites.

### Notification
- `blocked`
- Notification feed currently has no deterministic event correlation for order lifecycle assertions.

## Runtime seed status
- Stable:
  - `storeId=9768`
  - `skuId=14`
  - `lastCreatedOrderId=142`
- Blocked:
  - uniqueId lookup seed for `STO-010`
  - second store + sku seed (`ORD-API-008`, `ORD-API-017`)
  - closed/disabled store and disabled/out-of-stock sku seeds
  - customer-scope paid/cancelled/completed deterministic seeds for deep lifecycle checks

## Immediate next unlock targets
1. Provide merchant account that owns/manages the store used for created orders.
2. Provide deterministic second-store and edge-case sku seeds.
3. Provide deterministic paid/cancelled/completed customer-scope order ids (or deterministic setup flow) for cancellation and notification assertions.
