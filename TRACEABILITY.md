# TRACEABILITY

P0 traceability matrix derived from [SMOKE_MUST_PASS.md](c:/Users/PC-Thien/ai_test_system/SMOKE_MUST_PASS.md), `ROUTES.md`, and `API_LIST.md`.

| P0 Testcase | Feature module | UI route(s) | API endpoint(s) |
|---|---|---|---|
| `SMK-01` | Authentication | `web_admin /login` | `POST /auth/login`, `GET /account/get-info` |
| `SMK-02` | Authentication | `web_admin /login` | `POST /auth/login` |
| `SMK-04` | Authentication | `web_admin /forgot-password/otp` | `POST /auth/forget-password`, `POST /auth/check-valid-otp`, `PUT /auth/update-password-otp` |
| `SMK-06` | Search | `app /search`, `app /search/result` | `GET /searches/posts` |
| `SMK-07` | Search | `app /search` | `GET /searches/suggestions/{keyword}` |
| `SMK-09` | Search | `app /search` | `POST /searches/histories`, `GET /searches/histories`, `DELETE /searches/histories` |
| `SMK-11` | Store / merchant features | `app /store-list/category-level1`, `app /store/:uniqueId` | `GET /store`, `GET /store/{uniqueId}` |
| `SMK-13` | Store / merchant features | `app /store/verify` | `POST /store/verify`, `GET /store/verify`, `GET /store/verify/detail/{id:long}` |
| `SMK-15` | Store / merchant features | `web_admin /admin/verify-store` | `PUT /store/verify/{id:long}/approve`, `GET /store/verify/detail/{id:long}` |
| `SMK-16` | Store / merchant features | `web_admin /admin/verify-store` | `PUT /store/verify/{id:long}/reject`, `GET /store/verify/detail/{id:long}` |
| `SMK-19` | Menu / catalog | `web_admin /admin/category` | `POST /category-admin/create`, `GET /category-admin/paged` |
| `SMK-20` | Menu / catalog | `web_admin /product` | `POST /product/create`, `GET /product/paged` |
| `SMK-23` | Admin panel | `web_admin /dashboard` | `GET /dashboard/user-registrations`, `GET /dashboard/qr-scans`, `GET /dashboard/store-registrations` |
| `SMK-24` | Admin panel | `web_admin /settings/apikey`, `web_admin /settings/create-apikey` | `POST /apikey/create`, `GET /apikey/paged`, `PUT /apikey/update/{id}` |
