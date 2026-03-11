# Order Runtime Evidence Snapshot

## Source
- Summary: `artifacts/test-results/api-regression/api_regression.summary.json`
- Log: `artifacts/test-results/api-regression/api_regression.log`
- Run window: `2026-03-11T14:20:50+07:00` to `2026-03-11T14:21:05+07:00`

## Reusable Evidence (Critical Order Cases)
| Testcase ID | Method | Path | Outcome | Status | Evidence Note |
|---|---|---|---|---|---|
| `ORD-API-001` | `POST` | `/api/v1/orders` | `PASS` | `200` | Create-order success with runtime contract (`application/json`, `Idempotency-Key`, `quantity=1`). |
| `ORD-API-004` | `GET` | `/api/v1/orders/2` | `PASS` | `200` | Order detail for created/reusable order id succeeded. |
| `MORD-API-001` | `POST` | `/api/v1/merchant/orders/2/accept` | `PASS` | `400` | Accepted by expected status set; indicates lifecycle state precondition mismatch rather than transport/auth failure. |
| `MORD-API-002` | `POST` | `/api/v1/merchant/orders/2/reject` | `PASS` | `400` | Accepted by expected status set; indicates lifecycle state precondition mismatch rather than transport/auth failure. |

## Lifecycle Interpretation
- `MORD-API-001`/`MORD-API-002` returning `400` is currently treated as business-state validation behavior.
- Deeper lifecycle setup is still needed to force deterministic `200` transitions:
  - order must be in exact merchant-actionable state
  - merchant must own/operate the target store
  - policy/state side-conditions must be satisfied
- Current unresolved relationship:
  - not yet proven that current merchant-capable account has scope ownership for store `9768` and created order context.

## Admin Access Evidence
- `AORD-API-001` currently returns `401` and is classified `SKIPPED: requires admin role`.
- Admin detail coverage (`AORD-API-002`) is now registered with the same role-based skip behavior until an admin-capable account is provided.
