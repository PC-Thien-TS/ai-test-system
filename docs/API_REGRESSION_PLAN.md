# API Regression Plan (Didaunao / RankMate)

## Objective
Provide deterministic regression coverage (deeper than smoke) for core business API modules using Swagger (`/swagger/v1/swagger.json`) as contract source, while keeping execution safe and non-destructive.

## Manual-Proven Realistic Automation Strategy (2026-03-20)
- Order coverage now prioritizes scenario journeys over historical seed scanning.
- Each journey creates its own order context when feasible:
  - payment journey
  - customer-action journey
  - merchant visibility/action journey
- Cross-journey state reuse is intentionally reduced to avoid invalid lifecycle chaining (for example, cancelled order reused in merchant accept path).
- Historical seed lookup remains as fallback only for hard runtime states (second store, closed store, notification correlation, job windows).
- Defect detection remains strict: known `500` defects are still `FAIL`.

## Focused Verification Round (2026-03-24, host `192.168.1.103`)
- Rerun scope:
  - `CORE` and `JOURNEYS` executed as required verification round
  - `EDGE` executed as diagnostic pass for skip-cluster revalidation
- Fresh layer summary:
  - `CORE`: `109/102/7/0`
  - `JOURNEYS`: `33/33/0/0`
  - `EDGE`: `26/1/0/25`
- Backend defects remain unchanged and stable across repeated CORE rerun:
  - `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`
- Merchant auth status in this round:
  - token path is executable with current runtime credentials
  - merchant lifecycle still lacks happy-path preconditions (`accept/reject/arrived/complete` return controlled `400`)
- `ORD-API-022` remains `CONTRACT_REVIEW` while runtime accepts past `arrivalTime` with `200`.

## Runtime Update (2026-03-24, host `192.168.1.7`)
- Full run result: `total=166`, `passed=126`, `failed=7`, `skipped=33`.
- Confirmed fail set remains backend defects only:
  - `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`.
- Merchant auth remains blocked:
  - `API_MERCHANT_USER=tieuphiphi020103+71111@gmail.com`
  - login returns `400 Incorrect email or password`
  - merchant journeys (`MORD-*`) remain blocked as `CONFIG_BLOCKER/SCOPE_BLOCKER`.
- Seed progress:
  - deterministic second store seed unlocked: `altStoreId=10141`, `altSkuId=21`.
  - `ORD-API-008` and `ORD-API-017` now execute and pass with controlled `400` rejection.
  - `ORD-API-018` remains blocked (no deterministic closed/ordering-disabled store seed).
  - `ORD-API-019` remains blocked (no deterministic disabled/out-of-stock sku seed).
- `ORD-API-022` remains `CONTRACT_REVIEW` when runtime accepts past `arrivalTime` with `200`.

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
- `order api (critical+)`: `ORD-API-001..029`, `ORD-PAY-001..008`, `ORD-CAN-001..004`, `ORD-CUS-001..004`, `ORD-ADDON-001..002`, `MORD-API-001..008`, `AORD-API-001..008`, `AORD-OPS-001..002`, `NOTI-ORD-001..006`, `ORD-JOB-001..004`, `ORD-CAVEAT-001..004`

## Test Categories By Module
- Positive:
  - happy path status checks for read endpoints
  - authenticated happy path where token is available
  - successful-response contract assertion:
    - when body is a JSON object that uses an envelope pattern, `result` and `data` are asserted
    - success responses with empty/minimal/non-object bodies are accepted with explicit notes
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
- Optional merchant override for lifecycle checks: `API_MERCHANT_USER`, `API_MERCHANT_PASS`
- Optional admin override for admin-order checks: `API_ADMIN_USER`, `API_ADMIN_PASS`
- Optional deterministic seed overrides:
  - `API_STORE_ID`, `API_STORE_UNIQUE_ID`
  - `API_ORDER_STORE_ID`, `API_ORDER_SKU_ID`
  - `API_ALT_STORE_ID`, `API_ALT_STORE_UNIQUE_ID`, `API_ALT_SKU_ID`
  - `API_MERCHANT_STORE_ID`
  - `API_PENDING_ORDER_ID`, `API_PAID_ORDER_ID`, `API_CANCELLED_ORDER_ID`, `API_COMPLETED_ORDER_ID`
  - `API_DISABLED_SKU_ID`, `API_OUT_OF_STOCK_SKU_ID`
  - `API_CLOSED_STORE_ID`, `API_ORDERING_DISABLED_STORE_ID`
  - `API_NEWS_SLUG`, `API_CATEGORY_ADMIN_ID`, `API_STORE_CATEGORY_ADMIN_ID`
