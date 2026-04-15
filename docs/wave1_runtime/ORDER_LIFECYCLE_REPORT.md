# ORDER_LIFECYCLE_REPORT

- Generated at: `2026-04-15T10:49:53.923386+00:00`
- Main order id: `760`
- Store id: `9768`
- Initial status: `pending`
- Final status: `pending`
- User visible: `True`
- Merchant visible: `True`
- Admin visible: `False`

## Captured IDs

- `payment_attempt_id`: `192`
- `payment_transaction_id`: `None`

## Branch Outcomes

| Branch | Order ID | Status | Note |
|---|---:|---:|---|
| `cancel` | `761` | `10` | create -> cancel branch verified by user detail |
| `merchant_visibility` | `760` | `200` | Merchant list/detail visibility confirmed. |
| `no_show` | `` | `` | Missing API_NO_SHOW_ORDER_ID seed. |
| `payment` | `760` | `200` | Payment init+verify contract completed without webhook mutation. |

## Notes

- Golden path created order 760 for store 9768 and verified user detail/history.
