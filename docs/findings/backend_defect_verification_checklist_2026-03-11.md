# Backend Defect Verification Checklist (2026-03-11)

## Purpose
Provide a clean verification cycle for currently confirmed backend defects from the latest admin-account regression run.

## Preconditions
- Use admin-capable account that produced the latest `97/85/7/5` run.
- Keep regression runner and expectations unchanged before verification.
- Ensure environment variables are set:
  - `API_BASE_URL`
  - `API_USER`
  - `API_PASS`

## Defects Under Verification

| ID | Endpoint | Current Observed | Expected After Fix | Pass Criteria |
|---|---|---|---|---|
| `STO-009` | `GET /api/v1/store/999999999` | `500` | `400` or `404` | No `5xx`; response follows controlled error path. |
| `STO-011` | `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` | `500` | `400` or `404` | No `5xx`; response follows controlled error path. |
| `STO-012` | `GET /api/v1/store/collections` | `500` (`Sequence contains no elements.`) | `200`/`400`/`404`/`415` | No `5xx`; no unhandled empty-sequence exception. |
| `MEMBER-001` | `GET /api/v1/member/list` | `500` mapping/config error | `200` | Endpoint returns successful list response without mapping exception. |
| `STCATADM-004` | `GET /api/v1/store-category/admin/detail/999999999` | `500` | `400` or `404` | No `5xx`; invalid-id path handled safely. |

## Out of Scope for Defect Closure
- `ORD-003`, `ORD-API-004`: `FORBIDDEN_SCOPE` (scope/account mismatch, not backend defect)
- `STO-010`: deterministic seed blocker (missing stable uniqueId seed)
- `NEWS-003`: deterministic seed blocker (no slug seed from `/news` list)

## Verification Steps
1. Run full regression with admin account.
2. Confirm the 5 defect cases above no longer return `5xx`.
3. Confirm defect IDs are absent from `api_regression.failed.json`.
4. Keep scope/seed blockers classified as non-defect.
5. Update health and findings docs only after evidence is captured.

## Evidence to Capture
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json` (or absence of defect IDs)
- `artifacts/test-results/api-regression/api_regression.log`

## Rerun Command
```powershell
$env:API_BASE_URL="http://192.168.1.7:19066"
$env:API_USER="<admin_account>"
$env:API_PASS="<admin_password>"
.\scripts\run_api_regression.ps1
```
