# API Regression Health Snapshot (2026-03-11, Admin Account Run)

## Focused Verification Update (2026-03-24, host `192.168.1.103`)
- Layer reruns in this round:
  - `CORE`: `109/102/7/0` (total/pass/fail/skip)
  - `JOURNEYS`: `33/33/0/0`
  - `EDGE` (diagnostic): `26/1/0/25`
- Confirmed backend defect set (stable across repeated CORE rerun):
  - `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`
- Merchant status in this round:
  - merchant token is available and merchant module cases execute;
  - remaining merchant non-happy-path outcomes are business-state dependent (`400`), not auth/token absence.
- Major skip clusters (EDGE-only):
  - `SEED_BLOCKER`: `STO-010`, `ORD-API-008`, `ORD-API-017`, `ORD-API-019`, `AORD-API-007`, `AORD-API-008`, `NOTI-ORD-001`, `NEWS-003`
  - `RUNTIME_CONTRACT_CONFIG_BLOCKER`: `ORD-API-018`, `ORD-CAN-004`, `NOTI-ORD-002/003/006`, `ORD-JOB-001..004`, `ORD-CAVEAT-001/003/004`
  - `SCOPE_BLOCKER`: `NOTI-ORD-004`, `NOTI-ORD-005`, `ORD-CAVEAT-002`
  - `FRAMEWORK_GAP`: `ORD-001` (legacy superseded)

## Latest Snapshot Update (2026-03-24, host `192.168.1.7`)
- Source artifacts:
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.failed.json`
  - `artifacts/test-results/api-regression/api_regression.log`
- Totals: `total=166`, `passed=126`, `failed=7`, `skipped=33`
- Layer summary:
  - `CORE`: `109/100/7/2` (total/pass/fail/skip)
  - `JOURNEYS`: `32/24/0/8`
  - `EDGE`: `25/2/0/23`

### Current backend defect set (unchanged)
- `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`

### Current major blockers
- Merchant auth blocker:
  - merchant login returns `400 Incorrect email or password`
  - merchant module cases are skipped with explicit `CONFIG_BLOCKER/SCOPE_BLOCKER` notes.
- Seed blockers:
  - `STO-010` uniqueId still unresolved.
  - `ORD-API-018` closed/ordering-disabled store seed missing.
  - `ORD-API-019` disabled/out-of-stock sku seed missing.
  - `NEWS-003` no slug from current `/news` list payload.
- Seed unlock achieved:
  - alternate store seed now deterministic (`storeId=10141`, `skuId=21`), enabling `ORD-API-008` and `ORD-API-017`.


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

## Supplemental Order Evidence (2026-03-13)
- Separate live Order rerun re-established a working seed:
  - `storeId=9768`
  - `skuId=14`
- `ORD-API-001`, `ORD-API-002`, `ORD-API-003`, and `ORD-API-004` all passed in the focused rerun.
- Merchant lifecycle remains blocked by scope/account (`400 FORBIDDEN_SCOPE`).
- Admin order endpoints remain blocked by role (`401`) for the current account.
- Supplemental artifacts:
  - `test-assets/seeds/order/order_seed.json`
  - `artifacts/test-results/order/order_execution_2026-03-13.json`
  - `artifacts/test-results/order/order_critical_rerun_2026-03-13.json`

## Order Flow Health Update (2026-03-17)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/findings/order_execution_findings_2026-03-17.md`

| Order Flow | Status | Evidence |
|---|---|---|
| Order Creation | Covered + defect findings | `ORD-API-001..007`, `ORD-API-009..013`, `ORD-API-016`, `ORD-API-020` pass; `ORD-API-014`, `ORD-API-015` fail (`500`). |
| Order Payment | Partial (mostly covered) | `ORD-PAY-001..004` pass; `ORD-PAY-005`, `ORD-PAY-006` blocked by deterministic paid/cancelled seeds. |
| Merchant Processing | Blocked by scope | `MORD-API-001..005` remain scope-blocked (`FORBIDDEN_SCOPE` or created order not visible in merchant list). |
| Admin Tracking | Blocked by role | `AORD-API-001..004`, `AORD-OPS-001..002` return `401` with current account. |
| Order Cancellation | Partial | `ORD-CAN-001` reaches controlled status path; deeper lifecycle checks (`ORD-CAN-002..004`) remain blocked. |
| Order Notification | Blocked/Partial | Notification feed check executes but no deterministic order event mapping (`NOTI-ORD-001..006` mostly blocked). |
| Order Control & Support | Blocked by role | Admin support checks are wired but blocked without admin-capable account token. |

## Order Flow Health Update (2026-03-18)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/findings/order_execution_findings_2026-03-18.md`

Latest totals:
- `total=134`, `passed=107`, `failed=6`, `skipped=21`

