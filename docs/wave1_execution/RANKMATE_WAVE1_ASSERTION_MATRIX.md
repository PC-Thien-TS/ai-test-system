# RANKMATE Wave 1 Assertion Matrix

## Scope
- Assertion contracts for API-first + selective E2E Wave 1 execution.
- Designed to be directly translatable into pytest assertions and Playwright checks.

## Source Basis
- `docs/wave1_execution/RANKMATE_WAVE1_API_CASES.md`
- `docs/wave1_execution/RANKMATE_WAVE1_E2E_CASES.md`
- `docs/RANKMATE_SOURCE_TO_TEST_COVERAGE_MAP.md`
- Backend and frontend source files listed in those documents.

## Why Wave 1
- Highest bug yield from enforcing strict invariants on auth, idempotency, callbacks, transitions, and cross-surface consistency.

---

## A) API Assertion Matrix

| Assertion ID | Assertion Type | Applies To | Assertion Contract | Source Basis | Failure Impact |
|---|---|---|---|---|---|
| API-A01 | Response schema | AUTH-API-001,003,006,007 | Success auth responses must include `result=20`, non-empty `token`, non-empty `refreshToken`, role/classification fields | `AuthController.cs`, frontend auth APIs | Blocks all protected flow tests |
| API-A02 | Error boundary | AUTH-API-002 | Invalid login must return non-200 and no valid token payload | `AuthController.cs` | Security and auth correctness risk |
| API-A03 | Permission boundary | AUTH-API-008,009, CONS-API-005 | Unauthorized role calls to admin/merchant endpoints must fail (`401` or guarded scope `4xx`) | `AdminAuthorizationFilter.cs`, merchant commands | Privilege escalation risk |
| API-A04 | Required header guard | ORD-API-003, PAY-API-001 (precondition) | Missing `Idempotency-Key` on guarded endpoints returns `400` with required message | `OrdersController.cs` | Duplicate-submit and replay safety failure |
| API-A05 | Order create contract | ORD-API-002 | Create order success must return canonical `order.id`, `status=10`, amount fields present | `OrdersController.cs`, `CreateOrderCommand.cs` | Core revenue flow failure |
| API-A06 | Validation contract | ORD-API-004,005 | Invalid quantity/SKU must be rejected and no order created | `CreateOrderCommand.cs`, order creation service path | Data integrity corruption |
| API-A07 | Idempotency replay | ORD-API-006 | Same key + same fingerprint returns equivalent response and same order id | `CreateOrderCommand.cs` | Duplicate order/charge risk |
| API-A08 | Idempotency mismatch | ORD-API-007 | Same key + changed fingerprint must fail (replay mismatch) | `CreateOrderCommand.cs` | Key abuse and inconsistent state risk |
| API-A09 | Retry-payment semantics | ORD-API-010,011 | Pending source order reuses same order; terminal source creates replacement order | `RetryOrderPaymentCommand.cs` | Payment recovery logic drift |
| API-A10 | Callback acceptance | PAY-API-003,009 | Valid callback returns `204` and updates intended payment/order state | `PaymentController.cs`, payment handlers | Financial correctness failure |
| API-A11 | Callback replay safety | PAY-API-004,007,010 | Duplicate or invalid callback must not duplicate financial/state mutation | payment handlers | Double charge/order mutation risk |
| API-A12 | Malformed callback reject | PAY-API-005,006 | Missing/invalid Stripe signature or malformed payload fails safely | `PaymentController.Handle`, stripe handler | Security exploit and false paid-state risk |
| API-A13 | Transition validity | MER-API-002..008 | Merchant actions only valid on legal previous status; invalid state must fail without mutation | ordering command handlers | State machine corruption |
| API-A14 | Admin list/detail consistency | CONS-API-001,002,006 | Admin list/detail statuses and filters reflect backend canonical values | `AdminOrdersController.cs`, admin FE APIs | Release-monitoring blind spot |

---

## B) UI Assertion Matrix

