# Order Traceability

## Requirement-to-Test Mapping (Initial)

| Requirement ID | Module | Endpoint | Testcase ID | Current Integration | Status | Notes |
|---|---|---|---|---|---|---|
| `REQ-ORD-PAY-001` | `payments` | `GET /api/v1/payments/methods` | `PAY-001` | `run_api_regression.ps1` | Covered | Safe read-only check. |
| `REQ-ORD-AORD-001` | `admin-orders` | `GET /api/v1/admin/orders` | `AORD-001` | `run_api_regression.ps1` | Partial | Admin-role dependent; unauthorized becomes `SKIPPED`. |
| `REQ-ORD-MORD-001` | `merchant-orders` | `GET /api/v1/merchant/orders` | `MORD-001` | `run_api_regression.ps1` | Partial | Merchant-role dependent; unauthorized becomes `SKIPPED`. |
| `REQ-ORD-ORD-001` | `orders` | `POST /api/v1/orders` | `ORD-001` | `run_api_regression.ps1` | Partial | Uses safe body when available; can be skipped if required payload has no example. |
| `REQ-ORD-ORD-003` | `orders` | `GET /api/v1/orders/{id}` | `ORD-003` | `run_api_regression.ps1` | Partial | Requires inferred `orderId` seed. |
| `REQ-ORD-MORD-003` | `merchant-orders` | `POST /api/v1/merchant/orders/{id}/accept` | `MORD-003` | `run_api_regression.ps1` | Partial | Requires `orderId`; merchant-role dependent. |
| `REQ-ORD-POL-001` | `ordering-policy` | `GET /api/v1/ordering-policy/store/{storeId}` | `POL-001` | `run_api_regression.ps1` | Partial | Requires inferred `storeId` seed; fallback to store module seed. |

## Planned IDs in Repository Assets

- `ORD-001..ORD-010`
- `MORD-001..MORD-008`
- `AORD-001..AORD-004`
- `POL-001..POL-004`
- `POLADM-001..POLADM-005`
- `ADDPAY-001..ADDPAY-002`
- `PAY-001`

## Status Semantics

- `Covered`: integrated and executable without special seeds/roles.
- `Partial`: integrated but depends on role or seed.
- `Pending`: defined in case assets but not wired into runner yet.
