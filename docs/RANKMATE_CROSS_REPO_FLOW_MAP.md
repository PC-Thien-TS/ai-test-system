# RANKMATE Cross-Repo Flow Map

## Scope
- End-to-end flow mapping across:
  - `rankmate_us` (user app)
  - `rankmate_be` (backend)
  - `didaunao_mc_web` (merchant web)
  - `rankmate_fe` (admin)
  - `ai_test_system` (planning/prioritization integration)

## Flow 1. User Login
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. User opens `/sign-up` or auth flow pages in `src/routes/AppRoutes.tsx`.
2. User submits login via `src/services/apis/authAPI.ts` (`auth/login`).
3. Backend processes in `CoreV2.MVC/Api/AuthController.cs`.
4. Token stored; `src/services/mainAxios.ts` injects `Authorization` for protected APIs.

### APIs Involved
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh-token`

### Critical State/Permission Notes
- Access to user routes is gated by `checkRoutePermission` in `src/middlewares/authGuard.ts`.

### Recommended Test Types
- `api`, `ui`, `permission`, `e2e`

### Risk Notes
- Token refresh and route guard hydration timing can break downstream flows.

### Blockers
- Need stable user accounts with known statuses (active vs not active).

---

## Flow 2. Search Store
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. User navigates `/search` -> `/search/result`.
2. `SearchResult.tsx` dispatches store search action.
3. `search.api.ts` calls backend `searches/stores`.
4. Backend resolves via `SearchController` in `rankmate_be`.

### APIs Involved
- `GET /api/v1/searches/stores`
- `GET /api/v1/searches/filters`
- `GET /api/v1/searches/suggestions/{keyword}`

### Critical State/Permission Notes
- Search routes are anonymous-allowed in app route policy.

### Recommended Test Types
- `api`, `ui`, `e2e`, `integration`

### Risk Notes
- Search relevance/order can affect conversion entry paths.

### Blockers
- Deterministic dataset required for stable assertions.

---

## Flow 3. Store Detail
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. User clicks store in search result (`SearchResult.tsx`).
2. App navigates to `/store/:uniqueId` (`StoreDetail.tsx`).
3. Store detail fetched through `store.api.ts`.
4. Backend serves `StoreController` uniqueId/detail path.

### APIs Involved
- `GET /api/v1/store/{uniqueId}`
- `GET /api/v1/store/{id}/reviews` (auxiliary)

### Critical State/Permission Notes
- Detail page links directly to menu route `/store/:uniqueId/menu`.

### Recommended Test Types
- `api`, `ui`, `e2e`

### Risk Notes
- Broken store-to-menu linking blocks checkout funnel.

### Blockers
- Test data must include stores with valid `uniqueId` and published menu.

---

## Flow 4. Add to Cart
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. User opens `/store/:uniqueId/menu` (`StoreMenuPage.tsx`).
2. App retrieves menu and eligibility.
3. User builds cart in UI state.
4. Pricing preview called before checkout transition.

### APIs Involved
- `GET /api/v1/stores/{storeId}/menu`
- `GET /api/v1/store/{storeId}/eligibility`
- `POST /api/v1/orders/pricing-preview`

### Critical State/Permission Notes
- Eligibility response gates whether checkout is allowed.

### Recommended Test Types
- `api`, `ui`, `integration`, `e2e`

### Risk Notes
- Eligibility/policy mismatch can cause silent checkout failure.

### Blockers
- Need seed data for eligibility variants (allowed, blocked, edge reasons).

---

## Flow 5. Checkout
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. User proceeds to `/orders/checkout`.
2. Order request finalized from cart payload.
3. App may call pricing preview again before create.

### APIs Involved
- `POST /api/v1/orders/pricing-preview`
- `POST /api/v1/orders`

### Critical State/Permission Notes
- `Idempotency-Key` is required by backend for order creation.
- FE interceptor auto-injects idempotency for `POST orders*`.

### Recommended Test Types
- `api`, `integration`, `ui`, `e2e`, `exploratory`

### Risk Notes
- Duplicate-submit and cross-store cart invariants are high-risk.

### Blockers
- Need deterministic way to assert server idempotency replay behavior.

---

## Flow 6. Create Order
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. Checkout calls `orderAPI.create()`.
2. Backend `OrdersController` -> `CreateOrderCommand`.
3. Order persisted with status gating and idempotency handling.

### APIs Involved
- `POST /api/v1/orders`

### Critical State/Permission Notes
- State and ownership checks in ordering commands.

### Recommended Test Types
- `api`, `integration`, `permission`, `exploratory`

### Risk Notes
- Wrong order status initialization breaks all downstream lifecycle paths.

### Blockers
- Requires stable cart/menu snapshots and user/store ownership setup.

---

## Flow 7. Payment Initiation
### Initiating Repo
- `rankmate_us`

### Flow Chain
1. Checkout requests payment intent.
2. Backend creates/reuses payment attempt.
3. Client receives intent data and continues provider flow.

### APIs Involved
- `POST /api/v1/orders/{id}/payments`
- `POST /api/v1/stripe-payment/create-payment-intent` (top-up/alias path)
- `POST /api/v1/orders/{id}/payments/wallet` (wallet branch)

### Critical State/Permission Notes
- Order state must be pending; invalid states rejected.

### Recommended Test Types
- `api`, `integration`, `e2e`, `exploratory`

### Risk Notes
- Payment init failures or wrong branch selection directly impact revenue.

### Blockers
- Payment provider sandbox credentials/setup may be required for full e2e.

---

## Flow 8. Payment Callback / Result
### Initiating Repo
- `rankmate_be` (callback receiver), then consumed by `rankmate_us`

### Flow Chain
1. Provider callback hits backend webhook endpoint.
2. Backend validates signature and dedupes events.
3. Payment/order statuses updated.
4. User app sees outcome in `/payment-result` and `/orders/:orderId` detail.

### APIs Involved
- `POST /api/v1/payments/stripe/webhook`
- `POST /api/v1/payments/momo/webhook`
- `GET /api/v1/orders/{id}`
- `GET /api/v1/orders/{id}/payments/verify` and `GET /api/v1/payments/transactions/{id}/verify` (verification paths)

### Critical State/Permission Notes
- Webhook dedupe/idempotency logic in payment command handlers.

### Recommended Test Types
- `api`, `integration`, `exploratory`

### Risk Notes
- Duplicate callbacks and stale status writes can corrupt order lifecycle.

### Blockers
- Requires valid mock/signature payload generation to exercise real verification paths.

---

## Flow 9. Merchant Sees Order
### Initiating Repo
- `didaunao_mc_web`

### Flow Chain
1. Merchant logs in and selects store context.
2. Merchant opens `/orders` queue.
3. UI calls `GET /merchant/orders` filtered by status/store.

### APIs Involved
- `POST /api/v1/auth/login`
- `GET /api/v1/store/verify` (store context)
- `PUT /api/v1/authors/switch`
- `GET /api/v1/merchant/orders`

### Critical State/Permission Notes
- Token context switching (user token vs store token) in merchant axios interceptor.

### Recommended Test Types
- `api`, `ui`, `permission`, `e2e`

### Risk Notes
- Incorrect context token can hide orders or cause unauthorized errors.

### Blockers
- Need merchant account with linked verified store + active queue data.

---

## Flow 10. Merchant Confirms/Rejects Order
### Initiating Repo
- `didaunao_mc_web`

### Flow Chain
1. Merchant opens `/orders/:id` detail.
2. Merchant action triggers endpoint (accept/reject/arrived/complete/no-show/cancel).
3. Backend updates order status via ordering commands.

### APIs Involved
- `POST /api/v1/merchant/orders/{id}/accept`
- `POST /api/v1/merchant/orders/{id}/reject`
- `POST /api/v1/merchant/orders/{id}/mark-arrived`
- `POST /api/v1/merchant/orders/{id}/complete`
- `POST /api/v1/merchant/orders/{id}/mark-no-show`
- `POST /api/v1/merchant/orders/{id}/cancel`

### Critical State/Permission Notes
- Action availability should follow backend status constraints.

### Recommended Test Types
- `api`, `ui`, `integration`, `e2e`, `exploratory`

### Risk Notes
- Invalid transitions and repeated actions are high-risk failure classes.

### Blockers
- Need deterministic order fixtures in each prerequisite status.

---

## Flow 11. Admin Sees Order/Payment State
### Initiating Repo
- `rankmate_fe`

### Flow Chain
1. Admin accesses `/admin/orders` with SSR/HOC guard.
2. Page queries admin orders list + details.
3. Dashboard also consumes order status aggregates.

### APIs Involved
- `GET /api/v1/admin/orders`
- `GET /api/v1/admin/orders/{id}`

### Critical State/Permission Notes
- Admin authorization enforced by backend filter and frontend guard.

### Recommended Test Types
- `api`, `ui`, `permission`, `integration`, `e2e`

### Risk Notes
- Monitoring inaccuracies can hide production-critical failures.

### Blockers
- Need admin test identity with valid role claims and seeded order data.

---

## Flow 12. Order Status Propagation Back to User
### Initiating Repo
- Status updated by `rankmate_be` (merchant/payment/user actions), consumed by `rankmate_us`

### Flow Chain
1. Order status changes from payment callback and merchant/user actions.
2. User tracking page fetches order detail.
3. UI enables/disables lifecycle actions by status.

### APIs Involved
- Producer endpoints:
  - merchant action endpoints
  - payment webhook endpoints
  - user lifecycle endpoints
- Consumer endpoints:
  - `GET /api/v1/orders/{id}`

### Critical State/Permission Notes
- Status machine shared across user and merchant flows; consistency is essential.

### Recommended Test Types
- `integration`, `api`, `ui`, `e2e`, `exploratory`

### Risk Notes
- Stale or conflicting status propagation causes incorrect user actions (retry/cancel/confirm/dispute).

### Blockers
- Need synchronized multi-role test orchestration for reliable propagation assertions.

---

## AI QA Integration Hook (for Next Phase)
- Source-derived flow artifacts should be transformed into requirement/risk inputs in `ai_test_system`:
  - requirement ingestion: `orchestrator/advanced_qa/requirement_*`
  - risk/execution prioritization: `orchestrator/advanced_qa/risk_*`, `execution_queue.py`
- Execution API surface available at `ai_test_system/api/routes/runs.py` (mounted under `/runs` in `api/app.py`).
