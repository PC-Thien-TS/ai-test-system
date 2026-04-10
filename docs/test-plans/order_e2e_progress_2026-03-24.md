# Order E2E Progress (2026-03-24)

## Runtime status
- Host: `http://192.168.1.103:19066`
- Focused rerun:
  - `CORE`: `109/102/7/0`
  - `JOURNEYS`: `33/33/0/0`
  - `EDGE` (diagnostic): `26/1/0/25`
- Current FAIL set remains backend defects only (`7` in CORE).

## Access status
- Customer auth: `PASS` (`tieuphiphi020103+71111@gmail.com`)
- Admin auth: `PASS`
- Merchant auth: `PASS` in this verification round.

## Journey status
- Customer create/detail/history journey: executable and stable.
- Payment intent/retry/verify journey: executable and stable for controlled-status checks.
- Customer action journey: executable with controlled-status assertions.
- Admin monitoring/support journey: executable (`AORD-API-003` remains PASS with paging-aware scan logic).
- Merchant lifecycle endpoints are executable but happy-path transitions are still not proven (`accept/reject/arrived/complete` currently return controlled `400` on selected order state).

## Seed status
- Stable:
  - `storeId=9768`
  - `skuId=14`
  - second same-store sku `15`
- Still missing:
  - deterministic uniqueId seed for `STO-010`
  - deterministic second-store seed for cross-store validation in this host run (`ORD-API-008`, `ORD-API-017` remain seed-blocked in EDGE)
  - deterministic closed/ordering-disabled store seed (`ORD-API-018`)
  - deterministic disabled/out-of-stock sku seed (`ORD-API-019`)

## Contract review item
- `ORD-API-022` remains `CONTRACT_REVIEW`:
  - runtime currently accepts past `arrivalTime` with `200`.

## Next execution targets
1. Prove one merchant happy-path branch (`accept -> arrived -> complete`) using a deliberately prepared paid order state.
2. Add deterministic uniqueId seed for `STO-010` (or keep explicit seed blocker with route-level evidence).
3. Discover deterministic closed/ordering-disabled store and disabled/out-of-stock sku seeds to unlock `ORD-API-018/019`.
