# Order Manual-Proven Realistic Automation Strategy

## Purpose
Shift Order automation from seed-heavy historical lookup to journey-owned runtime orchestration that mirrors real manual validation.

## Strategy
- Build state by behavior first (`create -> pay -> act -> verify`).
- Use fresh order(s) per journey to avoid cross-branch pollution.
- Keep historical seeds only as fallback for hard-to-orchestrate states.
- Keep defect detection strict; do not downgrade known `500` defects.

## Journey map

| Journey | Primary Cases | Current State | Notes |
|---|---|---|---|
| J1 Customer create/detail/history | `ORD-API-001`, `004`, `009`, `020` | Covered | Uses fresh created order and verifies detail/list consistency. |
| J2 Customer payment intent | `ORD-PAY-001..004`, `007`, `008` | Partial | Intent/retry/verify/wallet contract is proven; full settlement completion still partial. |
| J3 Customer cancellation/actions | `ORD-CUS-001..004`, `ORD-CAN-001..003` | Partial | Controlled statuses are proven; timeline-specific cancel mapping remains blocked (`ORD-CAN-004`). |
| J4 Merchant visibility | `MORD-API-005`, `MORD-API-008` | Covered | Merchant list/detail sees scenario-created order. |
| J5 Merchant accept/reject | `MORD-API-001`, `MORD-API-002` | Partial | Executable with controlled statuses; deterministic `accept=200` precondition not yet proven. |
| J6 Merchant arrived/complete/no-show | `MORD-API-003`, `004`, `006`, `007` | Blocked/Partial | Precondition gated by accept result and lifecycle state. |
| J7 Admin monitoring/support | `AORD-API-001..004`, `AORD-OPS-001..002` | Covered | Admin list/detail/timeline markers are executable and passing. |
| J8 Reservation/preorder variants | `ORD-API-021`, `022`, `023`, `028` | Partial | `ORD-API-022` currently fails as backend defect (past arrival accepted). |
| J9 Multi-item/note/idempotency | `ORD-API-024..027` | Covered/Partial | Core behavior proven; depends on second SKU in same store. |
| J10 Add-on guard | `ORD-ADDON-001`, `002` | Partial | Guard behavior proven; positive Arrived/Completed add-on path is not deterministic yet. |

## Base deterministic inputs
- `storeId=9768`
- `skuId=14`
- second SKU in same store (`skuId=15`) for multi-item/idempotency mismatch checks
- account scopes:
  - customer: `API_USER/API_PASS`
  - merchant: `API_MERCHANT_USER/API_MERCHANT_PASS`
  - admin: `API_ADMIN_USER/API_ADMIN_PASS`

## Current fallback-seed areas
- store uniqueId lookup (`STO-010`)
- second store + active SKU (`ORD-API-008`, `ORD-API-017`)
- closed/ordering-disabled store and disabled/out-of-stock SKU
- deterministic notification correlation (`NOTI-ORD-*`)
- scheduler/SLA job windows (`ORD-JOB-*`)

## Execution command
```powershell
$env:API_BASE_URL="http://192.168.1.103:19066"
$env:API_USER="tieuphiphi020103+71111@gmail.com"
$env:API_PASS="Thien123$"
$env:API_MERCHANT_USER="tieuphiphi020103+71111@gmail.com"
$env:API_MERCHANT_PASS="Thien123$"
$env:API_ADMIN_USER="admin@gmail.com"
$env:API_ADMIN_PASS="123"
$env:API_STORE_ID="9768"
$env:API_ORDER_STORE_ID="9768"
$env:API_ORDER_SKU_ID="14"
.\scripts\run_api_regression.ps1
```

## Current defect visibility policy
These remain strict failures while unresolved:
- `STO-009`, `STO-011`
- `ORD-API-014`, `ORD-API-015`, `ORD-API-022`
- `MEMBER-001`
- `STCATADM-004`