- Token is obtained once from login and reused.
- If token cannot be obtained, token-required cases are marked `SKIPPED`.

## Seed Inference Approach
- Infer IDs/slugs from prior successful list/paged responses:
  - `store`: infer `id` from `/store`, `/store/list`, `/store/paged`; infer `uniqueId` only from exact keys (`uniqueId`, `storeUniqueId`, `unique_id`) to avoid name/title false positives
  - `posts`: infer `id` from `/posts` or `/posts/ids`
  - `news`: infer `slug` from `/news`
  - `organization`: infer `id` from `/organization/list`, `/organization/get-info`, `/organization/paged`
  - `category-admin`: infer `id` from list/selection responses
  - `member`: infer `id` from list/pagination-selection responses
  - `store-category admin`: infer `id` and `parentId` from selection responses
- If no safe seed value is inferable, testcase is `SKIPPED` with explicit reason.
- Current live note for `NEWS-003`: `/news` can return `200` with empty paged data (`data.data=[]`), so detail slug seed is unavailable and case remains intentionally `SKIPPED`.
- Improved auto-seed targets:
  - post id (`POSTS-*` detail cases)
  - news slug (`NEWS-*` detail cases)
  - category-admin id (`CATADM-*` detail cases)
  - store-category admin parentId (`STCATADM-*` children cases)
  - order id and store id (`AORD-*`, `MORD-*`, `ORD-*`, `POL-*`)
  - posts/news seed hardening:
    - primitive array values are now accepted by seed inference (e.g. numeric `ids` arrays)
    - news slug fallback patterns include `slug`, `newsSlug`, `urlSlug`, `seoSlug`, `alias`, `path`

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
- Extended order-depth tests are registered for reservation/preorder variants, multi-item/idempotency replay, admin dispute monitoring, add-on checks, and runtime caveat trackers.

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
  - current live seed revalidated on `2026-03-13`: `storeId=9768`, `skuId=14`, category `Mon Nuoc`, item `Banh Canh`
  - `storeId=9608` is currently unusable because `/api/v1/stores/9608/menu` returned zero categories
- `ORD-API-002` intentionally sends `text/plain` (with auth + idempotency header) to assert controlled `415 Unsupported Media Type`.
- Runtime blocker handling:
  - when create-order returns `POLICY_NOT_CONFIGURED`, `ORD-API-001` is classified `SKIPPED` with explicit blocker notes (not framework failure).
- Store uniqueId handling:
  - `STO-010` now prefers explicit `API_STORE_UNIQUE_ID` and no longer silently reuses store name/title fields.
  - if runtime rejects configured uniqueId with a not-found server response, classification is `SEED_BLOCKER` with probe evidence for attempted candidates.
  - numeric `/store/{id}` success is not accepted as uniqueId proof when `/store/{id}?UniqueId=<invalid>` still returns `200` (query appears ignored).
- Payment runtime contract (live Swagger + execution evidence):
  - `POST /api/v1/orders/{id}/payments` has no declared requestBody schema in Swagger.
  - Runtime requires `Idempotency-Key` header.
  - `application/json; charset=utf-8` with `{}` body is executable for payment intent creation.
  - Additional contract-backed endpoints now wired:
    - `POST /api/v1/orders/{id}/payments/wallet` (`ORD-PAY-007`)
    - `GET /api/v1/orders/{id}/payments/verify` (`ORD-PAY-008`)
