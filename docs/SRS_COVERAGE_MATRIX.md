# SRS Coverage Matrix

This matrix is the initial traceability seed for importing formal SRS / functional requirements into the current test project.

Current source inputs:

- `docs/FUNCTIONAL_MODULES.md`
- `docs/API_REGRESSION_PLAN.md`
- `docs/API_REGRESSION_FINDINGS.md`
- `docs/UI_SMOKE_PLAN.md`
- `docs/UI_E2E_PLAN.md`
- `TEST_LOGIC_PLAN.md`
- `FEATURE_MAP.md`
- `API_LIST.md`
- `ROUTES.md`

## Status Legend

- `Covered`: direct automated assets exist and align to the requirement row.
- `Partial`: some automation exists, but not enough to claim full requirement coverage.
- `Blocked`: execution is currently constrained by admin-role access, unstable UI/runtime routes, or known environment issues.
- `Not covered`: no direct automated test asset is mapped yet.

## Traceability Columns

- `Requirement ID`
- `Module`
- `Feature`
- `Description`
- `Priority`
- `API Coverage`
- `FE Coverage`
- `UI Coverage`
- `Current Test Assets`
- `Status`
- `Notes`

## Prefilled Matrix

| Requirement ID | Module | Feature | Description | Priority | API Coverage | FE Coverage | UI Coverage | Current Test Assets | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `REQ-AUTH-001` | `auth` | Valid login and session bootstrap | User can sign in with valid credentials and reach an authenticated session. | `P0` | `run_api_smoke.ps1` `API-01..02`; `run_api_regression.ps1` `AUTH-*` | Frontend auth/login and auth utility coverage referenced in `TEST_LOGIC_PLAN.md` | `run_ui_smoke.ps1` auth flow; `run_ui_e2e.ps1` `ADMIN-E2E-001` | `scripts/run_api_smoke.ps1`, `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `scripts/run_ui_e2e.ps1`, `TEST_LOGIC_PLAN.md` | Covered | Cross-layer automation exists. |
| `REQ-AUTH-002` | `auth` | Invalid login rejection | Invalid credentials must be rejected without crash and without silent success. | `P0` | `run_api_smoke.ps1` `API-03`; `run_api_regression.ps1` negative auth cases | Frontend login failure state referenced in `TEST_LOGIC_PLAN.md` | `run_ui_smoke.ps1` login failure flow | `scripts/run_api_smoke.ps1`, `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `TEST_LOGIC_PLAN.md` | Covered | UI E2E currently focuses on successful admin login path. |
| `REQ-AUTH-003` | `auth` | Logout and session invalidation | User can log out and return to a login route. | `P1` | `run_api_regression.ps1` refresh/logout when feasible | Frontend auth utility cleanup referenced in `TEST_LOGIC_PLAN.md` | `run_ui_smoke.ps1` logout if exposed; `run_ui_e2e.ps1` `ADMIN-E2E-007` | `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `scripts/run_ui_e2e.ps1`, `TEST_LOGIC_PLAN.md` | Partial | Logout automation is present, but endpoint feasibility depends on live auth response. |
| `REQ-ACCOUNT-001` | `account` | Account info retrieval | Authenticated user can retrieve current account/profile information. | `P0` | `run_api_smoke.ps1` `API-02`; `API_LIST.md` `/account/get-info` | FE auth/session helpers indirectly support account state | UI smoke organization/profile candidate routes only | `scripts/run_api_smoke.ps1`, `API_LIST.md`, `FEATURE_MAP.md` | Partial | Core read path is covered, but account settings screens are not yet directly automated. |
| `REQ-ACCOUNT-002` | `account` | Account profile update/settings | User can update account details, password, avatar, or related settings. | `P1` | Inventory only (`/account/change-password`, `/account/update-info`, `/account/upload-avatar`) | No direct FE setting-form automation mapped | No direct UI automation mapped | `API_LIST.md`, `FEATURE_MAP.md`, `ROUTES.md` | Not covered | Should be split into multiple SRS rows once the formal SRS is imported. |
| `REQ-ORG-001` | `organization` | Organization list/detail/info | Authorized user can browse organization list/detail/info routes and APIs. | `P0` | `run_api_regression.ps1` `ORG-*` | FE organization table rendering covered via `TEST_LOGIC_PLAN.md` | `run_ui_smoke.ps1` organization route; `run_ui_e2e.ps1` `ADMIN-E2E-004` | `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `scripts/run_ui_e2e.ps1`, `TEST_LOGIC_PLAN.md` | Covered | API + UI + FE component coverage exists. |
| `REQ-ORG-002` | `organization` | Organization search/filter/sort/paging | Organization page supports keyword search, sort, filters, and pagination. | `P1` | `run_api_regression.ps1` `ORG-*` list/paged/detail | FE organization filter/table interaction coverage referenced in `TEST_LOGIC_PLAN.md` | `run_ui_e2e.ps1` `ADMIN-E2E-005` | `scripts/run_api_regression.ps1`, `scripts/run_ui_e2e.ps1`, `TEST_LOGIC_PLAN.md` | Covered | Good candidate for future exact SRS field-level acceptance checks. |
| `REQ-NOTI-001` | `notification` | Notification list and unread count | User can open notifications and retrieve unread count/list. | `P1` | `run_api_regression.ps1` `NOTI-001..003` | FE notification template table coverage exists for admin surface only | `run_ui_smoke.ps1` notification route; `run_ui_e2e.ps1` `ADMIN-E2E-006` | `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `scripts/run_ui_e2e.ps1`, `TEST_LOGIC_PLAN.md` | Partial | Admin notification template coverage is stronger than end-user notification UI coverage. |
| `REQ-NOTI-002` | `notification` | Notification mark-read/delete semantics | Notification mark-read/delete actions should obey the agreed contract. | `P2` | `run_api_regression.ps1` `NOTI-004..006`; mismatch documented in findings | No direct FE action coverage mapped | No direct UI action coverage mapped | `scripts/run_api_regression.ps1`, `docs/API_REGRESSION_FINDINGS.md` | Partial | Contract currently allows empty payload for some actions; review still needed. |
| `REQ-POSTS-001` | `posts` | Posts list and recommendation | User can access post list, ids, categories, and recommendations. | `P1` | `run_api_regression.ps1` `POSTS-*` | No direct FE source-level posts component coverage mapped in this repo | `run_ui_smoke.ps1` posts/newsfeed flow | `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `docs/API_REGRESSION_PLAN.md` | Partial | API coverage is stronger than UI/FE coverage. |
| `REQ-NEWS-001` | `news` | News list and detail | User can browse news list and open news detail by slug. | `P1` | `run_api_regression.ps1` `NEWS-*` | No direct FE source-level news component coverage mapped in this repo | `run_ui_smoke.ps1` news list/detail flow | `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `docs/API_REGRESSION_PLAN.md` | Partial | Detail coverage depends on slug seed inference. |
| `REQ-CATADM-001` | `category-admin` | Category admin list/selection/detail | Admin user can view category admin list, selection, generate-code, and detail. | `P1` | `run_api_regression.ps1` `CATADM-*` | FE admin route-guard coverage referenced in `TEST_LOGIC_PLAN.md` | No dedicated Playwright admin category flow yet | `scripts/run_api_regression.ps1`, `TEST_LOGIC_PLAN.md`, `ROUTES.md` | Partial | Latest admin run proves executable API coverage; UI-specific admin navigation depth is still limited. |
| `REQ-MEMBER-001` | `member` | Member list/detail | Admin user can list members, page selections, and view details. | `P1` | `run_api_regression.ps1` `MEMBER-*` | No direct FE member page automation mapped | No direct UI automation mapped | `scripts/run_api_regression.ps1`, `ROUTES.md`, `API_LIST.md` | Partial | Latest admin run executes most member checks; `MEMBER-001` is currently blocked by backend defect (`500` mapping/configuration). |
| `REQ-DASH-001` | `dashboard` | Dashboard metrics visibility | Admin dashboard shows user/store/QR metrics without fatal errors. | `P0` | `run_api_regression.ps1` `DASH-*` | FE dashboard component coverage referenced in `TEST_LOGIC_PLAN.md` | `run_ui_e2e.ps1` `ADMIN-E2E-002` | `scripts/run_api_regression.ps1`, `scripts/run_ui_e2e.ps1`, `TEST_LOGIC_PLAN.md` | Partial | FE/UI coverage is strong; API positive execution can still be role-blocked. |
| `REQ-STORE-001` | `store` | Store list and detail browse | User can open store list and store detail without server errors. | `P0` | `run_api_smoke.ps1` store/search endpoints; `run_api_regression.ps1` `STO-*` | Backend logic/integration notes in `TEST_LOGIC_PLAN.md` | `run_ui_smoke.ps1` store list/detail flows | `scripts/run_api_smoke.ps1`, `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `TEST_LOGIC_PLAN.md` | Covered | This is one of the strongest currently mapped areas. |
| `REQ-STORE-002` | `store` | Store verification approve/reject | Store verify list/detail and approve/reject endpoints behave safely. | `P0` | `run_api_regression.ps1` store verify coverage; backend integration notes in `TEST_LOGIC_PLAN.md` | No direct FE verify-page automation mapped in this repo | No direct Playwright verify-store flow yet | `scripts/run_api_regression.ps1`, `TEST_LOGIC_PLAN.md`, `API_LIST.md` | Partial | Verification endpoints exist and are tested technically, but UI/admin execution is not yet direct. |
| `REQ-STORE-003` | `store` | Invalid store identifiers handled safely | Invalid store id/uniqueId/collections paths must not return `500`. | `P0` | `run_api_regression.ps1` `STO-009`, `STO-011`, `STO-012` | None | None | `scripts/run_api_regression.ps1`, `docs/API_REGRESSION_FINDINGS.md` | Blocked | Confirmed backend bugs are still open. |
| `REQ-STCATADM-001` | `store-category-admin` | Store-category admin detail/children | Admin user can access store-category selection/detail/children/generate-code APIs. | `P1` | `run_api_regression.ps1` `STCATADM-*` | No direct FE admin store-category automation mapped | No direct UI automation mapped | `scripts/run_api_regression.ps1`, `ROUTES.md`, `API_LIST.md` | Partial | Latest admin run proves executable coverage for selection/detail/children; invalid-id detail path still fails (`STCATADM-004`, backend `500`). |
| `REQ-SEA-001` | `searches` | Search query, suggestions, and filters | User can query search, receive suggestions, and access filter/hot-keyword endpoints. | `P0` | `run_api_smoke.ps1` `API-04..05`; `run_api_regression.ps1` `SEA-*` | Backend search-related logic noted in `TEST_LOGIC_PLAN.md` | `run_ui_smoke.ps1` search open/query/suggestions flow | `scripts/run_api_smoke.ps1`, `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `TEST_LOGIC_PLAN.md` | Covered | Search is covered across API and UI smoke layers. |
| `REQ-SEA-002` | `searches` | Search history persistence | User can create, read, and delete search history safely. | `P1` | `run_api_smoke.ps1` `API-06..08`; `run_api_regression.ps1` `SEA-*` | Backend integration notes in `TEST_LOGIC_PLAN.md` | UI smoke only checks history if exposed | `scripts/run_api_smoke.ps1`, `scripts/run_api_regression.ps1`, `scripts/run_ui_smoke.ps1`, `TEST_LOGIC_PLAN.md` | Covered | UI exposure is optional, but API path is directly exercised. |
| `REQ-LANGUAGE-001` | `language` | Language selection and language master data | System supports language selection and language CRUD/selection endpoints. | `P2` | Inventory only (`/language/*`, `/devices/update-language`) | No direct FE language automation mapped | Route inventory only (`/settings/language`) | `API_LIST.md`, `ROUTES.md`, `FEATURE_MAP.md` | Not covered | Add after SRS import defines required language behavior. |
| `REQ-FOLDER-001` | `folder` | Folder CRUD and list/detail | Authorized user can create, list, detail, update, and remove folders. | `P2` | Inventory only (`/folder/*`) | None | None | `API_LIST.md`, `FEATURE_MAP.md` | Not covered | Present in inventory, but no direct automated asset exists yet. |
| `REQ-STORAGES-001` | `storages` | Storage file listing and upload/download | Storage services list files, generate URLs, upload, and delete files. | `P2` | Inventory only (`/storages/*`) | None | None | `API_LIST.md`, `FEATURE_MAP.md`, `docs/API_REGRESSION_PLAN.md` | Not covered | Future expansion module already noted in API regression plan. |

## Immediate Next Steps

1. Import formal SRS requirement rows into `testdata/srs/requirement_traceability_template.csv` using the provisional IDs here as placeholders until official IDs are available.
2. Split broad rows such as `REQ-ACCOUNT-002`, `REQ-NOTI-002`, and `REQ-STORAGES-001` once the SRS clarifies sub-features and acceptance criteria.
3. Prioritize `Not covered` and `Blocked` rows for the next automation wave, especially `language`, `folder`, `storages`, and admin-role-sensitive modules.
