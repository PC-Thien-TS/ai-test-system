# RANKMATE Wave 1 API Cases

## Scope
- Wave 1 critical API coverage only.
- API-first execution pack for:
  1. Auth + session guards
  2. Order create + idempotency
  3. Payment callback integrity
  4. Merchant transition validity
  5. Admin-user status consistency

## Source Basis
- `docs/RANKMATE_WAVE1_TEST_PLAN.md`
- `docs/RANKMATE_SOURCE_TO_TEST_COVERAGE_MAP.md`
- Backend controllers/commands:
  - `rankmate_be/CoreV2.MVC/Api/AuthController.cs`
  - `rankmate_be/CoreV2.MVC/Api/OrdersController.cs`
  - `rankmate_be/CoreV2.MVC/Api/PaymentController.cs`
  - `rankmate_be/CoreV2.MVC/Api/MerchantOrdersController.cs`
  - `rankmate_be/CoreV2.MVC/Api/AdminOrdersController.cs`
  - `rankmate_be/CoreV2.Application/Features/Ordering/Commands/*.cs`
  - `rankmate_be/CoreV2.Application/Features/Payments/Commands/*`
- Frontend API wiring:
  - `rankmate_us/src/services/mainAxios.ts`, `rankmate_us/src/services/apis/*.ts`
  - `didaunao_mc_web/src/services/mainAxios.ts`, `didaunao_mc_web/src/services/apis/*.ts`
  - `rankmate_fe/src/services/mainAxios.ts`, `rankmate_fe/src/services/apis/*.ts`

## Why Wave 1
- Highest revenue and state-corruption risk surfaces.
- Direct conversion flow impact (login -> order -> payment).
- Multi-role consistency risk across user, merchant, admin.
- Permission boundary and callback replay risks are production-critical.

---

## A. Auth + Session Guards API Cases

### Assertions Focus
- Backend: auth result contract, token issuance/refresh, role-based access barriers.
- UI integration: token persistence and refresh compatibility per client interceptors.
- Cross-repo: token from one surface must not grant unauthorized role endpoints.

### Blockers
- Dedicated test identities for each role are required.
- Admin cookie/session encryption keys are needed for full admin surface validation.

