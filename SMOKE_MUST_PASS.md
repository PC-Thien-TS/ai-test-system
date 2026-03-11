# SMOKE_MUST_PASS

Scope: this week smoke set based only on `FEATURE_MAP.md`, `ROUTES.md`, `API_LIST.md`, `TEST_SUGGESTIONS.md`.

Execution rule:
- Run all `P0` first.
- `P1` can continue only if no `P0` blocker is open.

## Evidence Required For P0

- Screenshot/video of each critical step and final UI state.
- Network/API capture proving the evidence hook endpoint(s) were called.
- Response status code and response body snippet for each evidence hook API.
- Console/app log snippet when error or warning appears.
- If failure occurs, defect ticket ID must be added in test notes.

## Testcases

### SMK-01 Authentication login success
- Preconditions: Valid user account exists and is not locked.
- Steps:
1. Open `web_admin /login`.
2. Submit valid credentials.
3. Call profile/info retrieval after login.
- Expected: Login succeeds, authenticated session/token is usable, profile/info API returns success.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /login`
  - API: `POST /auth/login`, `GET /account/get-info`

### SMK-02 Authentication login failure
- Preconditions: Valid username exists; use wrong password.
- Steps:
1. Open `web_admin /login`.
2. Submit invalid credentials.
- Expected: Login is rejected with clear error; no authenticated session is created.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /login`
  - API: `POST /auth/login`

### SMK-04 Forgot password via OTP
- Preconditions: Existing account with recoverable contact.
- Steps:
1. Open `web_admin /forgot-password/otp`.
2. Trigger forgot-password.
3. Submit OTP and set new password.
- Expected: Password reset flow completes; old password no longer works and new password works.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /forgot-password/otp`
  - API: `POST /auth/forget-password`, `POST /auth/check-valid-otp`, `PUT /auth/update-password-otp`

### SMK-23 Admin dashboard metrics
- Preconditions: Admin user authorized.
- Steps:
1. Open `web_admin /dashboard`.
2. Load registration/scan widgets.
- Expected: Dashboard metric requests return success and widgets render values.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /dashboard`
  - API: `GET /dashboard/user-registrations`, `GET /dashboard/qr-scans`, `GET /dashboard/store-registrations`

### SMK-24 API key management baseline
- Preconditions: Admin user authorized.
- Steps:
1. Open `web_admin /settings/apikey`.
2. Create API key from `web_admin /settings/create-apikey`.
3. Verify key is listed and can be updated.
- Expected: API key lifecycle baseline (create/list/update) works without data corruption.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /settings/apikey`, `web_admin /settings/create-apikey`
  - API: `POST /apikey/create`, `GET /apikey/paged`, `PUT /apikey/update/{id}`

### SMK-06 Search posts basic query
- Preconditions: App is reachable; test keyword available.
- Steps:
1. Open `app /search`.
2. Submit keyword query.
3. Observe search result page.
- Expected: Result list is returned without crash; payload schema remains stable.
- Priority: P0
- Evidence hook:
  - Route: `app /search`, `app /search/result`
  - API: `GET /searches/posts`

### SMK-07 Search suggestions
- Preconditions: App search input available.
- Steps:
1. Open `app /search`.
2. Type partial keyword.
3. Observe suggestions.
- Expected: Suggestions endpoint responds and UI renders suggestion items.
- Priority: P0
- Evidence hook:
  - Route: `app /search`
  - API: `GET /searches/suggestions/{keyword}`

### SMK-09 Search history create/list/delete
- Preconditions: App search page available.
- Steps:
1. Open `app /search`.
2. Perform a search to create history.
3. Reload history list.
4. Delete search history.
- Expected: History is created, listed, then deleted consistently.
- Priority: P0
- Evidence hook:
  - Route: `app /search`
  - API: `POST /searches/histories`, `GET /searches/histories`, `DELETE /searches/histories`

### SMK-11 Store listing and detail
- Preconditions: At least one store exists.
- Steps:
1. Open `app /store-list/category-level1`.
2. Open `app /store/:uniqueId`.
- Expected: Store list and store detail load successfully.
- Priority: P0
- Evidence hook:
  - Route: `app /store-list/category-level1`, `app /store/:uniqueId`
  - API: `GET /store`, `GET /store/{uniqueId}`

### SMK-13 Store verification submission
- Preconditions: Authorized merchant user with existing store.
- Steps:
1. Open `app /store/verify`.
2. Submit verification request.
3. Fetch verification status.
- Expected: Verification request is created and appears in verification listing/detail.
- Priority: P0
- Evidence hook:
  - Route: `app /store/verify`
  - API: `POST /store/verify`, `GET /store/verify`, `GET /store/verify/detail/{id:long}`

### SMK-15 Admin approve store verification
- Preconditions: Pending store verification exists; admin user authorized.
- Steps:
1. Open `web_admin /admin/verify-store`.
2. Approve a pending verification item.
- Expected: Verification status transitions to approved and is visible in detail/list.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /admin/verify-store`
  - API: `PUT /store/verify/{id:long}/approve`, `GET /store/verify/detail/{id:long}`

### SMK-16 Admin reject store verification
- Preconditions: Pending store verification exists; admin user authorized.
- Steps:
1. Open `web_admin /admin/verify-store`.
2. Reject a pending verification item.
- Expected: Verification status transitions to rejected and is visible in detail/list.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /admin/verify-store`
  - API: `PUT /store/verify/{id:long}/reject`, `GET /store/verify/detail/{id:long}`

### SMK-19 Admin category management
- Preconditions: Admin user authorized.
- Steps:
1. Open `web_admin /admin/category`.
2. Create category.
3. Validate category appears in paged view.
- Expected: Category creation succeeds and list is updated.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /admin/category`
  - API: `POST /category-admin/create`, `GET /category-admin/paged`

