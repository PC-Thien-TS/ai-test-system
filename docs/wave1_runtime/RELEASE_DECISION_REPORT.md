# RELEASE_DECISION_REPORT

## Executive Decision

- Adapter: `rankmate` (RankMate / Didaunao)
- Decision: `block_release`
- Confidence: `medium`
- Generated at: `2026-04-16T11:15:53.513910+00:00`
- Summary: Release is near/under block threshold due to confirmed merchant terminal mutation risk and open defects.

## Weighted Score Summary

- Weighted score: `57` / `100`

## Phase Contribution Table

| Phase | Score Contribution |
|---|---:|
| `auth` | `25` |
| `order_core` | `25` |
| `search_store` | `12` |
| `lifecycle` | `15` |
| `admin_consistency` | `20` |
| `merchant_depth` | `-4` |
| `payment_realism` | `-8` |

## Product Defect Penalties

| ID | Severity | Penalty | Note |
|---|---|---:|---|
| `STORE-API-004` | `P2` | `-8` | Invalid store lookup returns 500 instead of controlled 400/404 |
| `STO-011` | `P2` | `0` | Invalid store uniqueId lookup returns 500 instead of controlled 400/404 |
| `DF-MERCHANT-STALE-TERMINAL-MUTATION` | `P1` | `-15` | Merchant stale/double complete mutation safety defect |

## Environment Blocker Penalties

| ID | Severity | Penalty | Note |
|---|---|---:|---|
| `BLK-W1-003` | `medium` | `-5` | Stripe webhook secret/signing alignment blocked in runtime |

## Coverage Gap Penalties

| ID | Severity | Penalty | Note |
|---|---|---:|---|
| `GAP-MERCHANT-DEPTH` | `medium` | `0` | Merchant transition depth partially seed-blocked (3 slots missing) |
| `GAP-PAYMENT-REALISM` | `medium` | `0` | Payment webhook realism coverage is incomplete |

## Evidence Gap Penalties

| ID | Severity | Penalty | Note |
|---|---|---:|---|
| `none` | `` | `0` | No penalties |

## Confidence Rationale

- Weighted score is below release-with-caution threshold (65).
- Known product defects remain open and are explicitly penalized.
- Environment blockers are separated from product defects and penalized moderately.
- Coverage depth remains incomplete for merchant/payment realism paths.
- Confirmed P1 merchant terminal mutation defect is now included from rerun cluster evidence.

## Scenario Drift Validation

| Scenario | Expected | Actual | Score | Confidence | Match |
|---|---|---|---:|---|---|
| `A_current_real_repo_evidence` | `block_release` | `block_release` | `57` | `medium` | `True` |
| `B_improved_future_state` | `release` | `release` | `100` | `high` | `True` |
| `C_regressed_auth_or_admin` | `block_release` | `block_release` | `32` | `low` | `True` |

## Evidence Delta Since Previous Snapshot

- `MER-API-021` (`DF-MERCHANT-STALE-TERMINAL-MUTATION`): suspected_or_unmodeled -> confirmed_backend_defect
- Rerun evidence: terminal status=23; mark_arrived returns 400; complete_order incorrectly returns 200
- Score delta: `72` -> `57` (delta `-15`)
- Decision delta: `release_with_caution` -> `block_release`
- Risk delta: Merchant terminal mutation safety elevated to top active release-critical risk.

## Recommended Next Actions

- Before release: Fix stale/double complete guard in merchant complete endpoint so terminal orders reject repeat complete with controlled 4xx.
- Before release: Fix STORE-API-004 negative-path regression so invalid store lookups return controlled 400/404.
- Before release: Align deployed Stripe webhook secret/signing path with QA runtime to unblock payment realism checks.
- Before release: Unlock merchant state seeds for transition-depth and terminal-state verification.
- Before release: If merchant settlement is release-critical in this release train, consider temporary release block until MER-API-021 is fixed.
- After release: Monitor store lookup 5xx rate and invalid-lookup error handling.
- After release: Monitor payment callback anomalies until full webhook realism coverage is stable.
- After release: Keep merchant transition reruns in nightly cycle until seed depth is fully deterministic.

## Evidence Sources

- C:\Projects\Rankmate\ai_test_system\docs\wave1_runtime\ORDER_LIFECYCLE_REPORT.md
- C:\Projects\Rankmate\ai_test_system\docs\wave1_runtime\ADMIN_CONSISTENCY_REPORT.md
- C:\Projects\Rankmate\ai_test_system\docs\wave1_runtime\MERCHANT_STATE_SEEDS_REPORT.md
- C:\Projects\Rankmate\ai_test_system\order_lifecycle_seed.json
- C:\Projects\Rankmate\ai_test_system\merchant_state_seeds.json
- C:\Projects\Rankmate\ai_test_system\merchant_state_seeds.env
- C:\Projects\Rankmate\ai_test_system\defect_cluster_report.json
- C:\Projects\Rankmate\ai_test_system\docs\wave1_execution\RANKMATE_WAVE1_BLOCKERS_AND_DEPENDENCIES.md
- C:\Projects\Rankmate\ai_test_system\docs\wave1_runtime\RANKMATE_WAVE1_RUNTIME_ENV_CONTRACT.md
- C:\Projects\Rankmate\ai_test_system\tests\rankmate_wave1\test_search_store_api.py
- C:\Projects\Rankmate\ai_test_system\artifacts\test-results\api-regression\README.md