| Case ID | Domain | Endpoint | Method | Auth role | Preconditions | Request payload | Expected status code | Expected response assertions | State assertions | Idempotency assertions | Cross-repo propagation assertions | Priority | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUTH-API-001 | Auth | `/api/v1/auth/login` | POST | anonymous -> user | Active user account exists | `{ "email": "<user_email>", "password": "<password>" }` | 200 | `result=20`, `data.token`, `data.refreshToken`, `data.userType` present | Token is accepted on protected `/api/v1/orders` | N/A | Token must work in `rankmate_us` axios auth header flow | P0 | High | Source: `AuthController.cs`, `rankmate_us/authAPI.ts` |
| AUTH-API-002 | Auth | `/api/v1/auth/login` | POST | anonymous | Invalid credentials | Wrong password payload | 4xx (not 200) | Response is error and does not include valid token pair | No session token should be persisted | N/A | `rankmate_us` and `didaunao_mc_web` must stay unauthenticated after failure | P0 | High | Accept 400/401 based on backend error policy |
| AUTH-API-003 | Auth | `/api/v1/auth/login` | POST | anonymous -> merchant | Merchant account exists | Merchant credential payload | 200 | `result=20`, token issued | Token accepted by `/api/v1/store/verify` and `/api/v1/merchant/orders` after profile switch | N/A | Required precursor for merchant queue flow | P0 | High | Merchant app uses dual-token strategy |
| AUTH-API-004 | Auth | `/api/v1/store/verify?forSelf=true&isverify=true&pageNumber=0&pageSize=1000` | GET | merchant user token | Merchant login token available | N/A | 200 | Store list payload is returned and contains selectable store id | Store context candidates available | N/A | Enables `/api/v1/authors/switch` and merchant operational token | P0 | High | Source: `didaunao_mc_web/store.api.ts`, `mainAxios.ts` |
| AUTH-API-005 | Auth | `/api/v1/authors/switch` | PUT | merchant user token | Valid `storeId` and `profileId` from verify response | `{ "storeId": <id>, "profileId": <id> }` | 200 | New auth payload contains token/refreshToken | Store-scope token can access merchant order endpoints | N/A | Merchant UI should route to `/dashboard` and `/orders` after switch | P0 | High | Source: `didaunao_mc_web/auth.api.ts` |
| AUTH-API-006 | Auth | `/api/v1/auth/login` | POST | anonymous -> admin | Admin account exists | Admin credential payload | 200 | `data.userType` maps to admin class | Token is accepted on `/api/v1/admin/orders` | N/A | Admin FE SSR/HOC should allow admin pages | P0 | High | Source: `AdminAuthorizationFilter.cs`, `adminPage.ts` |
| AUTH-API-007 | Auth | `/api/v1/auth/refresh-token` | POST | authenticated session | Valid token + refresh token pair | `{ "token": "<old>", "refreshToken": "<refresh>" }` | 200 | New token payload returned, `result=20` | Old token eventually expires; new token works on protected endpoint | N/A | Must be compatible with all 3 clients interceptors | P0 | High | Source: all three `mainAxios.ts` files |
| AUTH-API-008 | Permission | `/api/v1/admin/orders` | GET | non-admin token | User or merchant token available | N/A | 401 | Unauthorized response | No data leakage | N/A | Admin FE should redirect non-admin away from admin route | P0 | High | Source: `AdminAuthorizationFilter.cs`, `adminPage.ts` |
| AUTH-API-009 | Permission | `/api/v1/merchant/orders` | GET | user token (non-merchant scope) | User token exists | `?status=20` | 4xx | Access is denied (auth scope error) | No merchant order data exposed | N/A | User app token must not view merchant queue | P0 | High | Command handlers enforce `FORBIDDEN_SCOPE` |
| AUTH-API-010 | Session | `/api/v1/auth/logout` | POST | authenticated | Valid token/session | logout DTO per client (`LogoutDto`) | 200 | Logout response success | Refresh with old pair should fail; protected call should fail after signout | N/A | `rankmate_us` removes local/capacitor session; admin clears cookie; merchant clears local/session storage | P1 | Medium | Source: `AuthController.cs`, frontend auth/session helpers |

---

## B. Order Create + Idempotency API Cases

### Assertions Focus
- Backend: order creation invariants, payload validation, idempotency replay protection.
- UI integration: `rankmate_us` auto-injected `Idempotency-Key` for `POST /orders*`.
- Cross-repo: created order becomes visible downstream (merchant/admin) when state allows.

### Blockers
- Need deterministic store/menu data with active and unavailable SKUs.
- Need order type fixtures for Reservation and Preorder.

