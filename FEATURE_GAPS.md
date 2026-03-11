# FEATURE_GAPS

Scope: route reachability checklist derived from `ROUTES.md` and prioritized by `SMOKE_MUST_PASS.md`.

Status values:
- `REACHABLE`
- `HIDDEN`
- `BROKEN`
- `AUTH-GATED`
- `UNKNOWN`

## Route Reachability Checklist

| Route | Module | Current status | Evidence link | Notes |
|---|---|---|---|---|
| `web_admin /login` | Authentication | UNKNOWN | `UNKNOWN` | Entry route for SMK-01/02 |
| `web_admin /forgot-password/otp` | Authentication | UNKNOWN | `UNKNOWN` | Required for SMK-04 |
| `web_admin /register` | Authentication | UNKNOWN | `UNKNOWN` | Required for SMK-03 |
| `web_admin /register/otp` | Authentication | UNKNOWN | `UNKNOWN` | Required for SMK-03 |
| `web_admin /dashboard` | Admin panel | AUTH-GATED | `UNKNOWN` | Required for SMK-23 |
| `web_admin /settings/apikey` | Admin panel | AUTH-GATED | `UNKNOWN` | Required for SMK-24 |
| `web_admin /settings/create-apikey` | Admin panel | AUTH-GATED | `UNKNOWN` | Required for SMK-24 |
| `web_admin /admin/verify-store` | Store / merchant features | AUTH-GATED | `UNKNOWN` | Required for SMK-15/16 |
| `web_admin /admin/category` | Menu / catalog | AUTH-GATED | `UNKNOWN` | Required for SMK-19 |
| `web_admin /admin/store-category` | Store / merchant features | AUTH-GATED | `UNKNOWN` | Required for SMK-17 |
| `web_admin /product` | Menu / catalog | AUTH-GATED | `UNKNOWN` | Required for SMK-20/22 |
| `web_admin /document` | Menu / catalog | AUTH-GATED | `UNKNOWN` | Required for SMK-21 |
| `app /search` | Search | UNKNOWN | `UNKNOWN` | Required for SMK-06/07/08/09 |
| `app /search/result` | Search | UNKNOWN | `UNKNOWN` | Required for SMK-06 |
| `app /search/mobile/posts/:uniqueId/:id` | Search | UNKNOWN | `UNKNOWN` | Required for SMK-10 |
| `app /store-list/category-level1` | Store / merchant features | UNKNOWN | `UNKNOWN` | Required for SMK-11 |
| `app /store/:uniqueId` | Store / merchant features | UNKNOWN | `UNKNOWN` | Required for SMK-11 |
| `app /store` | Store / merchant features | AUTH-GATED | `UNKNOWN` | Required for SMK-12 |
| `app /store/verify` | Store / merchant features | AUTH-GATED | `UNKNOWN` | Required for SMK-13 |
| `app /settings/manage-store/verify-status/:authorId/:storeId` | Store / merchant features | AUTH-GATED | `UNKNOWN` | Required for SMK-14 |
| `app /select-location` | Store / merchant features | UNKNOWN | `UNKNOWN` | Required for SMK-18 |
| `app /select-ward/:provinceId` | Store / merchant features | UNKNOWN | `UNKNOWN` | Required for SMK-18 |

## Top Risk Routes (From SMOKE P0)

| Route | Why high risk |
|---|---|
| `web_admin /login` | If unreachable, all authenticated web admin smoke paths are blocked. |
| `web_admin /dashboard` | Core admin health/metrics visibility gate for release operations. |
| `web_admin /settings/apikey` | API key lifecycle is a platform control plane path. |
| `app /search` | Search is high-frequency user flow and feeds multiple downstream paths. |
| `app /store-list/category-level1` | Entry point for store discovery and merchant traffic funnel. |
| `app /store/verify` | Merchant onboarding/compliance gate; failures block business process. |
| `web_admin /admin/verify-store` | Approval/rejection gate for store verification lifecycle. |
| `web_admin /product` | Product/catalog availability impacts merchant and user-facing content quality. |
