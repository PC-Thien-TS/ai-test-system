# MERCHANT_STATE_SEEDS_REPORT

- Generated at: `2026-04-16T04:52:36.828544+00:00`
- Base URL: `http://tldraft.hopto.org:19066`
- Merchant store id: `9768`

Deterministic selection rule:
- Discovery-first from merchant list/detail.
- Choose newest candidate (`highest order id`) per slot.
- For transition-driving slots, prefer distinct order ids to reduce cross-test mutation contamination.

## Seed Slots

| Seed Slot | Order ID | Status | Status Name | Source | Note |
|---|---:|---:|---|---|---|
| `API_PAID_ORDER_ID` | `768` | `20` | `Paid` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_REJECTABLE_PAID_ORDER_ID` | `701` | `20` | `Paid` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_ACCEPTED_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_ARRIVED_ORDER_ID` | `127` | `22` | `Arrived` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_MERCHANT_CANCELLABLE_ORDER_ID` | `767` | `10` | `Pending` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_NO_SHOW_ORDER_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_PENDING_ORDER_ID` | `767` | `10` | `Pending` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID` | `` | `` | `` | `missing` | no candidate discovered |
| `API_CANCELLED_ORDER_ID` | `761` | `60` | `Cancelled` | `env_existing` | kept existing env value |
| `API_COMPLETED_ORDER_ID` | `762` | `23` | `Completed` | `env_existing` | kept existing env value |
| `API_NON_PAID_ORDER_ID` | `767` | `10` | `Pending` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_STALE_TRANSITION_ORDER_ID` | `762` | `23` | `Completed` | `discovered` | selected newest order id by deterministic rule (descending id) |
| `API_CONSISTENCY_ORDER_ID` | `768` | `20` | `Paid` | `discovered` | selected newest order id by deterministic rule (descending id) |

## Copy-ready .env lines

```env
API_PAID_ORDER_ID=768
API_REJECTABLE_PAID_ORDER_ID=701
# API_ACCEPTED_ORDER_ID=  # MISSING (no candidate discovered)
API_ARRIVED_ORDER_ID=127
API_MERCHANT_CANCELLABLE_ORDER_ID=767
# API_NO_SHOW_ORDER_ID=  # MISSING (no candidate discovered)
API_PENDING_ORDER_ID=767
# API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID=  # MISSING (no candidate discovered)
API_CANCELLED_ORDER_ID=761
API_COMPLETED_ORDER_ID=762
API_NON_PAID_ORDER_ID=767
API_STALE_TRANSITION_ORDER_ID=762
API_CONSISTENCY_ORDER_ID=768
```

## Diagnostics

- customer_login=ok
- merchant_login=ok
- merchant_store_context=ok

## Mutations performed

- none (discovery only)