| Case ID | Domain | Endpoint | Method | Auth role | Preconditions | Request payload | Expected status code | Expected response assertions | State assertions | Idempotency assertions | Cross-repo propagation assertions | Priority | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ORD-API-001 | Order | `/api/v1/orders/pricing-preview` | POST | user | Eligible store, valid SKU list | `{ "storeId": <id>, "orderType": 20, "items": [{"skuId": <sku>, "quantity": 2}] }` | 200 | `data.totalAmount`, `data.totalDueNowAmount`, `data.currency` present | Preview values are non-negative and coherent | N/A | Preview totals should match checkout UI summary | P0 | High | Source: `OrdersController.cs`, `order.api.ts` |
| ORD-API-002 | Order | `/api/v1/orders` | POST | user | Valid store, valid items, header `Idempotency-Key` | `{ "storeId": <id>, "orderType": 20, "items": [{"skuId": <sku>, "quantity": 1}] }` | 200 | `result=20`, `data.id`, `data.status=10(Pending)` | Order is retrievable via `GET /orders/{id}` | First create with unique key stores response for replay | Order appears in user tracking and becomes payable | P0 | Critical | `OrdersController` requires idempotency header |
| ORD-API-003 | Validation | `/api/v1/orders` | POST | user | Missing `Idempotency-Key` | Same as valid payload | 400 | Error message contains `Idempotency-Key header is required` | No order created | N/A | UI should surface actionable error if interceptor missing | P0 | Critical | Explicit controller guard |
| ORD-API-004 | Validation | `/api/v1/orders` | POST | user | Invalid payload (`items=[]` or quantity<=0) | `{ "storeId": <id>, "items": [] }` | 400 | Error contains `OrderingErrorCodes.InvalidQuantity` behavior | No order created | N/A | No phantom order in merchant/admin views | P0 | High | `CreateOrderCommand` validation |
| ORD-API-005 | Catalog edge | `/api/v1/orders` | POST | user | SKU marked unavailable or non-existent | Payload contains invalid/unavailable skuId | 4xx | Creation rejected, no success order payload | Order count unchanged for user | N/A | Downstream merchant queue must not receive invalid order | P0 | High | Backed by `OrderCreationService` validation path |
| ORD-API-006 | Idempotency | `/api/v1/orders` | POST x2 | user | Same payload + same `Idempotency-Key` | Same request sent twice | 200 (both) | Second response returns same order id/payload contract | Only one order row effective | Replay-safe; no duplicate order | Merchant/admin should see one order only | P0 | Critical | `CreateOrderCommand` idempotency service replay |
| ORD-API-007 | Idempotency mismatch | `/api/v1/orders` | POST x2 | user | Same key, different payload fingerprint | 2nd request changes items | 4xx | Replay mismatch rejection (no second success create) | Original order remains only order for key | Detects key reuse abuse | Prevents cross-surface duplicate charge/order divergence | P0 | Critical | `IdempotencyReplayMismatch` path |
| ORD-API-008 | Duplicate submit | `/api/v1/orders` | POST x2 | user | Different idempotency keys, same payload, rapid submit | Two requests with different keys | 200/200 | Both may succeed by design | Two distinct orders may exist; this is expected with unique keys | Confirms idempotency scope is key-based | Must be flagged in UX risk and monitored in queue | P1 | High | Important for duplicate-click risk analysis |
| ORD-API-009 | Reservation path | `/api/v1/orders` | POST | user | Store supports reservation | `{ "storeId": <id>, "orderType": 10, "arrivalTime": "<iso>", "pax": 2, "items":[...] }` | 200 | Order contains reservation fields and deposit values if configured | Status pending and fields persisted | Replay semantics same as preorder | Merchant/admin detail should show same reservation metadata | P1 | High | Source: `CreateOrderCommand` reservation fields |
| ORD-API-010 | Retry payment seed behavior | `/api/v1/orders/{id}/retry-payment` | POST | user | Source order status is Pending | Header `Idempotency-Key` | 200 | `data.reusedExistingPendingOrder=true`, `targetOrderId=sourceOrderId` | No replacement order created | Same key replay returns same response | User/merchant/admin continue tracking same order id | P1 | High | Source: `RetryOrderPaymentCommand` |
| ORD-API-011 | Retry payment replacement | `/api/v1/orders/{id}/retry-payment` | POST | user | Source status Expired/Cancelled/Rejected | Header `Idempotency-Key` | 200 | `reusedExistingPendingOrder=false`, `targetOrderId != sourceOrderId` | Replacement order created in Pending | Same key replay returns same replacement result | Admin/merchant should surface target order status correctly | P1 | High | High consistency impact |

---

## C. Payment Callback Integrity API Cases

### Assertions Focus
- Backend: callback auth/validation, replay safety, status transitions.
- UI integration: payment result and tracking page must match backend truth.
- Cross-repo: successful paid state propagates to merchant queue and admin monitoring.

### Blockers
- Stripe webhook secret and Momo secret/access key are required in test env.
- Need deterministic callback payload generator for Stripe signature and Momo signature.

