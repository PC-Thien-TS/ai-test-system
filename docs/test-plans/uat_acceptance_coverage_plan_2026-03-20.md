# UAT Acceptance Coverage Plan (2026-03-20)

## Scope Source
Feature inventory and priorities are derived from acceptance/UAT scope for:
- Admin Site RateMate-Didaunao
- App Didaunao
- Merchant Web

This plan maps feature groups to current automation assets and identifies what is executable now versus blocked.

## Coverage Legend
- `API`: `scripts/run_api_regression.ps1`
- `UI-SMOKE`: `scripts/run_ui_smoke.ps1`
- `UI-E2E`: `scripts/run_ui_e2e.ps1`
- Status: `covered` | `partial` | `blocked`

## B1. Admin Site (RateMate-Didaunao)
| Module Group | Priority | Current Test Assets | Automation Type | Status | Notes |
|---|---|---|---|---|---|
| Authentication | Critical | `AUTH-001..008`, `ADMIN-E2E-001` | API + UI-E2E | partial | API auth contract exists; current customer login drift blocks full auth happy path in latest run. |
| Dashboard | High | `DASH-001..007`, `ADMIN-E2E-002` | API + UI-E2E | covered | Admin dashboard API paths are executable with admin token. |
| User/Member management | High | `MEMBER-001..005` | API | partial | `MEMBER-001` remains backend defect (`500`). |
| Organization management | High | `ORG-001..007`, `ADMIN-E2E-004` | API + UI-E2E | partial | API coverage exists but token-dependent in latest run. |
| Store management | High | `STO-001..012` | API | partial | Core endpoints pass; known defects remain (`STO-009`, `STO-011`, `STO-012`). |
| Category management | High | `CATADM-001..006` | API | covered | Admin category endpoints execute with admin token. |
| Notification policy | Medium | `NOTI-001..006` | API | partial | Token-dependent in latest run. |
| Store verification and approval | High | `STO-006`, `STO-007` | API | covered | Verification read paths covered; write approval flow still not automated. |
| Province management | Medium | (planned) | API + UI | blocked | No deterministic province CRUD contract automation yet. |
| Account settings and password | High | `AUTH-008` partial reference | API + UI | blocked | Dedicated profile/password flows are not yet implemented in regression runner. |

## B2. App Didaunao
| Module Group | Priority | Current Test Assets | Automation Type | Status | Notes |
|---|---|---|---|---|---|
| Auth module | High | `AUTH-*`, `ORD-*` dependent login | API | partial | Runtime auth drift blocks customer-flow execution in latest run. |
| Home/Search/Category/Quick filter | High | `SEA-001..011`, `POSTS-*`, `NEWS-*` | API | partial | Search stable; `NEWS-003` remains slug-seed blocker. |
| Store detail and actions | High | `STO-*`, `ORD-API-004`, `ORD-API-020` | API | partial | Not-found defects remain in Store module. |
| Favorites/collections | Medium | `STO-012` behavior check | API | blocked | `/store/collections` currently defects in latest run. |
| Profile/Security/Settings | Medium | (planned) | UI + API | blocked | No deterministic profile settings automation yet. |
| Wallet and order activity | High | `ORD-PAY-*`, `ORD-API-009`, `ORD-CUS-*`, `ORD-CAN-*` | API | partial | Payment core is present; many stateful actions still seed/scope dependent. |
| Notification | Medium | `NOTI-*`, `NOTI-ORD-*` | API | partial | Order-event correlation still non-deterministic. |

## B3. Merchant Web
| Module Group | Priority | Current Test Assets | Automation Type | Status | Notes |
|---|---|---|---|---|---|
| Dashboard overview | High | `MORD-001` list baseline, merchant UI E2E shell | API + UI-E2E | partial | Merchant auth drift in latest run blocks happy path. |
| Orders lifecycle | Critical | `MORD-API-001..008` | API | partial | Lifecycle endpoints are wired; ownership and auth preconditions still gate full happy path. |
| Menu management | High | seed discovery via `/stores/{id}/menu` | API | partial | Read-side menu seed extraction exists; CRUD automation pending. |
| Store config/policy | High | `POL-001`, `ORD-API-018`, `ORD-CAVEAT-003` | API | partial | Policy and gating checks present; full config persistence flow pending. |
| Merchant settings | Medium | (planned) | UI + API | blocked | Notification/settings toggle automation not implemented yet. |

## Current Priority Execution Order
1. Recover deterministic customer and merchant login for current runtime.
2. Re-run full regression and unlock Order lifecycle and add-on assertions.
3. Add missing admin account settings and province CRUD cases.
4. Expand UI-E2E flows for admin and merchant after API seeds stabilize.

