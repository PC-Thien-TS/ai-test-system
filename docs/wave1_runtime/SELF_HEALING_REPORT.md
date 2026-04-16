# SELF_HEALING_REPORT

## Current Context

- Release decision: `release_with_caution`
- Release confidence: `medium`
- Release score: `72` / `100`
- Updated rerun action: `targeted_rerun`

## Healing Actions Attempted

- `HEAL-MERCHANT-SEEDS`: `success` | command=`python scripts/build_merchant_state_seeds.py` | note=missing slots before run: API_ACCEPTED_ORDER_ID, API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID, API_NO_SHOW_ORDER_ID

## Healing Actions Skipped

- `HEAL-LIFECYCLE-SEED`: Lifecycle seed exists and is not stale.

## Updated Rerun Recommendations

| Suite | Priority | Blocked | Reason |
|---|---|---|---|
| `tests/rankmate_wave1/test_merchant_transition_api.py` | `P1` | `False` | merchant depth coverage gap; post-healing merchant seeds available |
| `tests/rankmate_wave1/test_payment_api.py` | `P1` | `True` | unchanged Stripe secret/signature env blocker |
| `tests/rankmate_wave1/test_search_store_api.py` | `P3` | `True` | known defect family unchanged; rerun deprioritized to avoid duplicate churn |

## Defect Families

| Family ID | Type | Severity Suggestion | Release Impact | Members |
|---|---|---|---|---|
| `DF-STORE-NEGATIVE-500` | `product_defect` | `P2` | `release-critical` | STO-011, STORE-API-004 |
| `DF-MERCHANT-STALE-TERMINAL-MUTATION` | `product_defect` | `P1` | `release-critical` | MER-API-021 |
| `DF-STRIPE-WEBHOOK-ENV-BLOCKER` | `env_blocker` | `blocker/env` | `partial-surface` | PAY-API-003, PAY-API-004, PAY-API-007, PAY-API-008, PAY-API-011 |
| `DF-MERCHANT-SEED-COVERAGE-GAP` | `coverage_gap` | `coverage-gap` | `partial-surface` | API_ACCEPTED_ORDER_ID, API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID, API_NO_SHOW_ORDER_ID |

## Severity Suggestions

- `DF-STORE-NEGATIVE-500` -> `P2` (confidence `high`): Isolated defect in negative-path handling with limited blast radius.
- `DF-MERCHANT-STALE-TERMINAL-MUTATION` -> `P1` (confidence `medium`): Active-path state-machine defect with potential workflow integrity risk.
- `DF-STRIPE-WEBHOOK-ENV-BLOCKER` -> `blocker/env` (confidence `high`): Runtime/config blocker, not currently classified as product defect.
- `DF-MERCHANT-SEED-COVERAGE-GAP` -> `coverage-gap` (confidence `medium`): Coverage/data gap impacting depth but not core pass signal.

## Release Gate Adjustment Recommendations

- Add a new product-defect penalty in release gate for MER-API-021 family (suggested P1, -15) until fixed.
- Keep STORE-API-004 and STO-011 clustered under one family penalty to avoid duplicate severity inflation.
- Keep Stripe webhook mismatch as env-blocker penalty, not product-defect penalty, until behavior proves otherwise.
- If merchant seed missing-slot count decreases after healing, reduce merchant-depth coverage-gap penalty in next gate run.

## Scenario Validation

| Scenario | Expected | Actual | Match |
|---|---|---|---|
| `A_merchant_seeds_missing_initially` | run seed builder and make merchant rerun more actionable | implemented (seed healing action executes when missing slots are detected) | `True` |
| `B_unchanged_stripe_env_blocker` | suppress/defer pointless rerun | implemented (payment rerun deferred while blocker remains unchanged) | `True` |
| `C_repeated_store_failures_clustered` | single defect family without duplicate severity inflation | implemented | `True` |
| `D_merchant_stale_terminal_defect` | classify as product defect with P1/P0-light suggestion | implemented (P1 suggestion) | `True` |

## Recommended Next Engineering Actions

- Align deployed Stripe webhook secret/signing path, then rerun tests/rankmate_wave1/test_payment_api.py.
- Open backend bug ticket for MER-API-021 stale/double complete guard and verify controlled 4xx response.
- Track STORE-API-004/STO-011 as one defect family and rerun Search+Store only after backend patch.