| Case ID | Domain | Endpoint | Method | Auth role | Preconditions | Request payload | Expected status code | Expected response assertions | State assertions | Idempotency assertions | Cross-repo propagation assertions | Priority | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PAY-API-001 | Payment init | `/api/v1/orders/{id}/payments` | POST | user | Pending order exists, `Idempotency-Key` provided | N/A | 200 | `paymentAttemptId`, `stripeClientSecret`, `expiresAt` returned | Payment attempt status pending created/reused | Same key should replay same attempt response | Checkout UI receives intent and can proceed | P0 | Critical | Source: `OrdersController.cs`, `order.api.ts` |
| PAY-API-002 | Payment verify | `/api/v1/orders/{id}/payments/verify` | GET | user | Order with payment attempt exists | N/A | 200 | Verification payload includes order/payment attempt status | Status coherent with current order state | N/A | Must match user tracking and admin/merchant views | P1 | High | Useful post-callback consistency check |
| PAY-API-003 | Stripe callback success | `/api/v1/payments/stripe/webhook` | POST | anonymous webhook | Valid signed Stripe event, `type=payment_intent.succeeded`, metadata includes `order_id`,`attempt_id` | Raw Stripe event JSON + `Stripe-Signature` header | 204 | No response body expected | Order status transitions Pending->Paid when valid | Event id dedupe prevents second mutation | Paid order should appear in merchant queue and admin list as paid | P0 | Critical | Source: `PaymentController.Handle`, `ProcessPaymentSuccessCommand` |
| PAY-API-004 | Stripe callback duplicate replay | `/api/v1/payments/stripe/webhook` | POST (repeat) | anonymous webhook | Same event id as PAY-API-003 | Exact same payload/signature | 204 | Callback accepted but no duplicate processing | No extra state transitions, no duplicate financial side effects | Deduped by `TryRecordEventAsync` | User/merchant/admin status remains stable | P0 | Critical | Replay safety core case |
| PAY-API-005 | Stripe callback malformed | `/api/v1/payments/stripe/webhook` | POST | anonymous webhook | Missing signature or malformed JSON | Broken body or missing `Stripe-Signature` | 400 | Request rejected | No payment/order mutation | N/A | No false paid state on any surface | P0 | Critical | `Invalid signature` branch |
| PAY-API-006 | Stripe callback invalid signature | `/api/v1/payments/stripe/webhook` | POST | anonymous webhook | Wrong signature for body | Valid-looking JSON + bad signature header | 400 | Invalid webhook response | No status mutation | N/A | No propagation to merchant/admin | P0 | Critical | `ConstructStripeEvent` throws invalid webhook |
| PAY-API-007 | Stripe callback after already paid | `/api/v1/payments/stripe/webhook` | POST | anonymous webhook | Attempt already in Paid | New callback for same attempt | 204 | Ignored path, no failure | Order remains paid, not reprocessed | Idempotent by status check | No duplicate timeline events in admin detail | P0 | High | Handler checks `attempt.Status == Paid` |
| PAY-API-008 | Callback after cancel | `/api/v1/payments/stripe/webhook` | POST | anonymous webhook | Order cancelled before callback arrives | Signed success callback payload | 204 | Handler returns without crashing | Order should not transition into inconsistent paid flow | Must be replay-safe | Merchant/admin/user must remain consistent on final state | P0 | High | Race-condition critical case |
| PAY-API-009 | MoMo callback success | `/api/v1/payments/momo/webhook` | POST | anonymous webhook | Matching transaction exists | `MomoPaymentResponse` with valid signature and success `resultCode` | 204 | No response body | Transaction status set to Paid | Repeated callback should not duplicate top-up | Wallet/order side effects reflected once | P1 | High | Source: `MomoPaymentResponse.cs`, `UpdatePaymentCommand` |
| PAY-API-010 | MoMo invalid signature | `/api/v1/payments/momo/webhook` | POST | anonymous webhook | Signature invalid | Momo-like payload with wrong signature | 204 | Endpoint still returns no content | No transaction mutation | Replay no-op | No UI paid state should appear from invalid callback | P1 | High | Handler logs and returns on invalid signature |
| PAY-API-011 | Frontend/backend sync | `/api/v1/orders/{id}`, `/api/v1/merchant/orders/{id}` | GET | user + merchant | Callback success already applied | N/A | 200 | Both surfaces report coherent paid/next actionable status | Status and payment timestamps match backend truth | N/A | User payment-result/order tracking and merchant queue show aligned status | P0 | Critical | Cross-surface integrity check |

