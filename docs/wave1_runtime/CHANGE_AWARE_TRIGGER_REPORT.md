# CHANGE_AWARE_TRIGGER_REPORT

- Adapter: `rankmate` (RankMate / Didaunao)
- Generated at: `2026-04-16T11:15:53.140646+00:00`

## Changed Files

- `merchant/order_transition_service.cs`
- `merchant/dashboard_complete_order.ts`

## Selected Flows

- `order_core` (Order Core Flow)
  - Matched files: merchant/order_transition_service.cs, merchant/dashboard_complete_order.ts
- `merchant_handling` (Merchant Handling Flow)
  - Matched files: merchant/order_transition_service.cs, merchant/dashboard_complete_order.ts

## Runnable Commands

- `python -m pytest -q -rs tests/rankmate_wave1/test_order_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_order_lifecycle_flow_api.py`
- `python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py`
