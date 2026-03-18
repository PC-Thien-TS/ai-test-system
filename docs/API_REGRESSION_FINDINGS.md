# API Regression Findings (Latest Admin Evidence)

## Scope
- Evidence source:
  - `artifacts/test-results/api-regression/api_regression.failed.json`
  - `artifacts/test-results/api-regression/api_regression.summary.json`
- This document separates backend defects from scope/account mismatches and seed blockers.

## Confirmed Backend Defects

| Testcase | Endpoint | Observed | Expected | Classification |
|---|---|---|---|---|
| `STO-009` | `GET /api/v1/store/999999999` | `500` | `400/404` | Backend defect |
| `STO-011` | `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` | `500` | `400/404` | Backend defect |
| `STO-012` | `GET /api/v1/store/collections` | `500` (`Sequence contains no elements.`) | `200/400/404/415` | Backend defect |
| `MEMBER-001` | `GET /api/v1/member/list` | `500` (mapping/configuration error) | `200` | Backend defect |
| `STCATADM-004` | `GET /api/v1/store-category/admin/detail/999999999` | `500` | `400/404` | Backend defect |

## Scope/Account Mismatch (Not Backend Defect)

| Testcase | Endpoint | Observed | Classification |
|---|---|---|---|
| `ORD-003` | `GET /api/v1/orders/{id}` | `400 FORBIDDEN_SCOPE` | Scope/account mismatch |
| `ORD-API-004` | `GET /api/v1/orders/{id}` | `400 FORBIDDEN_SCOPE` | Scope/account mismatch |

Notes:
- Under admin account context, order visibility for target `orderId` is scope-constrained.
- These are not framework issues and should not be tracked as backend defects.

## Deterministic Seed/Data Blockers (Not Backend Defect)

| Testcase | Status | Reason |
|---|---|---|
| `NEWS-003` | `SKIPPED` | `/news` list returns empty paged data; no slug/key available for detail route seed. |
| `STO-010` | `SKIPPED` | No stable store uniqueId seed available in current dataset. |

## Module Promotion from Latest Admin Run
- Executable now: `admin-orders`, `category-admin`, `dashboard`
- Partial but executable: `member`, `store-category-admin`

## Recommended Next Actions
1. Fix backend defects: `STO-009`, `STO-011`, `STO-012`, `MEMBER-001`, `STCATADM-004`.
2. Re-run admin regression and confirm defect closure with stable non-`5xx` behavior.
3. Re-run order detail with account/order scope alignment before reclassifying `ORD-003` and `ORD-API-004`.
4. Use `docs/findings/backend_defect_verification_checklist_2026-03-11.md` as the execution checklist for closure verification.
