# Functional Modules

This module catalog is the seed for SRS-to-test traceability in `ai_test_system`.
It is derived from the current test project assets plus the generated feature and API inventories:

- `FEATURE_MAP.md`
- `API_LIST.md`
- `ROUTES.md`
- `docs/API_REGRESSION_PLAN.md`
- `docs/UI_SMOKE_PLAN.md`
- `docs/UI_E2E_PLAN.md`
- `TEST_LOGIC_PLAN.md`

It now feeds the structured traceability assets under:

- `test-assets/srs/normalized/`
- `test-assets/srs/coverage/`
- `test-assets/srs/mappings/`

## Status Legend

- `Covered`: direct automated assets exist and are already mapped to the module.
- `Partial`: some automated coverage exists, but it is incomplete by flow, layer, or role.
- `Blocked`: automation exists or is planned, but runtime/admin-role/environment issues currently limit reliable execution.
- `Not covered`: the module exists in inventory, but no direct automated asset is currently mapped.

## Module Inventory

| Module | Scope | Primary Interfaces | Current Test Anchors | Current Status |
|---|---|---|---|---|
| `auth` | login, logout, refresh token, invalid credential handling | `/auth/*`, `/login` | API smoke, API regression `AUTH-*`, UI smoke auth flows, UI E2E login/logout, FE logic/component tests in `TEST_LOGIC_PLAN.md` | Covered |
| `account` | current user info, password/profile/account settings | `/account/*`, `/settings/account` | API smoke `GET /account/get-info`, API inventory, limited FE auth utility coverage | Partial |
| `organization` | organization list/detail/info, filters, paging, selection | `/organization/*`, `/organization` | API regression `ORG-*`, UI smoke organization route, UI E2E organization flows, FE organization table/filter tests referenced in `TEST_LOGIC_PLAN.md` | Covered |
| `notification` | user notifications plus admin notification template/policy surfaces | `/notification*`, `/admin/notification-*` | API regression `NOTI-*`, UI smoke notification route, UI E2E notification flow, FE notification template table tests referenced in `TEST_LOGIC_PLAN.md` | Partial |
| `posts` | posts list, ids, categories, pending/recommend, detail | `/posts*`, posts/newsfeed UI routes | API regression `POSTS-*`, UI smoke posts flow | Partial |
| `news` | news list/detail and admin-news adjacent read paths | `/news*`, news UI routes | API regression `NEWS-*`, UI smoke news flow | Partial |
| `category-admin` | admin category list, selection, detail, generate code | `/category-admin/*`, `/admin/category` | API regression `CATADM-*`, FE admin route-guard coverage referenced in `TEST_LOGIC_PLAN.md` | Partial |
| `member` | member list/detail/selection/activity-log | `/member/*`, `/member`, `/member-admin` | API regression `MEMBER-*`, route inventory only for UI | Partial |
| `dashboard` | registration and QR metrics dashboards | `/dashboard/*`, `/dashboard` | API regression `DASH-*`, UI E2E dashboard load, FE dashboard component coverage referenced in `TEST_LOGIC_PLAN.md` | Partial |
| `store` | store list/detail/reviews/views/verify and merchant flows | `/store*`, `/store`, `/merchant` | API smoke store endpoints, API regression `STO-*`, UI smoke store flow, backend logic/integration notes in `TEST_LOGIC_PLAN.md` | Covered |
| `store-category-admin` | admin store-category selection/detail/children | `/store-category/admin/*`, `/admin/store-category` | API regression `STCATADM-*`, route inventory only for UI | Partial |
| `searches` | search, suggestions, filters, histories, hot keywords | `/searches/*`, `/search` | API smoke search endpoints, API regression `SEA-*`, UI smoke search flow, backend search logic notes in `TEST_LOGIC_PLAN.md` | Covered |
| `language` | language selection and language admin CRUD | `/language/*`, `/settings/language` | API inventory and route inventory only | Not covered |
| `folder` | folder CRUD/list/detail/generate-code | `/folder/*` | API inventory only | Not covered |
| `storages` | file listing, upload, delete, presigned URL, paged storage views | `/storages/*` | API inventory only; future expansion noted in `docs/API_REGRESSION_PLAN.md` | Not covered |

## Notes

- Latest admin-account regression confirms `category-admin`, `dashboard`, and large parts of `member`/`store-category-admin` are executable; remaining gaps are defect-driven (`MEMBER-001`, `STCATADM-004`) or UI-depth related.
- `notification` is split between end-user notifications and admin notification template/policy screens, so current automation is useful but not yet full end-to-end product coverage.
- `language`, `folder`, and `storages` should be prioritized once formal SRS requirements are imported because those modules are present in the inventory but not yet represented by direct automated scripts.
- This document remains the readable module index; CSV assets under `test-assets/srs/` are the new structured traceability layer for later migration.