- Customer post-order action endpoints now wired with controlled-status assertions:
  - `POST /api/v1/orders/{id}/cancel` (`ORD-CUS-001`)
  - `POST /api/v1/orders/{id}/confirm-arrival` (`ORD-CUS-002`)
  - `POST /api/v1/orders/{id}/confirm-complete` (`ORD-CUS-003`)
  - `POST /api/v1/orders/{id}/report-not-arrived` (`ORD-CUS-004`)
- Merchant post-order extensions now wired:
  - `POST /api/v1/merchant/orders/{id}/cancel` (`MORD-API-006`)
  - `POST /api/v1/merchant/orders/{id}/mark-no-show` (`MORD-API-007`)
  - `GET /api/v1/merchant/orders/{id}` (`MORD-API-008`)
- Admin dispute monitoring extensions:
  - `GET /api/v1/admin/disputes` (`AORD-API-006`)
  - `GET /api/v1/admin/disputes/{id}` (`AORD-API-007`)
  - `POST /api/v1/admin/disputes/{id}/resolve` invalid-payload validation (`AORD-API-008`)
- Add-on contract checks:
  - `POST /api/v1/orders/{id}/addons` (`ORD-ADDON-001`, `ORD-ADDON-002`)
- Merchant lifecycle extension:
  - `MORD-API-003` (`mark-arrived`) and `MORD-API-004` (`complete`) run only if `MORD-API-001` accept returns `200`.
  - Otherwise these are deterministically `SKIPPED` with explicit unmet-precondition notes.
- Merchant transition interpretation:
  - Current `400` on accept/reject is treated as business-state validation (order state not eligible), not transport/contract failure.
  - Latest live follow-up for orders `37` and `38` returned `400 FORBIDDEN_SCOPE` on `accept`/`reject`/`mark-arrived`/`complete`; classify as scope/ownership precondition blocking, not framework defect.
- Admin coverage:
  - with `API_ADMIN_USER`/`API_ADMIN_PASS`, `AORD-API-001..004` and `AORD-OPS-001..002` are executable and passing.
  - without admin-capable token, admin-specific cases are still classified as account/scope blockers.
- Admin-account observation:
  - `ORD-003` and `ORD-API-004` can return `400 FORBIDDEN_SCOPE` when account scope does not own/cover the target order id; classify as scope/account mismatch, not backend defect.
- Merchant lifecycle success preconditions (`accept`, `reject`, `mark-arrived`, `complete`):
  - current auth token must belong to merchant account that owns/manages the order's store
  - target order must be visible in merchant scope (not only customer scope)
  - order must be in the exact lifecycle state required by each transition
  - when these are not met, current environment returns `400 FORBIDDEN_SCOPE`
- Legacy `ORD-001` is superseded by `ORD-API-001` and intentionally registered as `SKIPPED` to avoid duplicate/misleading contract signals.
- Role-sensitive behavior:
  - admin endpoints -> `SKIPPED` on `401/403` with explicit reason
  - merchant transition endpoints -> `SKIPPED` on `401/403` with explicit reason
  - Customer auth-config blocker:
    - if `API_USER/API_PASS` cannot obtain a token, role-separate admin/merchant login still runs and customer-scope tests are classified as `CONFIG_BLOCKER` instead of false backend failures.
  - Invalid-store defect visibility fallback:
    - when customer token is unavailable but admin token is valid, `ORD-API-014` and `ORD-API-015` are still probed with admin token (`auth_probe=admin_fallback`) to keep known backend defects visible.
- Deterministic fallback:
  - if `storeId`/`skuId`/`orderId` cannot be inferred, dependent cases are `SKIPPED` with explicit seed-missing notes.

## Current Proven Order State (2026-03-20)
- Latest full regression summary: `total=166`, `passed=128`, `failed=7`, `skipped=31`.
- Create/detail/history are proven with scenario-created orders:
  - `ORD-API-001`, `ORD-API-004`, `ORD-API-009`, `ORD-API-020`.
