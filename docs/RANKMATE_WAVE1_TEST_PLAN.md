# RANKMATE Wave 1 Test Plan (Critical Flows)

## Objective
- Execute the minimum critical cross-repo flow set needed to validate release-critical RankMate behavior.
- Focus areas required by scope: Auth, Search, Cart, Order Creation, Payment, Merchant handling, Admin tracking.

## Wave 1 Entry Criteria
- Backend (`rankmate_be`) deployed and reachable with test environment config.
- User app (`rankmate_us`), merchant web (`didaunao_mc_web`), admin (`rankmate_fe`) configured against same backend dataset.
- Seed identities exist:
  - user account (active)
  - merchant account linked to verified store
  - admin account
- Seed store/menu exists and is orderable.

## Execution Order (Recommended)
1. Auth foundation (user + merchant + admin access)
2. User discovery + store detail + menu/eligibility
3. Cart/pricing/checkout/order creation
4. Payment initiation + callback/result verification
5. Merchant queue + order action transitions
6. User order tracking and post-action state validation
7. Admin order visibility and status consistency checks

## Wave 1 Test Items

| Order | Wave 1 Item | Why in Wave 1 | Involved Repos | Backend Endpoints | UI Pages/Screens | Test Type | Preconditions/Test Data | Likely Blockers |
|---|---|---|---|---|---|---|---|---|
| 1 | User login + token refresh | Required gateway for all protected user flows | `rankmate_us`, `rankmate_be` | `POST /auth/login`, `POST /auth/refresh-token` | `/sign-up`/auth pages + protected route navigation | `api`, `ui`, `permission`, `e2e` | Active user credentials | account status variance, refresh token expiry behavior |
| 2 | Merchant login + store context activation | Required before merchant queue/actions | `didaunao_mc_web`, `rankmate_be` | `POST /auth/login`, `GET /store/verify`, `PUT /authors/switch` | `/login`, `/select-store` | `api`, `ui`, `permission`, `e2e` | Merchant user mapped to verified store | dual-token session misrouting |
| 3 | Admin access guard + orders page access | Required for release monitoring | `rankmate_fe`, `rankmate_be` | `GET /admin/orders` | `/admin/orders` | `permission`, `ui`, `api` | Admin user with valid role | SSR auth cookie/session setup |
| 4 | Search stores | Top-of-funnel conversion path | `rankmate_us`, `rankmate_be` | `GET /searches/stores`, `GET /searches/filters` | `/search`, `/search/result` | `api`, `ui`, `e2e` | Searchable stores seed data | unstable ranking/order for assertions |
| 5 | Store detail -> menu transition | Required handoff into cart/checkout | `rankmate_us`, `rankmate_be` | `GET /store/{uniqueId}`, `GET /stores/{storeId}/menu` | `/store/:uniqueId`, `/store/:uniqueId/menu` | `ui`, `api`, `e2e` | Store uniqueId + published menu | missing menu publication state |
| 6 | Eligibility + pricing preview | Hard gate before checkout/order creation | `rankmate_us`, `rankmate_be` | `GET /store/{id}/eligibility`, `POST /orders/pricing-preview` | `StoreMenuPage`, `OrderCheckoutPage` | `api`, `integration`, `ui` | Eligible store + known pricing items | policy toggles and edge reason codes |
| 7 | Create order with idempotency | Revenue-critical transaction entry | `rankmate_us`, `rankmate_be` | `POST /orders` | `/orders/checkout` | `api`, `integration`, `e2e`, `exploratory` | user + store + cart payload | duplicate-submit and idempotency replay checks |
| 8 | Payment initiation (order intent / wallet branch) | Required for paid order completion | `rankmate_us`, `rankmate_be` | `POST /orders/{id}/payments`, `POST /orders/{id}/payments/wallet` | `OrderCheckoutPage` | `api`, `integration`, `ui`, `e2e` | order in pending state | provider sandbox and wallet balance state |
| 9 | Payment callback + payment result | Highest financial/state integrity risk | `rankmate_be`, `rankmate_us` | `POST /payments/stripe/webhook`, `POST /payments/momo/webhook`, `GET /orders/{id}` | `/payment-result`, `/orders/:orderId` | `api`, `integration`, `exploratory` | signed/mocked callback payloads | signature fixture generation |
| 10 | Merchant order queue visibility | Operational SLA-critical | `didaunao_mc_web`, `rankmate_be` | `GET /merchant/orders`, `GET /merchant/orders/{id}` | `/orders`, `/orders/:id` | `api`, `ui`, `e2e` | order assigned to merchant store | store-token context and data routing |
| 11 | Merchant actions and transition validity | Core operational flow + status correctness | `didaunao_mc_web`, `rankmate_be` | `POST /merchant/orders/{id}/accept|reject|mark-arrived|complete|mark-no-show|cancel` | `/orders/:id` | `api`, `ui`, `integration`, `e2e`, `exploratory` | orders seeded in appropriate statuses | invalid transition edge cases |
| 12 | User order tracking after merchant/payment updates | Verifies status propagation to customer | `rankmate_us`, `rankmate_be`, `didaunao_mc_web` | `GET /orders/{id}` + lifecycle actions (`retry-payment`, `confirm-arrival`, `confirm-complete`, `report-not-arrived`) | `/orders/:orderId` | `integration`, `ui`, `e2e`, `exploratory` | same order exercised across roles | multi-role orchestration timing |
| 13 | Admin order monitoring consistency | Final control-plane check for release readiness | `rankmate_fe`, `rankmate_be` | `GET /admin/orders`, `GET /admin/orders/{id}` | `/admin/orders`, `/admin/orders/:id`, dashboard widgets | `api`, `ui`, `integration`, `permission` | existing orders with varied statuses | status mapping drift vs backend |

## Wave 1 Risk Focus (Must Assert)
- Duplicate checkout prevention (idempotency behavior).
- Payment callback dedupe and status integrity.
- Invalid order state transition rejection.
- Merchant/user/admin view consistency for the same order timeline.
- Permission boundary enforcement (non-admin/non-merchant access).

## Wave 1 Exit Criteria
- All P0 flows above executed with recorded pass/fail evidence.
- No unresolved blocker in payment callback integrity or order transition correctness.
- Any remaining failures are triaged with clear owner and severity.

## Immediate Follow-Up After Wave 1
- Feed executed findings into `ai_test_system` requirement/risk contracts.
- Use risk prioritization queue to define Wave 2 (disputes, verify-store, wallet/finance, notifications, deeper exploratory).
