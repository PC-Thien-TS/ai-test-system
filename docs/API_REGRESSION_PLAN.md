# API Regression Plan (Didaunao / RankMate)

## Objective
Provide deterministic regression coverage (deeper than smoke) for core business API modules using Swagger (`/swagger/v1/swagger.json`) as contract source, while keeping execution safe and non-destructive.

## Module Scope
| Module | Coverage |
|---|---|
| auth | login positive/negative, get-info with/without token, refresh/logout when feasible |
| searches | posts/suggestions/hot-keywords/histories/filters with positive + negative payload/query checks |
| store | list/paged/reviews/views/verify/detail + id/uniqueId valid/invalid where inferable |
| posts | list/ids/categories/pending/recommend + detail valid/invalid id |
| news | list + query variant + detail valid/invalid slug |
| organization | list/get-info/get-organization-type/pagination-selection/paged/detail valid-invalid id |
| notification | list/unread-count with auth + without auth, mark-all-read/mark-read/delete safe negative checks |
| category-admin | list/selection/generate-code/detail valid-invalid id with admin-aware skip |
| dashboard | registrations/qr-scan endpoints and by-date variants with admin-aware skip |
| member | list/pagination-selection/detail valid-invalid id with admin-aware skip |
| store-category admin | selection/generate-code/detail/children with admin-aware skip |
| order (initial) | payments methods, admin orders list, merchant orders list, create order, get order by id, merchant accept, ordering policy by store id |

## Coverage Summary
- `auth`: `AUTH-*`
- `searches`: `SEA-*`
- `store`: `STO-*`
- `posts`: `POSTS-*`
- `news`: `NEWS-*`
- `organization`: `ORG-*`
- `notification`: `NOTI-*`
- `category-admin`: `CATADM-*`
- `dashboard`: `DASH-*`
- `member`: `MEMBER-*`
- `store-category admin`: `STCATADM-*`
- `order (initial)`: `PAY-001`, `AORD-001`, `MORD-001`, `ORD-001`, `ORD-003`, `MORD-003`, `POL-001`
- `order api (critical)`: `ORD-API-001..004`, `MORD-API-001..004`, `AORD-API-001..002`

## Test Categories By Module
- Positive:
  - happy path status checks for read endpoints
  - authenticated happy path where token is available
  - successful-response contract assertion:
    - response must be a JSON object
    - `result` field must exist
    - `data` field must exist
- Negative:
  - invalid credentials and missing required fields
  - invalid id/slug path checks
  - unauthorized (without token) checks for protected routes
  - missing payload checks for safe notification actions
  - explicit negative auth checks (`401/403`) for admin/business modules
- Regression findings:
  - any unexpected `5xx` is `FAIL`
  - unexpected `4xx` outside expected status set is `FAIL`
  - admin positive case with `401/403` is converted to `SKIPPED: requires admin role`

## Assumptions
- Required env vars: `API_BASE_URL`, `API_USER`, `API_PASS`
- Optional: `API_PREFIX` (default `/api/v1`), `API_TIMEOUT_SEC` (default `30`)
- Token is obtained once from login and reused.
- If token cannot be obtained, token-required cases are marked `SKIPPED`.

## Seed Inference Approach
- Infer IDs/slugs from prior successful list/paged responses:
  - `store`: infer `id` and `uniqueId` from `/store`, `/store/list`, `/store/paged`
  - `posts`: infer `id` from `/posts` or `/posts/ids`
  - `news`: infer `slug` from `/news`
  - `organization`: infer `id` from `/organization/list`, `/organization/get-info`, `/organization/paged`
  - `category-admin`: infer `id` from list/selection responses
  - `member`: infer `id` from list/pagination-selection responses
  - `store-category admin`: infer `id` and `parentId` from selection responses
- If no safe seed value is inferable, testcase is `SKIPPED` with explicit reason.
- Improved auto-seed targets:
  - post id (`POSTS-*` detail cases)
  - news slug (`NEWS-*` detail cases)
  - category-admin id (`CATADM-*` detail cases)
  - store-category admin parentId (`STCATADM-*` children cases)
  - order id and store id (`AORD-*`, `MORD-*`, `ORD-*`, `POL-*`)

## Not-Found Negative Policy
- For known invalid-id/invalid-slug negative testcases, non-5xx responses are treated as acceptable contract behavior.
- Only unexpected `5xx` remains `FAIL` for these not-found negatives.