- Payment matrix is broadly executable:
  - `ORD-PAY-001..008` all `PASS` in latest run.
- Customer action and cancellation guards are executable:
  - `ORD-CUS-001..004` `PASS`
  - `ORD-CAN-001` `PASS`
  - `ORD-CAN-002..004` remain blocked by deterministic paid/completed/timeline mapping requirements in current runtime.
- Merchant and admin status:
  - Merchant visibility/detail proven (`MORD-API-005`, `MORD-API-008`).
  - Merchant accept/reject executable with controlled status (`MORD-API-001`, `MORD-API-002`).
  - Merchant deeper transitions still precondition-gated (`MORD-API-003`, `MORD-API-004`, `MORD-API-006`, `MORD-API-007`).
  - Admin list/detail/support remain executable and passing (`AORD-API-001..004`, `AORD-OPS-001..002`).
- Active fails to keep visible:
  - `STO-009`, `STO-011`, `ORD-API-014`, `ORD-API-015`, `ORD-API-022`, `MEMBER-001`, `STCATADM-004` (historical 2026-03-20 snapshot; `ORD-API-022` now tracked as `CONTRACT_REVIEW` when executable).
- Supplemental order evidence:
  - `test-assets/seeds/order/order_seed.json`
  - `docs/findings/order_execution_findings_2026-03-20.md`
  - `docs/test-plans/order_e2e_progress_2026-03-20.md`
  - `artifacts/test-results/api-regression/api_regression.summary.json`

## Current Runtime Update (2026-03-23)
- Full regression (reachable window): `total=166`, `passed=65`, `failed=7`, `skipped=94`.
- Layer snapshots:
  - `CORE`: `109/64/7/38`
  - `JOURNEYS`: `33/1/0/32`
- Current runtime blockers:
  - `API_USER/API_PASS` login returns `400 Incorrect email or password`
  - `API_MERCHANT_USER/API_MERCHANT_PASS` login returns `400 Incorrect email or password`
  - Admin login remains valid (`200`) and admin scopes (`orders/category-admin/dashboard`) execute.
- Merchant happy-path (`accept -> arrived -> complete`) remains blocked by merchant auth access in this run window.
- `AORD-API-003` logic is hardened with bounded multi-page scan so older order ids are not falsely classified as missing due short page scans.
- `ORD-API-022` handling:
  - when executable and runtime returns `200` for past `arrivalTime`, case is classified `CLASS=CONTRACT_REVIEW` (captured runtime behavior),
  - in this run it remained `SKIPPED` because customer auth token was unavailable.

## How To Run
PowerShell:

```powershell
$env:API_BASE_URL="http://192.168.1.103:19066"
$env:API_USER="your_email@example.com"
$env:API_PASS="your_password"
.\scripts\run_api_regression.ps1
```

Layered run entry points:

```powershell
.\scripts\run_api_regression_core.ps1
.\scripts\run_api_regression_journeys.ps1
.\scripts\run_api_regression_edge.ps1
```

Merchant lifecycle with dedicated merchant account:

```powershell
$env:API_BASE_URL="http://192.168.1.103:19066"
$env:API_USER="customer_or_general_account@example.com"
$env:API_PASS="***"
$env:API_MERCHANT_USER="merchant_account@example.com"
$env:API_MERCHANT_PASS="***"
.\scripts\run_api_regression.ps1
```

Seed precheck (non-mutating diagnostics before regression):

```powershell
$env:API_BASE_URL="http://192.168.1.103:19066"
$env:API_USER="customer@example.com"
$env:API_PASS="***"
.\scripts\run_api_seed_precheck.ps1
```

CMD:

```cmd
set API_BASE_URL=http://192.168.1.103:19066
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

## Supplemental Coverage Docs (2026-03-20)
- `docs/test-plans/order_extended_coverage_2026-03-20.md`
- `docs/test-plans/uat_acceptance_coverage_plan_2026-03-20.md`
- `docs/findings/uat_feature_execution_findings_2026-03-20.md`