---

## D. Merchant Transition Validity API Cases

### Assertions Focus
- Backend: legal transitions only (`Paid->Accepted->Arrived->WaitingCustomerConfirmation/...`).
- UI integration: action buttons should match backend-legal transitions.
- Cross-repo: each merchant action must propagate consistently to user/admin views.

### Blockers
- Need seeded orders in specific statuses (Paid, Accepted, Arrived, WaitingCustomerConfirmation).
- Need clock-stable environment for delayed action/race checks.

| Case ID | Domain | Endpoint | Method | Auth role | Preconditions | Request payload | Expected status code | Expected response assertions | State assertions | Idempotency assertions | Cross-repo propagation assertions | Priority | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MER-API-001 | Merchant queue | `/api/v1/merchant/orders?status=20&storeId=<id>` | GET | merchant store token | Store context switched | N/A | 200 | Paid orders list returns target order | Target order visible with expected status | N/A | Same order must be discoverable in admin list and user detail | P0 | High | Source: `MerchantOrdersController.GetList` |
| MER-API-002 | Transition | `/api/v1/merchant/orders/{id}/accept` | POST | merchant store token | Order status is Paid (20) | N/A | 200 | Response includes updated order snapshot | Status becomes Accepted (21) | Repeating on non-paid should fail | User `/orders/{id}` and admin detail show Accepted | P0 | Critical | `AcceptOrderCommand` expects previous Paid |
| MER-API-003 | Transition | `/api/v1/merchant/orders/{id}/reject` | POST | merchant store token | Order status is Paid | `{ "reason": "<reason>" }` | 200 | Order returned in terminal rejected/refund path | Not actionable for accept/arrived anymore | Duplicate reject should not create duplicate refund | User/admin show same terminal state | P0 | Critical | `RejectOrderCommand` via refund service |
| MER-API-004 | Transition | `/api/v1/merchant/orders/{id}/mark-arrived` | POST | merchant store token | Order status is Accepted | N/A | 200 | Order payload returned | Status becomes Arrived (22) | Repeating without state change should fail | User tracking enables relevant next actions | P0 | Critical | `MarkArrivedOrderCommand` expects Accepted |
| MER-API-005 | Transition | `/api/v1/merchant/orders/{id}/complete` | POST | merchant store token | Order status Arrived; if offline remaining >0 include collected amount | `{ "payAtStoreCollectedAmount": <decimal or null> }` | 200 | Order updated | Status moves to WaitingCustomerConfirmation (24) or remains completed flow | Second complete should be safe/no corruption | User can confirm complete; admin sees waiting state | P0 | Critical | `CompleteOrderCommand` logic |
| MER-API-006 | Validation | `/api/v1/merchant/orders/{id}/complete` | POST | merchant store token | Arrived order with offline remaining > 0 | `{}` | 400 | Error `PAY_AT_STORE_COLLECTED_AMOUNT_REQUIRED` | No status mutation | N/A | User/admin should not show false completion | P0 | High | Explicit command validation |
| MER-API-007 | Transition invalid | `/api/v1/merchant/orders/{id}/accept` | POST | merchant store token | Order status not Paid (e.g., Accepted/Cancelled) | N/A | 400 | Failure payload indicates invalid transition | Status unchanged | N/A | No inconsistent status drift across surfaces | P0 | High | `UpdateOrderStatusAsync` guarded transitions |
| MER-API-008 | Transition stale | `/api/v1/merchant/orders/{id}/mark-arrived` | POST | merchant store token | Another actor already moved status away from Accepted | N/A | 400 | Invalid state failure | No mutation from stale action | N/A | User/admin remain on authoritative backend status | P1 | High | Race prevention case |
| MER-API-009 | No-show path | `/api/v1/merchant/orders/{id}/mark-no-show` | POST | merchant store token | Eligible status per settlement rules | N/A | 200 or 400 | Success when valid, reject when invalid | Settlement/order statuses coherent | Repeat action should be safe | User/admin timelines must match result | P1 | Medium | Useful edge-path smoke |
| MER-API-010 | Merchant cancel | `/api/v1/merchant/orders/{id}/cancel` | POST | merchant store token | Status supports merchant cancel | N/A | 200 | Returns updated order | Order enters cancelled/refund-consistent state | Repeat cancel should not corrupt | User/admin reflect cancellation promptly | P1 | High | Source: `MerchantCancelOrderCommand` |

