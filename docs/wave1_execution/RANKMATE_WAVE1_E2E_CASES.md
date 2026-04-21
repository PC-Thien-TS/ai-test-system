# RANKMATE Wave 1 Selective E2E Cases

## Scope
- Selective E2E only for cross-surface critical flows.
- E2E here is intentionally narrow and tied to API-first checkpoints.

## Source Basis
- `docs/RANKMATE_CROSS_REPO_FLOW_MAP.md`
- `docs/RANKMATE_WAVE1_TEST_PLAN.md`
- Route and API wiring:
  - `rankmate_us/src/routes/AppRoutes.tsx`, `src/components/orders/*`, `src/components/search/result/*`
  - `didaunao_mc_web/src/App.tsx`, `src/features/orders/*`, `src/features/store/StoreSelectPage.tsx`
  - `rankmate_fe/src/pages/admin/orders/*`, `src/features/admin/orders/*`
  - `rankmate_be/CoreV2.MVC/Api/*.cs`

## Why Wave 1
- Covers conversion-critical path and highest-risk status propagation.
- Validates role-isolation boundaries across user, merchant, admin surfaces.
- Catches integration defects that API-only tests cannot expose (routing guards, stale UI state, token context issues).

---

## E2E-001 User Login -> Search -> Cart -> Create Order

### Case ID
- `E2E-W1-001`

### Flow name
- User purchase entry and order creation baseline

### Repos involved
- `rankmate_us`, `rankmate_be`

### Pages/routes
- User app: `/search`, `/search/result`, `/store/:uniqueId`, `/store/:uniqueId/menu`, `/orders/checkout`, `/orders/:orderId`

### APIs touched
- `POST /api/v1/auth/login`
- `GET /api/v1/searches/stores`
- `GET /api/v1/store/{uniqueId}`
- `GET /api/v1/stores/{storeId}/menu`
- `GET /api/v1/store/{storeId}/eligibility`
- `POST /api/v1/orders/pricing-preview`
- `POST /api/v1/orders`
- `GET /api/v1/orders/{id}`

### Preconditions
- Active user account.
- Active store with published menu and at least one valid SKU.
- Ordering eligibility enabled for target store.

### Steps
1. Login with valid user credentials.
2. Search store by keyword and open one result.
3. Navigate to store menu and add item(s) to cart.
4. Proceed to checkout and trigger order create.
5. Open created order tracking page.

### Expected UI assertions
- Search results render and selectable store cards are visible.
- Checkout page shows calculated totals.
- Order tracking page loads with created order id and pending/payment status.

### Expected backend assertions
- Order create returns success with `status=Pending`.
- Pricing preview totals align with order totals (`totalDueNowAmount` consistency window).

### Cross-surface consistency checks
- Created order id is retrievable by API and later visible to merchant/admin when state transitions.

### Risk notes
- High risk for idempotency mismatch and pricing drift.

### Blockers
- Deterministic data seeding required to stabilize search ranking and SKU availability.

---

## E2E-002 Payment Success -> Merchant Sees Paid Order

### Case ID
- `E2E-W1-002`

### Flow name
- Payment callback propagation to merchant queue

### Repos involved
- `rankmate_us`, `rankmate_be`, `didaunao_mc_web`

### Pages/routes
- User: `/orders/checkout`, `/payment-result`, `/orders/:orderId`
- Merchant: `/login`, `/select-store`, `/orders`, `/orders/:id`

### APIs touched
- `POST /api/v1/orders/{id}/payments`
- `POST /api/v1/payments/stripe/webhook` (or MoMo webhook variant)
- `GET /api/v1/orders/{id}`
- `GET /api/v1/merchant/orders`
- `GET /api/v1/merchant/orders/{id}`

### Preconditions
- Created pending order from E2E-W1-001.
- Payment webhook secret and simulation capability available.
- Merchant account linked to same store.

### Steps
1. Initiate payment for the pending order.
2. Simulate successful callback for that payment attempt.
3. Refresh user order tracking/payment result page.
4. Login merchant, select store, refresh queue.
5. Open merchant detail for the same order id.

### Expected UI assertions
- User sees payment success state (not still pending).
- Merchant queue shows the paid order and allows next valid actions.

### Expected backend assertions
- Callback returns `204` and marks order paid once.
- Duplicate callback replay does not duplicate state mutation.

### Cross-surface consistency checks
- User and merchant surfaces show the same canonical order status.

### Risk notes
- Highest financial integrity risk in Wave 1.

### Blockers
- Stripe/MoMo signature generation and sandbox credentials.

---

## E2E-003 Merchant Confirm Path -> User Sees Updated Status

### Case ID
- `E2E-W1-003`

### Flow name
- Merchant action transition propagation to user

### Repos involved
- `didaunao_mc_web`, `rankmate_be`, `rankmate_us`

### Pages/routes
- Merchant: `/orders`, `/orders/:id`
- User: `/orders/:orderId`

