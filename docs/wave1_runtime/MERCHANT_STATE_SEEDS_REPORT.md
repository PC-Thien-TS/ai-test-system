# MERCHANT_STATE_SEEDS_REPORT

- Generated at: `2026-04-15T09:30:30.880000+00:00`
- Base URL: `http://192.168.1.103:19066`
- Merchant store id: `None`

Deterministic selection rule:
- Discovery-first from merchant list/detail.
- Choose newest candidate (`highest order id`) per slot.
- For transition-driving slots, prefer distinct order ids to reduce cross-test mutation contamination.

## Seed Slots

| Seed Slot | Order ID | Status | Status Name | Source | Note |
|---|---:|---:|---|---|---|
| `API_PAID_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_REJECTABLE_PAID_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_ACCEPTED_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_ARRIVED_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_MERCHANT_CANCELLABLE_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_NO_SHOW_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_PENDING_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_CANCELLED_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_COMPLETED_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_NON_PAID_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_STALE_TRANSITION_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_CONSISTENCY_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |

## Copy-ready .env lines

```env
# API_PAID_ORDER_ID=  # MISSING (no candidate discovered)
# API_REJECTABLE_PAID_ORDER_ID=  # MISSING (no candidate discovered)
# API_ACCEPTED_ORDER_ID=  # MISSING (no candidate discovered)
# API_ARRIVED_ORDER_ID=  # MISSING (no candidate discovered)
# API_MERCHANT_CANCELLABLE_ORDER_ID=  # MISSING (no candidate discovered)
# API_NO_SHOW_ORDER_ID=  # MISSING (no candidate discovered)
# API_PENDING_ORDER_ID=  # MISSING (no candidate discovered)
# API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID=  # MISSING (no candidate discovered)
# API_CANCELLED_ORDER_ID=  # MISSING (no candidate discovered)
# API_COMPLETED_ORDER_ID=  # MISSING (no candidate discovered)
# API_NON_PAID_ORDER_ID=  # MISSING (no candidate discovered)
# API_STALE_TRANSITION_ORDER_ID=  # MISSING (no candidate discovered)
# API_CONSISTENCY_ORDER_ID=  # MISSING (no candidate discovered)
```

## Diagnostics

- customer_login=customer login request failed: HTTPConnectionPool(host='192.168.1.103', port=19066): Max retries exceeded with url: /api/v1/auth/login (Caused by ConnectTimeoutError(<HTTPConnection(host='192.168.1.103', port=19066) at 0x1ede447ed50>, 'Connection to 192.168.1.103 timed out. (connect timeout=30.0)'))
- merchant_login=merchant login request failed: HTTPConnectionPool(host='192.168.1.103', port=19066): Max retries exceeded with url: /api/v1/auth/login (Caused by ConnectTimeoutError(<HTTPConnection(host='192.168.1.103', port=19066) at 0x1ede4df1fa0>, 'Connection to 192.168.1.103 timed out. (connect timeout=30.0)'))
- merchant_store_context=skipped (merchant login unavailable)
- merchant_discovery=blocked (store-scoped merchant token unavailable)

## Mutations performed

- none (discovery only)
