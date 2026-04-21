# RANKMATE Wave 1 Blockers and Dependencies

## Scope
- Explicit blockers and external/internal dependencies for executing Wave 1 API and selective E2E pack.

## Source Basis
- `docs/wave1_execution/RANKMATE_WAVE1_API_CASES.md`
- `docs/wave1_execution/RANKMATE_WAVE1_E2E_CASES.md`
- `docs/wave1_execution/RANKMATE_WAVE1_TEST_DATA_REQUIREMENTS.md`
- Source files for payment/auth/session behavior across all repos.

## Why Wave 1
- These blockers directly determine whether critical risk cases can run deterministically.

## Blockers Table

| Blocker ID | Blocker | Severity | Affected Cases | Workaround (if any) | Recommended Owner |
|---|---|---|---|---|---|
| BLK-W1-001 | Missing dedicated Wave 1 test accounts (user, merchant, admin) | Critical | AUTH-API-001..010, all E2E | Temporary shared accounts only for manual dry-run; not acceptable for automation baseline | QA + BE |
| BLK-W1-002 | Merchant profile-to-store mapping unavailable (`/store/verify`, `/authors/switch`) | Critical | AUTH-API-004..005, MER-API-* , E2E-W1-002..004 | Manual DB mapping in test env | BE |
| BLK-W1-003 | Stripe webhook secret not available to QA runner | Critical | PAY-API-003..008, E2E-W1-002 | Use BE-owned helper endpoint/tool in non-prod env to sign payloads | DevOps + BE |
| BLK-W1-004 | Momo callback signature generation capability absent | High | PAY-API-009..010 | Focus Stripe path first; keep MoMo as blocked with explicit status | BE + QA |
| BLK-W1-005 | Deterministic store/menu/SKU dataset missing (including unavailable SKU) | Critical | ORD-API-001..009, E2E-W1-001, E2E-W1-006 | Manual seed script + immutable fixture IDs for test window | BE + QA |
| BLK-W1-006 | Payment sandbox credentials or gateway wiring inconsistent across env | Critical | PAY-API-001..011, E2E-W1-002 | Switch to callback simulation mode while preserving real handler logic | DevOps + BE |
| BLK-W1-007 | Admin env mismatch (`IDENTITY_URL`, cookie encryption keys) | High | AUTH-API-006, CONS-API-*, E2E-W1-004 | API-only admin checks until FE env parity restored | FE + DevOps |
| BLK-W1-008 | User and merchant base URL mismatch to backend test env | High | All cross-repo E2E | Standardize env files and health-check all clients pre-run | FE + QA |
| BLK-W1-009 | No deterministic order-state fixture generation (Paid/Accepted/Arrived/etc.) | Critical | MER-API-002..010, CONS-API-001..007, E2E-W1-003..004 | Build ordered API setup chain to create states at runtime | QA + BE |
| BLK-W1-010 | Async UI refresh timing causes stale reads during consistency assertions | Medium | CONS-API-007, E2E-W1-003..004 | Define retry window and forced refresh checkpoints | QA |
| BLK-W1-011 | Callback replay observability is log-only, limited explicit audit fields | Medium | PAY-API-004, PAY-API-007 | Correlate via order/payment attempt state before/after each callback replay | BE + QA |
| BLK-W1-012 | Route-guard behavior differs by app session mechanism (cookies vs local/session storage vs capacitor) | Medium | AUTH-API-010, E2E-W1-005 | Separate per-surface guard checks with explicit setup/teardown | QA |

## Dependency Graph (Execution-Critical)

1. Identity and role setup
- Blocks: Auth foundation, admin/merchant isolation.

2. Store/menu/orderable fixtures
- Blocks: Order create/idempotency and downstream payment/transition tests.

3. Payment secret and callback simulation capability
- Blocks: Callback integrity and merchant-after-payment checks.

4. State fixture orchestration
- Blocks: Merchant transition and consistency phases.

5. Frontend env parity
- Blocks: Selective E2E and cross-surface consistency validation.

## Recommended Triage Order
1. Resolve BLK-W1-001, BLK-W1-002, BLK-W1-005.
2. Resolve BLK-W1-003 and BLK-W1-006.
3. Resolve BLK-W1-009.
4. Resolve BLK-W1-007 and BLK-W1-008.
5. Mitigate BLK-W1-010..012 with execution policy and observability notes.

## Dependency-to-Owner Summary
- BE: state machine fixtures, merchant scope mapping, callback validation support.
- FE: env alignment and guard-stability behavior.
- QA: deterministic dataset governance, retry-window policy, artifact correlation.
- DevOps: secret distribution, sandbox connectivity, isolated test environment management.
