# AI_QA_LEAD_DASHBOARD_REPORT

## Executive Summary

- Adapter: `rankmate` (RankMate / Didaunao)
- Decision: `block_release`
- Score: `57` / `100`
- Confidence: `medium`
- Highest-risk flow: `merchant handling flow`
- Top reason: Weighted score is below release-with-caution threshold (65).
- Generated at (UTC): `2026-04-16T11:15:53.637830+00:00`

## Release Decision Snapshot

- Should release be blocked: `True`
- Should release with caution: `False`

## Current System Health By Phase

| Phase | Health |
|---|---|
| `auth` | `green` |
| `order_core` | `green` |
| `search_store` | `mostly_green_with_regression` |
| `lifecycle` | `usable` |
| `admin_consistency` | `green` |
| `merchant_depth` | `partial_seed_blocked` |
| `payment_realism` | `blocked_by_runtime_config` |

## Top Active Defects

| Family | Severity | Type | Impact | Status | Members |
|---|---|---|---|---|---|
| `DF-MERCHANT-STALE-TERMINAL-MUTATION` | `P1` | `product_defect` | `release-critical` | `active` | MER-API-021 |
| `DF-STORE-NEGATIVE-500` | `P2` | `product_defect` | `release-critical` | `suppressed` | STO-011, STORE-API-004 |
| `DF-STRIPE-WEBHOOK-ENV-BLOCKER` | `blocker/env` | `env_blocker` | `partial-surface` | `blocked` | PAY-API-003, PAY-API-004, PAY-API-007, PAY-API-008, PAY-API-011 |
| `DF-MERCHANT-SEED-COVERAGE-GAP` | `coverage-gap` | `coverage_gap` | `partial-surface` | `blocked` | API_ACCEPTED_ORDER_ID, API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID, API_NO_SHOW_ORDER_ID |

## Environment Blockers vs Product Defects

Environment blockers:
- `DF-STRIPE-WEBHOOK-ENV-BLOCKER`: Stripe webhook realism blocked by runtime secret/signature mismatch

Product defects:
- `DF-MERCHANT-STALE-TERMINAL-MUTATION`: Merchant stale/double complete mutation safety defect (P1)
- `DF-STORE-NEGATIVE-500`: Store invalid lookup negative-path returns 500 (P2)

## Rerun and Healing Operations

- Current rerun action: `targeted_rerun`
- Target suites:
- `tests/rankmate_wave1/test_merchant_transition_api.py`
- `tests/rankmate_wave1/test_payment_api.py`
- `tests/rankmate_wave1/test_search_store_api.py`
- Runnable commands:
- `python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py`
- Blocked reruns:
- `tests/rankmate_wave1/test_payment_api.py`: unchanged Stripe secret/signature env blocker
- `tests/rankmate_wave1/test_search_store_api.py`: known defect family unchanged; rerun deprioritized to avoid duplicate churn
- Healing actions run:
- `HEAL-MERCHANT-SEEDS` (success): `python scripts/build_merchant_state_seeds.py`

## Recommended Next Engineering Actions

- Enforce terminal transition guards for stale/double complete and return controlled 4xx.
- Add a new product-defect penalty in release gate for MER-API-021 family (suggested P1, -15) until fixed.
- Keep STORE-API-004 and STO-011 clustered under one family penalty to avoid duplicate severity inflation.
- Keep Stripe webhook mismatch as env-blocker penalty, not product-defect penalty, until behavior proves otherwise.
- If merchant seed missing-slot count decreases after healing, reduce merchant-depth coverage-gap penalty in next gate run.

## Recommended Next QA Actions

- After backend fix deploy, rerun: python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py
- Defer payment rerun until Stripe secret/signature alignment is confirmed.
- Rerun release gate after merchant rerun and any backend fixes to defect families.

## Release Manager Advisory

- Confirmed P1 merchant active-path defect (MER-API-021). Treat release as high caution; if merchant settlement is release-critical, consider temporary release block.

## Evidence Delta Since Previous Snapshot

- `MER-API-021` (`DF-MERCHANT-STALE-TERMINAL-MUTATION`): suspected_or_unmodeled -> confirmed_backend_defect
- Rerun evidence: terminal status=23; mark_arrived returns 400; complete_order incorrectly returns 200
- Score delta: `72` -> `57` (delta `-15`)
- Decision delta: `release_with_caution` -> `block_release`
- Risk delta: Merchant terminal mutation safety elevated to top active release-critical risk.

## Post-release Watch Items

- Monitor store lookup 5xx rate and invalid-lookup error handling.
- Monitor payment callback anomalies until full webhook realism coverage is stable.
- Keep merchant transition reruns in nightly cycle until seed depth is fully deterministic.