---

## E. Admin-User Status Consistency API Cases

### Assertions Focus
- Backend: admin list/detail reflect true order/payment state.
- UI integration: admin filters and user tracking route show same canonical status.
- Cross-repo: backend == user == merchant == admin for same order id.

### Blockers
- Requires shared order ids propagated across all three surfaces.
- Potential async delay in UI polling/refresh must be accounted for by retry windows.

| Case ID | Domain | Endpoint | Method | Auth role | Preconditions | Request payload | Expected status code | Expected response assertions | State assertions | Idempotency assertions | Cross-repo propagation assertions | Priority | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CONS-API-001 | Admin monitor | `/api/v1/admin/orders?pageNumber=0&pageSize=20&status=<s>` | GET | admin | Admin token + known order status | N/A | 200 | Paged list includes target order with expected status | Status in list aligns with backend order entity | N/A | Same status must match user `/orders/{id}` and merchant `/merchant/orders/{id}` | P0 | Critical | Source: `AdminOrdersController`, `orders.admin.api.ts` |
| CONS-API-002 | Admin detail | `/api/v1/admin/orders/{id}` | GET | admin | Existing order id | N/A | 200 | Detail includes order + timeline payload | Timeline/status timestamps are monotonic/coherent | N/A | Must match user tracking state and merchant detail state | P0 | Critical | High-value consistency oracle |
| CONS-API-003 | User detail | `/api/v1/orders/{id}` | GET | user owner token | User owns order | N/A | 200 | Returns canonical user-visible order state | No hidden invalid status values | N/A | Compare to admin and merchant detail for same id | P0 | Critical | Source: `OrdersController.GetDetail` |
| CONS-API-004 | Merchant detail | `/api/v1/merchant/orders/{id}` | GET | merchant store token | Order belongs to merchant org/store | N/A | 200 | Merchant detail status aligns with backend | Action availability inferred from same status | N/A | Must equal admin status and user tracking status | P0 | Critical | Source: `MerchantOrdersController.GetDetail` |
| CONS-API-005 | Permission boundary | `/api/v1/admin/orders/{id}` | GET | non-admin token | User or merchant token only | N/A | 401 | Unauthorized response | No sensitive order timeline exposure | N/A | Confirms isolation between consumer and admin surfaces | P0 | High | Admin guard enforcement |
| CONS-API-006 | Status filter correctness | `/api/v1/admin/orders?status=10|20|30|50` | GET | admin | Mixed status dataset | N/A | 200 | Returned rows match requested status filter only | No misclassified statuses in filtered results | N/A | Filtered counts should align with dashboard tiles using same API | P1 | High | Source: `AdminOrdersPage`, `DashboardOverview` |
| CONS-API-007 | Delayed update reconciliation | `/api/v1/orders/{id}`, `/api/v1/merchant/orders/{id}`, `/api/v1/admin/orders/{id}` | GET (poll window) | user + merchant + admin | Transition just executed (payment or merchant action) | N/A | 200 | Eventual status convergence within agreed SLA window | No permanent mismatch after refresh | N/A | Three surfaces converge to same canonical status | P0 | High | Core stale-cache detection case |

## Execution Notes
- All endpoints above should be executed against `api/v1` route prefix.
- Use deterministic idempotency keys (`wave1-<case>-<uuid>`) and persist request/response pairs for replay checks.
- Capture order ids from create/payment flows and reuse through merchant/admin/user consistency stages.
- Persist case outcome metadata in format consumable by `ai_test_system` requirement/risk queue input.
