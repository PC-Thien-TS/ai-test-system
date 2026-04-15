# RANKMATE Wave 1 Execution Order

## Scope
- Dependency-safe execution sequence for Wave 1 critical flow validation.
- API-first with selective E2E closure pass.

## Source Basis
- `docs/RANKMATE_WAVE1_TEST_PLAN.md`
- `docs/wave1_execution/RANKMATE_WAVE1_API_CASES.md`
- `docs/wave1_execution/RANKMATE_WAVE1_E2E_CASES.md`
- `docs/wave1_execution/RANKMATE_WAVE1_TEST_DATA_REQUIREMENTS.md`
- `docs/wave1_execution/RANKMATE_WAVE1_BLOCKERS_AND_DEPENDENCIES.md`

## Why Wave 1
- Order of execution is tuned for maximal bug discovery with minimal wasted runs:
  - first stabilize identity/permissions,
  - then financial/state-creation paths,
  - then transition and cross-surface convergence.

## Phase Plan (Recommended)

| Phase | Objective | Dependent test data | APIs involved | Repos involved | Expected bug yield | Blocks next phase? |
|---|---|---|---|---|---|---|
| 1 | Auth foundation and role isolation | TD-IDENT-* | `/auth/login`, `/auth/refresh-token`, `/admin/orders`, `/merchant/orders` | be, us, merchant, admin | High | Yes |
| 2 | Order create + idempotency correctness | TD-STORE-*, TD-MENU-*, TD-ORDER-PENDING-01 | `/orders/pricing-preview`, `/orders`, `/orders/{id}/retry-payment` | be, us | Critical | Yes |
| 3 | Payment callback integrity | TD-PAY-* + pending order fixture | `/orders/{id}/payments`, `/payments/stripe/webhook`, `/payments/momo/webhook`, `/orders/{id}/payments/verify` | be, us, merchant | Critical | Yes |
| 4 | Merchant transition validity | TD-ORDER-PAID/ACCEPTED/ARRIVED fixtures | `/merchant/orders/*` action endpoints + detail/list | be, merchant, us, admin | High | Yes |
| 5 | Admin-user status consistency | shared order ids from phases 2-4 | `/admin/orders`, `/admin/orders/{id}`, `/orders/{id}`, `/merchant/orders/{id}` | be, admin, us, merchant | High | Yes |
| 6 | Selective E2E consistency pass | all phase fixtures | cross-surface flow endpoints from E2E cases | all | Medium-High | Final gate |

---

## Detailed Execution Sequence

### Phase 0: Preflight (must pass before Phase 1)
- Validate env alignment and connectivity:
  - Backend health and API base URL reachable.
  - `rankmate_us` points to correct `VITE_BE`.
  - `didaunao_mc_web` points to correct `VITE_API_BASE_URL`/`VITE_MERCHANT_API_URL`.
  - `rankmate_fe` has valid `IDENTITY_URL` and cookie encryption settings.
- Validate secrets present for callback tests:
  - Stripe webhook secret.
  - Momo callback keys if included in run.
- Confirm role accounts and store fixtures are ready.

### Phase 1: Auth foundation
- Run: `AUTH-API-001..010`.
- Exit criteria:
  - Role login + refresh works.
  - Cross-role endpoint isolation enforced.
  - Session invalidation verified.

### Phase 2: Order create + idempotency
- Run: `ORD-API-001..011`.
- Exit criteria:
  - Create order deterministic and valid.
  - Missing-key and invalid-payload guards enforced.
  - Replay semantics validated (same key same payload, mismatch failure).

### Phase 3: Payment callback integrity
- Run: `PAY-API-001..011`.
- Exit criteria:
  - Payment init works.
  - Valid callbacks mutate once.
  - Duplicate/invalid callbacks do not corrupt state.

### Phase 4: Merchant transition validity
- Run: `MER-API-001..010`.
- Exit criteria:
  - Legal transitions succeed.
  - Illegal or stale transitions fail without mutation.

### Phase 5: Admin-user consistency
- Run: `CONS-API-001..007`.
- Exit criteria:
  - Admin list/detail aligns with user and merchant for same order ids.
  - Filter correctness and delayed-refresh convergence validated.

### Phase 6: Selective E2E closure pass
- Run: `E2E-W1-001..006` (minimum required path set).
- Exit criteria:
  - Core cross-surface flows reproduce API-level truth.
  - No unresolved P0 mismatch between backend and any surface.

---

## Expected Bug Yield by Phase

| Phase | Typical Defect Classes |
|---|---|
| 1 | token refresh loops, guard bypass, role leakage, invalid redirect behavior |
| 2 | idempotency regressions, payload validation gaps, duplicate order creation |
| 3 | callback signature handling issues, replay duplicates, stale paid-state bugs |
| 4 | invalid transition acceptance, stale-action race issues, action availability mismatch |
| 5 | admin/user/merchant status drift, filter errors, delayed consistency defects |
| 6 | integrated route/session/state regressions missed by API-only testing |

---

## Go/No-Go Gates

### Gate G1 (after Phase 1)
- No unresolved P0 auth/permission defects.
- If failed: stop Wave 1 implementation and fix auth baseline.

### Gate G2 (after Phase 3)
- Callback integrity cases pass for active gateway path.
- If failed: stop before merchant/admin consistency stages.

### Gate G3 (after Phase 5)
- Cross-surface status equality confirmed for target order set.
- If failed: run targeted triage before E2E closure.

### Gate G4 (final)
- Selective E2E core set passes with stable rerun behavior.

---

## Artifact Expectations Per Phase
- Persist case results with:
  - case id
  - request/response summary
  - order id(s)
  - role token context
  - assertion id outcomes from assertion matrix
- Format output for ingestion into `ai_test_system` requirement/risk queue as next step.

## Blockers
- Any unresolved critical blocker from `RANKMATE_WAVE1_BLOCKERS_AND_DEPENDENCIES.md` pauses affected phase.
- Do not run dependent phases with known unresolved upstream blockers.
