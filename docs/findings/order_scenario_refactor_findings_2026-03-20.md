# Order Scenario Refactor Findings (2026-03-20)

## Scope
This note captures the shift from historical-seed-heavy execution to scenario-owned journey execution in `scripts/run_api_regression.ps1`.

## What changed
- Added fresh-order orchestration per journey (payment, customer action, merchant) instead of reusing one mutable order.
- Merchant/admin/customer assertions now read from journey-specific order ids.
- Admin list visibility check uses deterministic page scan/filter logic and no longer reports `SEED_BLOCKER` when detail is already readable.
- Reservation past-arrival case (`ORD-API-022`) is now explicitly treated as a backend defect when runtime returns `200`.

## Runtime result after refactor
- `total=166`
- `passed=128`
- `failed=7`
- `skipped=31`

## Proven gains
- Scenario isolation removed cross-branch state pollution in Order flow.
- Payment/cancellation/customer action coverage became executable in the same run with deterministic setup.
- Merchant visibility is now proven (`MORD-API-005`, `MORD-API-008`).
- Admin monitoring and ops checks remain stable and executable.

## Remaining gaps
- Merchant action happy path (`accept=200 -> arrived -> complete`) still needs deterministic lifecycle precondition.
- Notification event correlation is still not deterministic.
- UniqueId seed and second-store seeds are still unresolved.

## Defect list preserved
- `STO-009`
- `STO-011`
- `ORD-API-014`
- `ORD-API-015`
- `ORD-API-022`
- `MEMBER-001`
- `STCATADM-004`

## Recommended next step
Implement one dedicated merchant-happy-branch journey that can produce an `accept=200` order deterministically, then chain `mark-arrived` and `complete` on that dedicated order only.