| Assertion ID | Surface | Applies To | Assertion Contract | Source Basis | Failure Impact |
|---|---|---|---|---|---|
| UI-U01 | User app | E2E-W1-001 | Authenticated session allows protected order routes and no sign-in modal loop | `rankmate_us/authGuard.ts`, `RouteGuard.ts` | User blocked from checkout |
| UI-U02 | User app | E2E-W1-001 | Search results render stores and route to store detail/menu | `SearchResult.tsx`, `StoreDetail.tsx` | Conversion entry broken |
| UI-U03 | User app | E2E-W1-001,006 | Checkout shows stable totals and creates one intended order outcome | `OrderCheckoutPage.tsx` | Duplicate submit confusion |
| UI-U04 | User app | E2E-W1-002,003 | Order tracking status and action buttons reflect backend legal state | `OrderTrackingPage.tsx` | Invalid user actions and trust issues |
| UI-U05 | Merchant app | E2E-W1-002,003 | Merchant requires login + selected store before order routes | `didaunao_mc_web/App.tsx` | Operational access leakage |
| UI-U06 | Merchant app | E2E-W1-003 | Only valid action buttons shown for current status | `OrderDetailPage.tsx` | Invalid transition attempts |
| UI-U07 | Admin app | E2E-W1-004 | Non-admin is redirected away from admin pages (SSR/HOC guard) | `adminPage.ts`, `withAdminConsoleHOC.tsx` | Admin data exposure |
| UI-U08 | Admin app | E2E-W1-004 | Orders list filter and detail status are coherent after refresh | `AdminOrdersPage.tsx`, `AdminOrderDetailPage.tsx` | Monitoring mismatch |
| UI-U09 | All UIs | E2E-W1-005 | Expired/invalid session leads to re-auth flow and no stale protected data | client `mainAxios.ts` + guards | Session leakage risk |

---

## C) Cross-Surface Consistency Matrix

| Assertion ID | Consistency Target | Applies To | Assertion Contract | Failure Signal | Priority |
|---|---|---|---|---|---|
| XSURF-C01 | `backend == user` | CONS-API-003, E2E-W1-003 | User detail status equals backend canonical order status | UI shows old/incorrect status | P0 |
| XSURF-C02 | `backend == merchant` | MER-API-001..005, CONS-API-004 | Merchant queue/detail status equals backend status | Merchant actions inconsistent with state | P0 |
| XSURF-C03 | `backend == admin` | CONS-API-001,002 | Admin list/detail status equals backend status | Admin monitors wrong status bucket | P0 |
| XSURF-C04 | `merchant == admin` | E2E-W1-004 | Same order id shows identical status in merchant and admin detail | Operational and monitoring divergence | P0 |
| XSURF-C05 | `admin == user` | E2E-W1-004 | User tracking status aligns with admin order status | Customer-facing misinformation | P0 |
| XSURF-C06 | Eventual convergence | CONS-API-007 | After transition/callback, all surfaces converge within agreed retry window | Persistent stale mismatch | P0 |

---

## D) Payment Integrity Matrix

| Assertion ID | Applies To | Assertion Contract | Source Basis | Failure Impact |
|---|---|---|---|---|
| PAY-I01 | PAY-API-003 | Valid callback marks payment/order as paid exactly once | `ProcessPaymentSuccessCommand.cs` | Financial loss or missed revenue |
| PAY-I02 | PAY-API-004 | Duplicate webhook event id is ignored (no duplicate mutation) | Stripe webhook dedupe repository call | Double processing risk |
| PAY-I03 | PAY-API-006 | Invalid Stripe signature is rejected and state remains unchanged | Stripe signature validation path | Security and fraud risk |
| PAY-I04 | PAY-API-010 | Invalid Momo signature causes no mutation | `UpdatePaymentCommand.cs` | False paid-state risk |
| PAY-I05 | PAY-API-007 | Already-paid callback is idempotent no-op | attempt status check in handler | Duplicate charge/timeline noise |
| PAY-I06 | PAY-API-008 | Callback after cancel does not create inconsistent terminal state | handler + state checks | State corruption and dispute risk |
| PAY-I07 | E2E-W1-002 | User payment result and merchant queue reflect same paid outcome | user/merchant APIs and UI components | Cross-surface payment mismatch |

---

## Execution Mapping (Assertion -> Case IDs)
- Auth/session: `API-A01..A03`, `UI-U01`, `UI-U09`, `XSURF-C06`
- Order/idempotency: `API-A04..A09`, `UI-U03`, `PAY-I07`
- Callback integrity: `API-A10..A12`, `PAY-I01..I06`
- Merchant transitions: `API-A13`, `UI-U06`, `XSURF-C01..C04`
- Admin-user consistency: `API-A14`, `UI-U07..U08`, `XSURF-C01..C06`

## Blockers
- Without deterministic data and webhook-signing capability, `API-A10..A12` and `PAY-I01..I06` cannot be validated reliably.
- Without role-isolated accounts and env parity, permission assertions (`API-A03`, `UI-U05`, `UI-U07`) are not trustworthy.

## Notes for Automation
- Keep assertion ids stable in pytest/Playwright implementation so failures map back to this matrix directly.
- Emit assertion-id tagged artifacts for ingestion by `ai_test_system` prioritization pipeline.
