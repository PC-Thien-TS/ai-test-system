# RANKMATE Wave 1 Test Data Requirements

## Scope
- Concrete data and environment dependencies required to execute Wave 1 API and selective E2E cases.
- This is a requirements pack, not seed script implementation.

## Source Basis
- `docs/RANKMATE_WAVE1_API_CASES.md`
- `docs/RANKMATE_WAVE1_E2E_CASES.md`
- Source contracts:
  - `rankmate_be/CoreV2.MVC/Api/*.cs`
  - `rankmate_be/CoreV2.Domain/Models/Payments/Momo/MomoPaymentResponse.cs`
  - `rankmate_us/src/types/order.type.ts`
  - `rankmate_us/src/config/env.ts`, `src/services/mainAxios.ts`
  - `didaunao_mc_web/src/services/mainAxios.ts`, `src/store/session.ts`
  - `rankmate_fe/src/services/mainAxios.ts`, `src/features/admin/lib/adminPage.ts`

## Why Wave 1
- Data quality directly controls determinism for idempotency, callback, transition, and consistency checks.
- Missing seed dependencies will invalidate bug triage outcomes.

---

## 1) Identity and Role Data

| Data ID | Required Entity | Mandatory Fields | Used By Cases | Owner | Notes |
|---|---|---|---|---|---|
| TD-IDENT-USER-01 | Active end-user account | `email`, `password`, `userType=end-user`, active status | AUTH-API-001, E2E-W1-001 | QA + BE | Must own created orders for tracking tests |
| TD-IDENT-USER-02 | Invalid user credential variant | Same email, wrong password | AUTH-API-002 | QA | For negative auth validation |
| TD-IDENT-MER-01 | Merchant login account | `email`, `password`, `organizationId`, merchant-capable `userType` | AUTH-API-003..005, MER-API-* | QA + BE | Must have switchable profile |
| TD-IDENT-MER-STORE-01 | Merchant profile mapping | `profileId`, linked `storeId` | AUTH-API-005, E2E-W1-002..004 | BE | Required by `/authors/switch` |
| TD-IDENT-ADMIN-01 | Admin account | `email`, `password`, admin `userType` recognized by admin guard | AUTH-API-006, CONS-API-* | QA + BE | Needed for `/api/v1/admin/orders` and admin pages |
| TD-IDENT-XROLE-01 | Cross-role token set | user token, merchant token, admin token, expired token | AUTH-API-008..009, E2E-W1-005 | QA | For permission isolation and expiry checks |

### Blockers
- No dedicated test identities -> high flakiness and environment contamination.
- Admin role classification mismatch breaks admin surface coverage.

---

## 2) Store, Menu, and Eligibility Data

| Data ID | Required Entity | Mandatory Fields | Used By Cases | Owner | Notes |
|---|---|---|---|---|---|
| TD-STORE-01 | Active orderable store | `storeId`, `uniqueId`, active verification/status, org ownership | ORD-API-001..009, E2E-W1-001 | BE + QA | Must be visible in `/searches/stores` |
| TD-STORE-02 | Payment-enabled store | Stripe/MoMo enabled gateway mapping | PAY-API-* | BE + DevOps | Needed for payment init + callback flow |
| TD-STORE-03 | Disabled or non-eligible store | eligibility false condition | ORD-API edge coverage | BE | For negative eligibility path |
| TD-MENU-01 | Published menu set | `skuId`, price, availability true | ORD-API-001..002, E2E-W1-001 | BE | Core create-order payload source |
| TD-MENU-02 | Unavailable/invalid SKU set | sku marked unavailable or deleted | ORD-API-005 | BE | Must return create-order rejection |

### Blockers
- If menu publication/eligibility state is unstable, checkout tests become nondeterministic.

---

## 3) Order State Fixtures

| Data ID | Required Entity | Mandatory Fields | Used By Cases | Owner | Notes |
|---|---|---|---|---|---|
| TD-ORDER-PENDING-01 | Pending order fixture | `orderId`, `status=10`, owner user, merchant store | ORD-API-010, PAY-API-001 | QA + BE | Can come from create-order case |
| TD-ORDER-PAID-01 | Paid order fixture | `status=20` after callback | MER-API-001..003 | QA + BE | Generated from payment callback success |
| TD-ORDER-ACCEPTED-01 | Accepted order fixture | `status=21` | MER-API-004, stale transition cases | QA | Used to test `mark-arrived` |
| TD-ORDER-ARRIVED-01 | Arrived order fixture | `status=22`, `totalDueNowAmount`, `totalAmount` | MER-API-005..006 | QA | Complete action validation |
| TD-ORDER-WAITCONF-01 | Waiting customer confirmation fixture | `status=24` | user confirm-complete consistency checks | QA | Expected post-complete state |
| TD-ORDER-TERMINAL-01 | Cancelled/Rejected/Expired fixture | status in `{50,60,90}` | ORD-API-011 retry replacement | QA | Retry-payment replacement path |

