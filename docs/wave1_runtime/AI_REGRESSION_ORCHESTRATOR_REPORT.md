# AI_REGRESSION_ORCHESTRATOR_REPORT

## Requested Regression Intent

- Adapter: `rankmate` (RankMate / Didaunao)
- Intent: `merchant_flow_regression`
- Mode: `balanced`
- Generated at: `2026-04-16T11:15:53.366539+00:00`

## Selected Product Flows

- `Auth Foundation Flow` (`auth_foundation`)
  - Why: Balanced/deep mode adds core anchors.
  - Suites: tests/rankmate_wave1/test_auth_api.py
- `Order Core Flow` (`order_core`)
  - Why: Balanced/deep mode adds core anchors.
  - Suites: tests/rankmate_wave1/test_order_api.py, tests/rankmate_wave1/test_order_lifecycle_flow_api.py
- `Merchant Handling Flow` (`merchant_handling`)
  - Why: Top active risk included: merchant handling flow.
  - Suites: tests/rankmate_wave1/test_merchant_transition_api.py
- `Admin Consistency Flow` (`admin_consistency`)
  - Why: Balanced/deep mode adds core anchors.
  - Suites: tests/rankmate_wave1/test_admin_consistency_api.py

## Selected Suites And Why

- `tests/rankmate_wave1/test_auth_api.py` (Auth Foundation Flow)
- `tests/rankmate_wave1/test_order_api.py` (Order Core Flow)
- `tests/rankmate_wave1/test_order_lifecycle_flow_api.py` (Order Core Flow)
- `tests/rankmate_wave1/test_merchant_transition_api.py` (Merchant Handling Flow)
- `tests/rankmate_wave1/test_admin_consistency_api.py` (Admin Consistency Flow)

## Suppressed Suites And Why

- none

## Blocked Suites And Why

- `tests/rankmate_wave1/test_merchant_transition_api.py`: Partial seed blocker: API_ACCEPTED_ORDER_ID, API_NO_SHOW_ORDER_ID, API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID

## Runnable Commands

- `python -m pytest -q -rs tests/rankmate_wave1/test_auth_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_order_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_order_lifecycle_flow_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_admin_consistency_api.py`

## Expected Release Confidence Impact

- Merchant workflow confidence refresh with core context anchors.

## Known Unresolved Risks After This Regression

- Included in this pack:
  - DF-MERCHANT-STALE-TERMINAL-MUTATION: Merchant stale/double complete mutation safety defect
  - DF-MERCHANT-SEED-COVERAGE-GAP: Merchant transition seed coverage gaps
- Deferred from this pack:
  - DF-STORE-NEGATIVE-500: Store invalid lookup negative-path returns 500
  - DF-STRIPE-WEBHOOK-ENV-BLOCKER: Stripe webhook realism blocked by runtime secret/signature mismatch

## Recommended Next Action After Run

- Execute planned suites, then rerun release gate and dashboard refresh.