### APIs touched
- `POST /api/v1/merchant/orders/{id}/accept`
- `POST /api/v1/merchant/orders/{id}/mark-arrived`
- `POST /api/v1/merchant/orders/{id}/complete`
- `GET /api/v1/orders/{id}`

### Preconditions
- Paid order exists and belongs to merchant store.

### Steps
1. Merchant accepts order.
2. Merchant marks arrived.
3. Merchant completes order (include `payAtStoreCollectedAmount` when required).
4. User refreshes order tracking page.

### Expected UI assertions
- Merchant action buttons reflect legal next transitions only.
- User tracking status updates accordingly and invalid actions are hidden/disabled.

### Expected backend assertions
- Status transitions follow allowed chain.
- Invalid transition attempt returns 400 and does not mutate state.

### Cross-surface consistency checks
- Merchant detail and user detail status are equal for same order id.

### Risk notes
- Core state-machine corruption risk.

### Blockers
- Need seeded order states for legal and illegal transition tests.

---

## E2E-004 Admin Sees Same Updated Status as User/Merchant

### Case ID
- `E2E-W1-004`

### Flow name
- Admin monitoring consistency on active commerce order

### Repos involved
- `rankmate_fe`, `rankmate_be`, `rankmate_us`, `didaunao_mc_web`

### Pages/routes
- Admin: `/admin/orders`, `/admin/orders/:id`
- User: `/orders/:orderId`
- Merchant: `/orders/:id`

### APIs touched
- `GET /api/v1/admin/orders`
- `GET /api/v1/admin/orders/{id}`
- `GET /api/v1/orders/{id}`
- `GET /api/v1/merchant/orders/{id}`

### Preconditions
- Order already processed through payment and merchant transition steps.
- Admin account has valid admin role session.

### Steps
1. Admin opens orders list and filters by expected status.
2. Admin opens order detail.
3. Capture status/timeline snapshot.
4. Compare with user and merchant detail views for same order id.

### Expected UI assertions
- Admin list row and detail page show current status/payed timestamps.
- Filter by status includes target order only in correct status bucket.

### Expected backend assertions
- Admin API and user/merchant APIs report consistent status fields.

### Cross-surface consistency checks
- `backend == admin == merchant == user` for same order id/status.

### Risk notes
- Release control-plane blind spot risk if mismatched.

### Blockers
- Admin SSR session/cookie and env (`IDENTITY_URL`, encryption keys) must be correct.

---

## E2E-005 Permission Isolation Across Surfaces

### Case ID
- `E2E-W1-005`

### Flow name
- Role boundary enforcement (user/merchant/admin)

### Repos involved
- `rankmate_us`, `didaunao_mc_web`, `rankmate_fe`, `rankmate_be`

### Pages/routes
- User protected routes (`/orders/:orderId`)
- Merchant routes (`/orders`, `/orders/:id`)
- Admin routes (`/admin/orders`, `/admin/orders/:id`)

### APIs touched
- `GET /api/v1/admin/orders` with non-admin token
- `GET /api/v1/merchant/orders` with user token
- Protected user endpoints with expired/invalid token

### Preconditions
- Test tokens for each role and one expired/invalid token variant.

### Steps
1. Try admin endpoint with user token.
2. Try merchant endpoint with user token.
3. Try protected user endpoint with expired token.
4. Verify frontend route guards and redirects.

### Expected UI assertions
- Unauthorized role is redirected/blocked in each app.
- No restricted data is rendered before redirect.

### Expected backend assertions
- Unauthorized/forbidden responses returned (`401` or guarded `4xx` scope errors).

### Cross-surface consistency checks
- No role can read or mutate state outside permitted domain.

### Risk notes
- High security and compliance impact.

### Blockers
- Need role-specific credentials/tokens and deterministic token expiry setup.

---

## E2E-006 Duplicate Submit Safety (Selective)

### Case ID
- `E2E-W1-006`

### Flow name
- UI double-submit behavior on create order/payment

### Repos involved
- `rankmate_us`, `rankmate_be`

### Pages/routes
- `/orders/checkout`

### APIs touched
- `POST /api/v1/orders`
- `POST /api/v1/orders/{id}/payments`

### Preconditions
- Checkout form ready with stable cart state.

### Steps
1. Trigger create-order action twice quickly (same interaction window).
2. Inspect outgoing headers/requests.
3. Verify resulting order count and idempotency behavior.

### Expected UI assertions
- User sees one stable order flow outcome and no duplicate success confusion.

### Expected backend assertions
- Same idempotency key replay returns same order; no accidental duplicate with same key.

### Cross-surface consistency checks
- Merchant/admin should not see duplicate order for same idempotency replay case.

### Risk notes
- High bug yield for concurrency and retry race conditions.

### Blockers
- Needs request capture tooling in E2E harness for header-level checks.

## Execution Notes
- Keep E2E set intentionally small; use API checks to validate heavy state logic.
- Every E2E should emit order ids and timestamps for later correlation in API assertion matrix.
