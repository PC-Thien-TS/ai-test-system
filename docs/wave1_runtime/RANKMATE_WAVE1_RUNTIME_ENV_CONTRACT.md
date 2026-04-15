# RANKMATE Wave 1 Runtime Env Contract

## A. Findings
- Runtime source of truth inspected:
  - `tests/rankmate_wave1/conftest.py`
  - `tests/rankmate_wave1/helpers/config.py`
  - `docs/wave1_execution/RANKMATE_WAVE1_API_CASES.md`
  - `docs/wave1_execution/RANKMATE_WAVE1_TEST_DATA_REQUIREMENTS.md`
  - `docs/wave1_execution/RANKMATE_WAVE1_BLOCKERS_AND_DEPENDENCIES.md`
- Current local state on `2026-04-14`:
  - `ai_test_system/.env` is missing.
  - All Wave 1 env variables are missing.
  - `rankmate_be` launch ports are not reachable from current runtime process.

## B. Runtime Variable Contract

### 1) Suite enablement and connectivity
| Variable | Required | Used by cases | Purpose | Safe example |
|---|---|---|---|---|
| `RANKMATE_WAVE1_ENABLED` | Yes | all `*-API-*` | Enable Wave 1 suite | `1` |
| `API_BASE_URL` | Yes | all `*-API-*` | Backend host root | `http://localhost:5209` |
| `API_PREFIX` | Yes | all `*-API-*` | API prefix | `/api/v1` |
| `API_TIMEOUT_SEC` | Optional | all | request timeout | `30` |
| `RANKMATE_WAVE1_VERIFY_SSL` | Optional | all | TLS verify toggle | `0` |
| `RANKMATE_WAVE1_DEBUG` | Optional | all | request debug logging | `0` |

### 2) Auth identity set
| Variable | Required | Used by cases | Purpose | Safe example |
|---|---|---|---|---|
| `API_USER` | Yes for auth/order/payment/consistency | `AUTH-API-001,002,007,008,009,010`, most `ORD/PAY/CONS` | End-user login | `qa_user@example.com` |
| `API_PASS` | Yes with `API_USER` | same as above | End-user password | `change_me` |
| `API_MERCHANT_USER` | Yes for merchant flows | `AUTH-API-003,004,005`, all `MER-API-*`, `CONS-API-*`, `PAY-API-011` | Merchant login | `qa_merchant@example.com` |
| `API_MERCHANT_PASS` | Yes with `API_MERCHANT_USER` | same as above | Merchant password | `change_me` |
| `API_ADMIN_USER` | Yes for admin flows | `AUTH-API-006`, `CONS-API-*` | Admin login | `qa_admin@example.com` |
| `API_ADMIN_PASS` | Yes with `API_ADMIN_USER` | same as above | Admin password | `change_me` |

### 3) Store/SKU and state seeds
| Variable | Required | Used by cases | Purpose |
|---|---|---|---|
| `API_ORDER_STORE_ID`, `API_ORDER_SKU_ID` | Yes for order/payment bootstrap | `ORD-API-001,002,003,004,006,007,008,009,010`, `PAY-API-001,002,003,004,007,008,011` and consistency auto-setup | Deterministic create-order payload |
| `API_DISABLED_SKU_ID` or `API_OUT_OF_STOCK_SKU_ID` | Optional but needed for full negative coverage | `ORD-API-005` | Unavailable SKU rejection |
| `API_CANCELLED_ORDER_ID` | Needed for terminal retry path | `ORD-API-011` | Existing cancelled/terminal order |
| `API_MERCHANT_STORE_ID` | Recommended for stable merchant scope | merchant/consistency + some payment consistency | Merchant store targeting |
| `API_PAID_ORDER_ID` | Yes for `MER-API-001,002` | Paid seed order |
| `API_REJECTABLE_PAID_ORDER_ID` | Yes for `MER-API-003` | Dedicated reject seed |
| `API_ACCEPTED_ORDER_ID` | Yes for `MER-API-004` | Accepted seed |
| `API_ARRIVED_ORDER_ID` | Yes for `MER-API-005` | Arrived seed |
| `API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID` | Yes for `MER-API-006` | Arrived seed requiring collected amount |
| `API_NON_PAID_ORDER_ID` / `API_STALE_TRANSITION_ORDER_ID` / `API_NO_SHOW_ORDER_ID` / `API_MERCHANT_CANCELLABLE_ORDER_ID` / `API_PENDING_ORDER_ID` | Needed for `MER-API-007..010` | Invalid/stale/no-show/cancel branches |
| `API_CONSISTENCY_ORDER_ID` | Optional (auto-created if missing) | `CONS-API-*` | Shared order id for cross-surface checks |

### 4) Payment callback realism
| Variable | Required | Used by cases | Purpose |
|---|---|---|---|
| `API_STRIPE_WEBHOOK_SECRET` | Required for Stripe signed callback cases | `PAY-API-003,004,007,008,011` | Sign Stripe webhook payload |
| `API_MOMO_ACCESS_KEY`, `API_MOMO_SECRET_KEY`, `API_MOMO_PARTNER_CODE`, `API_MOMO_REQUEST_ID`, `API_MOMO_TRANSACTION_ORDER_ID`, `API_MOMO_TRANSACTION_AMOUNT` | Required for MoMo success callback case | `PAY-API-009` | Build/sign MoMo callback payload |

## C. Mandatory vs Optional by Execution Phase
- Phase A (Auth): `RANKMATE_WAVE1_ENABLED`, `API_BASE_URL`, `API_PREFIX`, `API_USER`, `API_PASS` (+ merchant/admin creds for full auth pack).
- Phase B (Order): Phase A + `API_ORDER_STORE_ID`, `API_ORDER_SKU_ID`.
- Phase C (Payment): Phase B + callback secrets for signed callback cases.
- Phase D (Merchant/Consistency): Phase B + merchant/admin creds + seeded order IDs.

## D. Current Runtime Snapshot (This Session)
- `RANKMATE_WAVE1_ENABLED`: missing in environment file (defaulted to `0`).
- `API_BASE_URL`: missing.
- Role credentials: missing.
- Seeds and webhook secrets: missing.
- Local backend probe: unreachable at `http://localhost:5209`.

## E. Activation Procedure
1. Copy `.env.wave1.example` to `.env` in `ai_test_system`.
2. Fill connectivity + role credentials first.
3. Confirm backend reachability:
   - `python -c "import requests; print(requests.get('http://<base>/').status_code)"`
4. Run Phase A:
   - `pytest -q -rs tests/rankmate_wave1/test_auth_api.py`
5. Add store/SKU seeds, then run Phase B:
   - `pytest -q -rs tests/rankmate_wave1/test_order_api.py`
6. Add payment secrets and seeded state IDs, then run Phases C/D.