| Order Flow | Status | Evidence |
|---|---|---|
| Order Creation | Covered + defect findings | `ORD-API-001..007`, `009..013`, `016`, `020` pass; `ORD-API-014`, `015` still fail (`500`). |
| Order Payment | Covered | `ORD-PAY-001..006` executable; guard paths (`005`, `006`) now pass with discovered seeds (`paidOrderId=50`, `cancelledOrderId=43`). |
| Merchant Processing | Partial (scope blocked) | `MORD-API-001..005` remain `SCOPE_BLOCKER` because merchant list does not include created customer order. |
| Admin Tracking / Ops | Covered (admin token) | `AORD-API-001..004` and `AORD-OPS-001..002` pass with `API_ADMIN_USER/admin@gmail.com`. |
| Order Cancellation | Partial | `ORD-CAN-001`, `ORD-CAN-002` pass with controlled responses; `ORD-CAN-003`, `ORD-CAN-004` still blocked by completed/timeline seeds. |
| Order Notification | Blocked/Partial | Endpoint executes, but deterministic event correlation remains unresolved (`NOTI-ORD-001..006` mostly blocked). |

## Order/Regression Health Update (2026-03-19)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/findings/order_execution_findings_2026-03-19.md`

Latest totals:
- `total=134`, `passed=102`, `failed=7`, `skipped=25`

Module highlights:
- `auth`, `searches`, `posts`, `organization`, `notification`, `admin-orders`, `admin-ops`, `category-admin`, `dashboard`: stable in this run.
- `store`: backend-defect module (`STO-009`, `STO-011`, `STO-012`) plus deterministic seed blocker (`STO-010`).
- `orders`: partial; core create/detail/history checks pass, while `ORD-API-014/015` remain backend defects and multiple edge/lifecycle checks remain blocked by deterministic seeds.
- `merchant-orders`: scope-blocked; merchant list does not include created order id in current account/store context.
- `orders-cancellation`: partial; `ORD-CAN-001` covered, deeper checks blocked by seed/scope prerequisites.
- `order-notification`: blocked by missing deterministic correlation events in notification payload.
- `news`: partial with deterministic seed blocker (`NEWS-003`).

Confirmed backend defect set in latest run:
- `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`.

## Regression Health Update (2026-03-20, Config Validation Run)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/findings/order_execution_findings_2026-03-20.md`

Latest totals:
- `total=141`, `passed=63`, `failed=7`, `skipped=71`

Interpretation:
- This run is not used as a new backend-defect baseline because customer/merchant credentials failed login (`400 Incorrect email or password`).
- Admin login remained valid.
- Runner behavior was hardened:
  - role tokens are now resolved independently
  - customer-token absence is classified as `CONFIG_BLOCKER` where applicable
  - additional order lifecycle endpoints are now registered (`ORD-PAY-007/008`, `ORD-CUS-001..003`, `MORD-API-006/007`) for execution once seeds/scope are available.
- Active failures in this run:
  - backend defects re-verified: `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`
- `AUTH-001` and `SEA-007` are now correctly classified as `SKIPPED` auth/config blockers, not backend failures.
- `ORD-API-014/015` visibility is preserved via admin fallback probe when customer token is unavailable.

## Regression Health Update (2026-03-20, New Runtime Host)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/findings/order_execution_findings_2026-03-20.md`

Latest totals on `http://192.168.1.103:19066`:
- `total=141`, `passed=117`, `failed=6`, `skipped=18`

Highlights:
- Auth/runtime access recovered:
  - `AUTH-001` pass (`200`)
  - `SEA-007` pass (`200`)
  - merchant login/list restored (`MORD-001` pass)
- Merchant lifecycle now partially executable:
  - `MORD-API-001`, `MORD-API-002` return controlled `400`
  - downstream merchant transitions still skipped when accept precondition is not met
- Backend defect visibility remains strict:
  - active fail set: `STO-009`, `STO-011`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`
- `STO-012` changed to `PASS 200` on this host and is tracked as runtime behavior change.

## Regression Health Update (2026-03-20, Extended Order/UAT Coverage Registration)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/test-plans/order_extended_coverage_2026-03-20.md`
- `docs/findings/uat_feature_execution_findings_2026-03-20.md`

Latest totals:
- `total=166`, `passed=65`, `failed=7`, `skipped=94`

Interpretation:
- Extended order and acceptance-mapped cases are now registered in regression:
  - `ORD-API-021..029`
  - `ORD-CUS-004`
  - `MORD-API-008`
  - `AORD-API-005..008`
  - `ORD-ADDON-001..002`
  - `ORD-JOB-001..004`
  - `ORD-CAVEAT-001..004`
- In this execution, customer and merchant login returned `400 Incorrect email or password`, so customer/merchant-heavy modules are blocked by runtime auth access.
- Admin token remained valid and admin modules still executed.
- Confirmed failures remain:
  - `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`.

## Regression Health Update (2026-03-23, Auth/Access Drift)

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `docs/findings/order_execution_findings_2026-03-23.md`

Latest totals:
- `total=166`, `passed=65`, `failed=7`, `skipped=94`

Layer status:
- `CORE`: `109/64/7/38`
- `JOURNEYS`: `33/1/0/32`
- `EDGE`: not re-run independently after host instability; use full-run evidence.

Interpretation:
- Regression signal degraded by auth/runtime access, not by runner assertion weakening.
- Customer and merchant login now return `400 Incorrect email or password`.
- Admin login still passes and admin modules remain executable.
- Backend defect visibility remains intact:
  - `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`.

Order-specific notes:
- `JOURNEYS` currently has `0 FAIL`, but skip count is high due missing customer/merchant tokens.
- Merchant chain (`accept -> arrived -> complete`) is blocked by merchant auth access.
- `ORD-API-022` remains contract-review territory when executable (`200` accepted path), but was skipped in this run due missing customer auth token.
