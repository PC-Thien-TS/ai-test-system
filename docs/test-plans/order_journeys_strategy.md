# Order Journeys Strategy

## Objective
Run realistic Order automation with isolated scenario ownership per journey, matching manual-proven runtime behavior.

## Isolation rules
- Each journey creates and owns its own order(s) when feasible.
- Do not reuse a cancelled order for merchant happy-path transitions.
- Build preconditions by behavior first (create -> pay -> action), then fallback to deterministic seeds only when orchestration is infeasible.

## Implemented journey anchors
- `J2-Payment`: fresh order for payment intent/retry/verify.
- `J3-CustomerAction`: fresh order for customer cancel/confirm/report flows.
- `J5-Merchant`: fresh order for merchant visibility/actions.
- `J7-Admin`: admin list/detail checks consume scenario-created order ids.

## Journey set in current runner
1. Create order journey (`ORD-API-001`, `ORD-API-004`, `ORD-API-009`, `ORD-API-020`)
2. Payment intent journey (`ORD-PAY-001`, `003`, `004`, `007`, `008`)
3. Customer cancel/actions journey (`ORD-CUS-*`, `ORD-CAN-001..003`)
4. Merchant visibility and action journey (`MORD-API-*`)
5. Admin monitoring journey (`AORD-API-003`, `AORD-API-004`)
6. Reservation/preorder journey (`ORD-API-021`, `022`, `023`, `028`)
7. Add-on guard journey (`ORD-ADDON-001`, `ORD-ADDON-002`)

## Current known journey blockers
- Merchant deeper transitions (`mark-arrived`, `complete`, `cancel`, `no-show`) still require deterministic `accept=200` branch.
- Notification lifecycle correlation remains nondeterministic.
- Some state-heavy checks still depend on fallback seeds.
- 2026-03-23 runtime window adds auth blockers:
  - customer login failed (`400 Incorrect email or password`)
  - merchant login failed (`400 Incorrect email or password`)

## Latest journey run snapshot
- 2026-03-20 stable window:
  - `total=33`
  - `passed=26`
  - `failed=1`
  - `skipped=6`
- 2026-03-23 auth/access drift window:
  - `total=33`
  - `passed=1`
  - `failed=0`
  - `skipped=32`

## Investigation item
- `ORD-API-022` (past `arrivalTime`) currently returns `200`.
- Current runner classification is `CONTRACT_REVIEW` when executable.
- In 2026-03-23 run it was skipped due missing customer auth token.
