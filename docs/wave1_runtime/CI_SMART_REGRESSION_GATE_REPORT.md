# CI_SMART_REGRESSION_GATE_REPORT

## Active Adapter

- Adapter: `rankmate`

## Adapter Validation

- Status: `pass_with_warnings`
- Warnings: `1`
- Errors: `0`

## Changed Files Analyzed

- `merchant/order_transition_service.cs`
- `merchant/dashboard_complete_order.ts`

## Selected Regression Intent

- Intent: `merchant_flow_regression`
- Mode: `balanced`

## Regression Plan Summary

- Plan status: `generated`
- Selected suites: `5`
- Suppressed suites: `0`
- Blocked suites: `1`

## Execution

- Execution status: `not_executed`
- Execute requested: `False`

## Updated Release Decision

- Decision: `block_release`
- Score: `57`
- Confidence: `medium`

## Final CI Gate Status

- CI gate status: `fail`
- Summary: Gate detected blocking risk (adapter/step failure or block_release decision).

## Recommended Next Actions

- Address adapter validation warnings before production onboarding.
- Fix stale/double complete guard in merchant complete endpoint so terminal orders reject repeat complete with controlled 4xx.
- Fix STORE-API-004 negative-path regression so invalid store lookups return controlled 400/404.
- Align deployed Stripe webhook secret/signing path with QA runtime to unblock payment realism checks.
- Run selected regression commands to convert planning signal into execution signal.

## Recommended Commands

- `python -m pytest -q -rs tests/rankmate_wave1/test_auth_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_order_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_order_lifecycle_flow_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_admin_consistency_api.py`