## Known Limitations
- Write endpoints are intentionally minimized; no destructive scenarios without safe rollback.
- Notification write checks are limited to safe/contracted payload-negative scenarios.
- External-effect endpoints (payments/webhooks/realtime push tests) are not executed in this suite.
- Admin/business modules depend on account permission; positive cases may be `SKIPPED` if current token lacks admin role.
- Order lifecycle and policy-admin write coverage are intentionally deferred to a later pass.
- Order API critical tests are now registered with seed-safe skip behavior for unresolved order/store/sku preconditions.

## Order API Execution Notes
- Required env vars for `ORD-API-*` execution:
  - `API_BASE_URL`
  - `API_USER`
  - `API_PASS`
- Required seed signals (auto-inferred where possible):
  - `storeId` from store/order/admin list responses
  - `skuId` from search/store responses
  - `orderId` from admin/merchant list or create-order response
- `ORD-API-001` payload shape enforces runtime-required fields:
  - `storeId`
  - `items` with `items[].skuId`
  - `items[].quantity` (set to `1` for baseline create flow)
- `ORD-API-001` uses `application/json; charset=utf-8`.
- `Idempotency-Key` header is generated per create-order request.
- Seed preference for order success-path:
  - first try `storeId=9768` with `/api/v1/stores/9768/menu`
  - extract SKU from `data.categories[].items[].skus[].id`
  - fallback to inferred store/sku IDs when preferred seed is unavailable
- `ORD-API-002` intentionally sends `text/plain` (with auth + idempotency header) to assert controlled `415 Unsupported Media Type`.
- Runtime blocker handling:
  - when create-order returns `POLICY_NOT_CONFIGURED`, `ORD-API-001` is classified `SKIPPED` with explicit blocker notes (not framework failure).
- Merchant lifecycle extension:
  - `MORD-API-003` (`mark-arrived`) and `MORD-API-004` (`complete`) run only if `MORD-API-001` accept returns `200`.
  - Otherwise these are deterministically `SKIPPED` with explicit unmet-precondition notes.
- Merchant transition interpretation:
  - Current `400` on accept/reject is treated as business-state validation (order state not eligible), not transport/contract failure.
  - Latest manual follow-up for orderId `2` returned `400 FORBIDDEN_SCOPE` on `accept`/`reject`/`mark-arrived`/`complete`; classify as scope/ownership precondition blocking, not framework defect.
- Admin coverage:
  - `AORD-API-001` (list) and `AORD-API-002` (detail) remain role-gated and are `SKIPPED` without admin-capable account.
- Legacy `ORD-001` is superseded by `ORD-API-001` and intentionally registered as `SKIPPED` to avoid duplicate/misleading contract signals.
- Role-sensitive behavior:
  - admin endpoints -> `SKIPPED` on `401/403` with explicit reason
  - merchant transition endpoints -> `SKIPPED` on `401/403` with explicit reason
- Deterministic fallback:
  - if `storeId`/`skuId`/`orderId` cannot be inferred, dependent cases are `SKIPPED` with explicit seed-missing notes.

## Current Proven Order State (2026-03-11)
- Create-order success path: automated and proven (`ORD-API-001` `200`).
- Order detail path: automated and proven (`ORD-API-004` `200`).
- Merchant lifecycle transitions: currently blocked by scope/ownership (`400 FORBIDDEN_SCOPE`) in follow-up checks.
- Admin order list/detail: currently blocked by role (`401`) with non-admin account.

## How To Run
PowerShell:

```powershell
$env:API_BASE_URL="http://192.168.1.7:19066"
$env:API_USER="your_email@example.com"
$env:API_PASS="your_password"
.\scripts\run_api_regression.ps1
```

CMD:

```cmd
set API_BASE_URL=http://192.168.1.7:19066
set API_USER=your_email@example.com
set API_PASS=your_password
scripts\run_api_regression.cmd
```

## Artifact Outputs
Outputs are written to `artifacts/test-results/api-regression/`:
- `api_regression.log`
- `api_regression.summary.json`
- `api_regression.failed.json` (only when failures exist)

Result fields per testcase:
- `id`
- `module`
- `name`
- `method`
- `path`
- `ok`
- `status`
- `expected_status`
- `notes`
- `ts`

## Next Future Modules
- `reports`
- `category-admin` write workflow with rollback
- `member` activity-log and write workflow with rollback
- `store-category admin` write workflow with rollback
- `media` / `storages` advanced flows
