# API Regression Health Snapshot (2026-03-11, Admin Account Run)

## Scope
- Source artifacts:
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.failed.json`
- Run totals: `total=97`, `passed=85`, `failed=7`, `skipped=5`

## Module Health Summary
| Module | Health | Evidence | Notes |
|---|---|---|---|
| `auth` | Stable | 8 pass, 0 fail, 0 skipped | Core auth checks are stable. |
| `searches` | Stable | 11 pass, 0 fail, 0 skipped | Positive/negative coverage stable. |
| `organization` | Stable | 7 pass, 0 fail, 0 skipped | Current behavior aligns with suite expectations. |
| `notification` | Stable | 6 pass, 0 fail, 0 skipped | Stable in admin run. |
| `posts` | Stable | 8 pass, 0 fail, 0 skipped | Seed hardening is effective in this run. |
| `news` | Partial (seed) | 3 pass, 0 fail, 1 skipped | `NEWS-003` skipped: `/news` returned empty paged data, no slug seed. |
| `store` | Backend Defect | 8 pass, 3 fail, 1 skipped | Active defects: `STO-009`, `STO-011`, `STO-012`; `STO-010` is seed-blocked (not defect). |
| `orders` | Partial (scope/account) | 3 pass, 2 fail, 1 skipped | `ORD-003`, `ORD-API-004` failed with `FORBIDDEN_SCOPE` under admin account. |
| `merchant-orders` | Partial (state/scope) | pass + deterministic skips | Follow-up lifecycle still precondition-dependent. |
| `admin-orders` | Executable | 3 pass, 0 fail, 0 skipped | `AORD-001`, `AORD-API-001`, `AORD-API-002` all pass. |
| `category-admin` | Executable | 6 pass, 0 fail, 0 skipped | `CATADM-001..004` pass; module now executing with admin access. |
| `dashboard` | Executable | 7 pass, 0 fail, 0 skipped | `DASH-001..006` pass in admin run. |
| `member` | Partial (backend defect present) | 4 pass, 1 fail, 0 skipped | `MEMBER-001` fails with backend mapping/configuration `500`. |
| `store-category-admin` | Partial (backend defect present) | 5 pass, 1 fail, 0 skipped | `STCATADM-004` invalid-id path returns `500`. |
| `payments` | Stable (thin) | 1 pass, 0 fail, 0 skipped | Single read check (`PAY-001`) passes. |
| `ordering-policy` | Stable (thin) | 1 pass, 0 fail, 0 skipped | Single read check (`POL-001`) passes. |

## Modules Promoted From Blocked to Executable
- `admin-orders`
- `category-admin`
- `dashboard`
- `member` (partial; list endpoint still defective)
- `store-category-admin` (partial; invalid-id endpoint still defective)

## Defect vs Non-Defect Classification

### Confirmed Backend Defects
- `STO-009`: `GET /api/v1/store/999999999` -> `500` (expected controlled `400/404`)
- `STO-011`: `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` -> `500`
- `STO-012`: `GET /api/v1/store/collections` -> `500` (`Sequence contains no elements.`)
- `MEMBER-001`: `GET /api/v1/member/list` -> `500` (mapping/configuration error)
- `STCATADM-004`: `GET /api/v1/store-category/admin/detail/999999999` -> `500`

### Scope/Account Mismatch (Not Backend Defect)
- `ORD-003`: `GET /api/v1/orders/{id}` -> `400 FORBIDDEN_SCOPE` under admin account
- `ORD-API-004`: `GET /api/v1/orders/{id}` -> `400 FORBIDDEN_SCOPE` under admin account
- Interpretation: account scope/ownership mismatch for the target order; not a transport/framework issue.

### Deterministic Seed Blockers (Not Backend Defect)
- `NEWS-003`: skipped because `/news` returned no records with a detail-route-compatible slug.
- `STO-010`: skipped because stable uniqueId seed is unavailable in current data shape.

## Recommended Next Step
Prioritize backend defect remediation validation for:
1. Store invalid/not-found and collections handling (`STO-009`, `STO-011`, `STO-012`)
2. Member list mapping/configuration (`MEMBER-001`)
3. Store-category invalid detail path (`STCATADM-004`)

After backend fixes, rerun admin regression and then re-evaluate Order detail checks with a scope-matching account for `ORD-003` and `ORD-API-004`.

Execution checklist reference:
- `docs/findings/backend_defect_verification_checklist_2026-03-11.md`
