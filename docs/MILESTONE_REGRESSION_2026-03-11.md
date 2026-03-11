# QA Milestone Summary (Regression State 2026-03-11)

## Verified Run Snapshot
- Source: `artifacts/test-results/api-regression/api_regression.summary.json`
- Totals: `total=97`, `passed=85`, `failed=7`, `skipped=5`

## What Is Stable
- Core modules are stable in this milestone:
  - `auth`
  - `searches`
  - `organization`
  - `notification`
  - `posts`
- Admin access is proven executable for:
  - `admin-orders`
  - `category-admin`
  - `dashboard`

## Remaining Backend Defects (5)
- `STO-009` `GET /api/v1/store/999999999` -> `500`
- `STO-011` `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` -> `500`
- `STO-012` `GET /api/v1/store/collections` -> `500`
- `MEMBER-001` `GET /api/v1/member/list` -> `500`
- `STCATADM-004` `GET /api/v1/store-category/admin/detail/{invalidId}` -> `500`

## Non-Defect Blockers (Do Not Track as Backend Defects)
- Scope/account mismatch:
  - `ORD-003` -> `400 FORBIDDEN_SCOPE`
  - `ORD-API-004` -> `400 FORBIDDEN_SCOPE`
- Deterministic seed blockers:
  - `STO-010` -> missing stable `uniqueId` seed
  - `NEWS-003` -> `/news` list has zero records, no slug seed

## Verification Readiness
- Defect verification checklist is prepared:
  - `docs/findings/backend_defect_verification_checklist_2026-03-11.md`
- Health and findings docs are aligned to this run state:
  - `docs/API_REGRESSION_HEALTH_2026-03-11.md`
  - `docs/API_REGRESSION_FINDINGS.md`