### Blockers
- No deterministic state fixtures means transition tests become order-dependent and flaky.

---

## 4) Payment and Webhook Simulation Data

| Data ID | Required Entity | Mandatory Fields | Used By Cases | Owner | Notes |
|---|---|---|---|---|---|
| TD-PAY-STRIPE-SECRET-01 | Stripe webhook secret | `PaymentGateway:Stripe:WebhookSecret` (or active Stripe mode secret) | PAY-API-003..008 | DevOps + BE | Use secret name only, never commit value |
| TD-PAY-STRIPE-EVENT-01 | Stripe success event payload | `type=payment_intent.succeeded`, metadata (`order_id`,`attempt_id`) | PAY-API-003..004 | QA + BE | Payload body must align with payment attempt |
| TD-PAY-STRIPE-EVENT-NEG-01 | Invalid stripe payload variants | malformed JSON, wrong signature, missing signature | PAY-API-005..006 | QA | Required for security checks |
| TD-PAY-MOMO-SECRET-01 | Momo callback secret set | `PaymentGateway:Momo:AccessKey`, `SecretKey`, `PartnerCode` | PAY-API-009..010 | DevOps + BE | Needed for signature verification path |
| TD-PAY-MOMO-IPN-01 | Momo IPN payload | Fields in `MomoPaymentResponse` including `OrderId`, `RequestId`, `Amount`, `Signature`, `ResultCode` | PAY-API-009..010 | QA + BE | Must match transaction lookup conditions |

### Webhook Simulation Requirements
- Stripe:
  - Generate `Stripe-Signature` with the active webhook secret and exact JSON body.
  - Ensure event id reuse for duplicate replay test.
- Momo:
  - Build callback signature with configured momo secret.
  - Provide both success and invalid signature variants.

### Blockers
- Missing secrets or signature tooling is a hard blocker for callback integrity scope.

---

## 5) Environment Variables and Config Dependencies

| Repo | Required Config Key(s) | Why Needed | Cases Impacted | Owner |
|---|---|---|---|---|
| `rankmate_be` | `ConnectionStrings:*`, `Jwt:*`, payment gateway keys, webhook secrets | API auth + payment and callback validation | all Wave 1 API | DevOps + BE |
| `rankmate_us` | `VITE_BE`, `VITE_STRIPE_PUBLISHABLE_KEY` (if UI payment), optional `VITE_BE_PAYMENT_SERVICE` | API base + payment UI behavior | E2E-W1-001..003, AUTH/ORD/PAY APIs | FE + QA |
| `didaunao_mc_web` | `VITE_API_BASE_URL` or `VITE_MERCHANT_API_URL` | Merchant API routing | AUTH-API-003..005, MER-API-* | FE + QA |
| `rankmate_fe` | `IDENTITY_URL`, `COOKIE_DOMAIN`, `ENCRYPT_SECRET_KEY`, `ENCRYPT_IV` | Admin API base + SSR session decrypt and guard | AUTH-API-006, CONS-API-* | FE + DevOps |
| `ai_test_system` | Output path and run metadata conventions | Ingesting case execution artifacts | Post-execution ingestion | QA Platform |

### Feature Flags
- No Wave 1-critical frontend feature flag gating found for auth/order/payment/merchant/admin status paths.
- Search-related feature toggles exist in backend settings but are not primary blockers for Wave 1 critical path.

---

## 6) Data Lifecycle and Isolation Requirements

### Required reset/isolation policy
- Use dedicated Wave 1 test tenant/store/users.
- Reset or isolate orders created in Wave 1 run by run id tag (`wave1_run_id`) where possible.
- Never reuse production-like finance/payment credentials in automation logs.

### Minimal deterministic dataset checklist
1. 1 active end-user.
2. 1 merchant account + 1 verified store mapping.
3. 1 admin account.
4. 1 orderable store with 3 valid SKUs + 1 unavailable SKU.
5. 1 callback-capable payment attempt path.
6. Known order ids in statuses Pending/Paid/Accepted/Arrived/WaitingCustomerConfirmation.

## Blockers Summary
- Hard blockers: webhook secrets/tooling, missing role accounts, missing store/profile mapping.
- Medium blockers: unstable search/menu dataset, inconsistent env base URLs.
- Recommended owners:
  - BE: state fixture generation + callback contract support.
  - FE: env alignment and guard behavior stabilization.
  - DevOps: secrets and isolated test environment.
  - QA: deterministic dataset governance and case data registry.
