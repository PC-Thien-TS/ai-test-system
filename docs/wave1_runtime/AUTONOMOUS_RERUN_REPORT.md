# AUTONOMOUS_RERUN_REPORT

## Current Release Decision Context

- Decision: `block_release`
- Confidence: `medium`
- Weighted score: `57` / `100`

## Rerun Necessity

- Rerun action: `targeted_rerun`
- Priority: `P1`
- Reason: Targeted rerun needed for uncovered/high-risk areas while keeping current green baseline stable.

## Target Suite Table

| Suite | Priority | Blast Radius | Trigger | Blocked | Blocker Reason |
|---|---|---|---|---|---|
| `tests/rankmate_wave1/test_payment_api.py` | `P1` | `release-critical` | payment realism coverage gap | `True` | unchanged Stripe webhook runtime secret/config blocker |
| `tests/rankmate_wave1/test_search_store_api.py` | `P1` | `release-critical` | product defect STORE-API-004; product defect STO-011 | `False` |  |
| `tests/rankmate_wave1/test_merchant_transition_api.py` | `P2` | `partial-surface` | merchant depth coverage gap | `True` | merchant transition seeds missing |

## Runnable Commands

- `python scripts/build_merchant_state_seeds.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_search_store_api.py`

## Deferred Commands

- `python -m pytest -q -rs tests/rankmate_wave1/test_payment_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py`

## Blockers Preventing Rerun

- Payment realism rerun is blocked until Stripe webhook secret/signing alignment changes.
- Merchant transition depth rerun requires refreshed deterministic merchant state seeds.

## Escalation Recommendation

- Escalate to DevOps/BE to align deployed Stripe webhook secret and signing path for QA runtime.
- Escalate to QA/BE to regenerate merchant state seeds with store-scoped merchant visibility.

## Scenario Validation

| Scenario | Expected | Actual | Expected Targets | Actual Targets |
|---|---|---|---|---|
| `A_current_real_state` | `targeted_rerun` | `targeted_rerun` | tests/rankmate_wave1/test_payment_api.py, tests/rankmate_wave1/test_merchant_transition_api.py | tests/rankmate_wave1/test_payment_api.py, tests/rankmate_wave1/test_merchant_transition_api.py |
| `B_blockers_cleared_score_ge_85` | `no_rerun_needed` | `no_rerun_needed` | none | none |
| `C_auth_or_admin_regression` | `phased_rerun` | `phased_rerun` | tests/rankmate_wave1/test_auth_api.py, tests/rankmate_wave1/test_order_api.py, tests/rankmate_wave1/test_admin_consistency_api.py | tests/rankmate_wave1/test_auth_api.py, tests/rankmate_wave1/test_order_api.py, tests/rankmate_wave1/test_admin_consistency_api.py |

## Next Checkpoint

- After executing runnable commands, regenerate release decision and rerun this planner.

- Ready for self-healing loop v2: `True`