### SMK-20 Product create and paged listing
- Preconditions: Admin or authorized product operator account.
- Steps:
1. Open `web_admin /product`.
2. Create a product.
3. Open paged list and confirm presence.
- Expected: Product creation succeeds and appears in paged list.
- Priority: P0
- Evidence hook:
  - Route: `web_admin /product`
  - API: `POST /product/create`, `GET /product/paged`

### SMK-03 Registration and OTP verification
- Preconditions: Test email/phone available for OTP receive.
- Steps:
1. Open `web_admin /register`.
2. Submit registration payload.
3. Open `web_admin /register/otp` and submit OTP.
- Expected: UNKNOWN exact OTP handshake sequence from docs; collect request/response evidence for registration and OTP validation.
- UNKNOWN handling: Must capture actual endpoint(s) called + status codes + UI state; pass = no crash + non-5xx + user-visible result.
- Priority: P1
- Evidence hook:
  - Route: `web_admin /register`, `web_admin /register/otp`
  - API: `POST /auth/register`, `POST /auth/check-valid-otp`, `PUT /auth/accept-valid-otp`

### SMK-05 Refresh token and logout invalidation
- Preconditions: Active authenticated session exists.
- Steps:
1. Request token refresh.
2. Logout.
3. Retry an authorized API call with old token.
- Expected: Refresh succeeds before logout; after logout, old token/session is invalid.
- Priority: P1
- Evidence hook:
  - Route: `web_admin /login`
  - API: `POST /auth/refresh-token`, `POST /auth/logout`

### SMK-08 Hot keywords retrieval
- Preconditions: App search page available.
- Steps:
1. Open `app /search`.
2. Load hot keywords section.
- Expected: Hot keyword list loads successfully.
- Priority: P1
- Evidence hook:
  - Route: `app /search`
  - API: `GET /searches/hot-keywords`

### SMK-10 Mobile search deep-link details
- Preconditions: A valid post identifier exists.
- Steps:
1. Open `app /search/mobile/posts/:uniqueId/:id`.
2. Validate content detail render.
- Expected: UNKNOWN exact detail API from docs; collect network evidence for resolved endpoint and payload.
- UNKNOWN handling: Must capture actual endpoint(s) called + status codes + UI state; pass = no crash + non-5xx + user-visible result.
- Priority: P1
- Evidence hook:
  - Route: `app /search/mobile/posts/:uniqueId/:id`
  - API: `GET /searches/posts` (seed query), detail endpoint UNKNOWN

### SMK-12 Store create flow
- Preconditions: Authorized merchant user available.
- Steps:
1. Open `app /store`.
2. Submit store creation form.
- Expected: Store is created and visible in follow-up listing.
- Priority: P1
- Evidence hook:
  - Route: `app /store`
  - API: `POST /store/create`, `GET /store/list`

### SMK-14 Merchant verification status page
- Preconditions: Existing verification request ID is available.
- Steps:
1. Open `app /settings/manage-store/verify-status/:authorId/:storeId`.
2. Validate displayed verification status.
- Expected: UNKNOWN exact route-to-endpoint binding from docs; collect endpoint evidence used by UI.
- UNKNOWN handling: Must capture actual endpoint(s) called + status codes + UI state; pass = no crash + non-5xx + user-visible result.
- Priority: P1
- Evidence hook:
  - Route: `app /settings/manage-store/verify-status/:authorId/:storeId`
  - API: `GET /store/verify/detail`, `GET /store/verify/detail/{id:long}`

### SMK-17 Store category admin CRUD
- Preconditions: Admin user authorized.
- Steps:
1. Open `web_admin /admin/store-category`.
2. Create a store category.
3. Update the same category.
4. Verify it appears in paged listing.
- Expected: Create/update operations succeed and data is reflected in admin listing.
- Priority: P1
- Evidence hook:
  - Route: `web_admin /admin/store-category`
  - API: `POST /store-category/admin/create`, `PUT /store-category/admin/update/{id}`, `GET /store-category/admin/paged`

### SMK-18 Location and ward resolution for store flow
- Preconditions: Province data exists.
- Steps:
1. Open `app /select-location`.
2. Select a province, then open `app /select-ward/:provinceId`.
3. Verify ward list is loaded.
- Expected: Province and ward datasets load and are selectable.
- Priority: P1
- Evidence hook:
  - Route: `app /select-location`, `app /select-ward/:provinceId`
  - API: `GET /provinces`, `GET /provinces/{provinceId:long}/wards`

### SMK-21 Document CRUD sanity
- Preconditions: Admin/authorized account.
- Steps:
1. Open `web_admin /document`.
2. Create a document.
3. Update the document.
4. Remove the document.
- Expected: Create/update/remove operations are successful and reflected in listing.
- Priority: P1
- Evidence hook:
  - Route: `web_admin /document`
  - API: `POST /document/create`, `PUT /document/update/{id}`, `DELETE /document/remove/{id}`, `GET /document/paged`

### SMK-22 Product menu extraction upload
- Preconditions: Valid menu image/file prepared.
- Steps:
1. Open `web_admin /product`.
2. Upload menu image for extraction.
- Expected: UNKNOWN extraction result contract from docs; collect request/response and resulting product draft evidence.
- UNKNOWN handling: Must capture actual endpoint(s) called + status codes + UI state; pass = no crash + non-5xx + user-visible result.
- Priority: P1
- Evidence hook:
  - Route: `web_admin /product`
  - API: `POST /product/menu-extraction`
