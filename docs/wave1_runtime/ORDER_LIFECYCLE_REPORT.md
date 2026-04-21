# ORDER_LIFECYCLE_REPORT

- Generated at: `2026-04-20T06:49:16.500166+00:00`
- Main order id: `817`
- Store id: `9768`
- Initial status: `pending`
- Final status: `cancelled`
- User visible: `True`
- Merchant visible: `True`
- Admin visible: `False`

## Captured IDs

- `payment_attempt_id`: `213`
- `payment_transaction_id`: `None`

## Branch Outcomes

| Branch | Order ID | Status | Note |
|---|---:|---:|---|
| `cancel` | `818` | `10` | create -> cancel branch verified by user detail |
| `merchant_visibility` | `817` | `200` | Merchant list/detail visibility confirmed. |
| `no_show` | `` | `` | Missing API_NO_SHOW_ORDER_ID seed. |
| `payment` | `817` | `200` | Payment init+verify contract completed without webhook mutation. |
| `stale_terminal` | `761` | `60` | Repeated terminal action returned controlled status and did not crash. |

## Notes

- Golden path created order 817 for store 9768 and verified user detail/history.
