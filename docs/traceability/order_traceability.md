# Order Traceability

## Objective
Provide requirement-to-test traceability for current Order-first automation with explicit execution state.

## Latest evidence baseline
- Full regression on 2026-03-20: `total=166`, `passed=131`, `failed=7`, `skipped=28`.
- Source: `artifacts/test-results/api-regression/api_regression.summary.json`.

## Requirement-to-Test Mapping (Current)

| Requirement ID | Module | Endpoint/Flow | Testcase IDs | Runner Integration | Status | Notes |
|---|---|---|---|---|---|---|
| `ORDER-REQ-001` | ordering | Create order happy path | `ORD-API-001` | `run_api_regression.ps1` | Covered | Runtime-aligned create contract with idempotency header and deterministic seed. |
| `ORDER-REQ-002` | ordering | Create order media-type validation | `ORD-API-002` | `run_api_regression.ps1` | Covered | `415` check is stable. |
| `ORDER-REQ-003` | ordering | Create-order required-field validation | `ORD-API-003`, `006`, `010`, `011`, `012`, `016` | `run_api_regression.ps1` | Covered | Controlled `4xx` paths. |
| `ORDER-REQ-004` | ordering | Order detail + consistency | `ORD-API-004`, `020` | `run_api_regression.ps1` | Covered | Scenario-created order detail consistency is proven in latest run. |
| `ORDER-REQ-005` | ordering | Idempotency same-key replay | `ORD-API-005`, `027` | `run_api_regression.ps1` | Partial | Same payload and changed payload replay checks are wired. |
| `ORDER-REQ-006` | ordering | Reservation/preorder variants | `ORD-API-021`, `022`, `023`, `028` | `run_api_regression.ps1` | Partial | Runtime preconditions can block happy-path proof. |
| `ORDER-REQ-007` | ordering | Multi-item and note behavior | `ORD-API-024`, `025`, `026` | `run_api_regression.ps1` | Covered | Multi-item note/null-note and duplicate SKU-line behavior are executable with deterministic same-store seeds. |
| `ORDER-REQ-008` | ordering | Cross-store and availability guards | `ORD-API-008`, `017`, `018`, `019` | `run_api_regression.ps1` | Blocked | Deterministic alt-store and gating seeds still missing. |
| `ORDER-REQ-009` | ordering | Pricing preview contract | `ORD-API-029` | `run_api_regression.ps1` | Partial | Endpoint wired; auth/seed dependent. |
| `PAY-REQ-001` | payments | Payment intent core | `ORD-PAY-001`, `003`, `004` | `run_api_regression.ps1` | Partial | Core executable with order seed and scope. |
| `PAY-REQ-002` | payments | Payment validation and guards | `ORD-PAY-002`, `005`, `006` | `run_api_regression.ps1` | Partial | Some state guards remain seed dependent. |
| `PAY-REQ-003` | payments | Wallet and verify endpoints | `ORD-PAY-007`, `008` | `run_api_regression.ps1` | Partial | Wired; requires deterministic order/auth seeds. |
| `ORDER-REQ-010` | ordering | Customer post-order actions | `ORD-CUS-001`, `002`, `003`, `004` | `run_api_regression.ps1` | Partial | State and scope dependent. |
| `ORDER-REQ-011` | ordering | Cancellation/dispute paths | `ORD-CAN-001..004` | `run_api_regression.ps1` | Partial | Deeper states still need deterministic paid/completed seeds. |
| `ORDER-REQ-012` | ordering | Add-on behavior | `ORD-ADDON-001`, `002` | `run_api_regression.ps1` | Partial | Controlled-status assertions implemented. |
| `MORD-REQ-001` | merchant_orders | Merchant order visibility | `MORD-001`, `MORD-API-005`, `MORD-API-008` | `run_api_regression.ps1` | Covered | Merchant list/detail visibility is proven for scenario-owned order context. |
| `MORD-REQ-002` | merchant_orders | Merchant lifecycle actions | `MORD-API-001..004`, `006`, `007` | `run_api_regression.ps1` | Partial | Accept/reject are executable; deeper transitions remain precondition-gated until deterministic accept=200 branch exists. |
| `AORD-REQ-001` | admin_orders | Admin order list/detail | `AORD-API-001..005` | `run_api_regression.ps1` | Covered | Admin token path is separate and executable. |
| `AORD-REQ-002` | admin_orders | Admin dispute monitoring | `AORD-API-006`, `007`, `008` | `run_api_regression.ps1` | Partial | Dispute detail/resolve need deterministic dispute id. |
| `AORD-REQ-003` | admin_orders | Admin support visibility | `AORD-OPS-001`, `002` | `run_api_regression.ps1` | Covered | Support-relevant fields are asserted in admin detail payload. |
| `ORDER-REQ-013` | ordering | Notification event mapping | `NOTI-ORD-001..006` | `run_api_regression.ps1` | Blocked | Event correlation keys are not deterministic yet. |
| `ORDER-REQ-014` | ordering | Runtime jobs and caveats | `ORD-JOB-001..004`, `ORD-CAVEAT-001..004` | `run_api_regression.ps1` | Blocked | Tracked with explicit blockers pending deterministic job orchestration. |

## Status Semantics
- `Covered`: integrated and regularly executable in current environment.
- `Partial`: integrated but depends on auth, scope, runtime state, or deterministic seeds.
- `Blocked`: integrated as explicit blocked checkpoint; prerequisites not yet deterministic.
