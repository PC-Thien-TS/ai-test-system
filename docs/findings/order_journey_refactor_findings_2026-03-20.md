# Order Journey Refactor Findings (2026-03-20)

## Scope
Focused on separating journey execution from stable core checks and edge blockers.

## What is improved
- Journey order ownership is explicit for payment/customer-action/merchant paths.
- Core release-confidence signal can now be run separately from edge-heavy blockers.
- Journey and edge outcomes are now easier to audit without hiding backend failures.

## Current journey status
- Proven executable:
  - create/detail/history
  - payment intent/retry/verify
  - customer action endpoints
  - merchant detail and partial lifecycle probes
  - admin list/detail monitoring
- Still partial:
  - merchant accept/reject/arrived/complete/no-show full happy chain
  - notification lifecycle correlation
  - timeline/event-code deterministic checks

## Journey run summary
- `total=33`
- `passed=26`
- `failed=1`
- `skipped=6`
- Current journey-layer fail:
  - `ORD-API-022` (past `arrivalTime` accepted with `200`)

## Classification position
- Keep true backend defects as `FAIL`.
- Keep nondeterministic scenarios as explicit `SEED_BLOCKER`, `SCOPE_BLOCKER`, or `RUNTIME_CONTRACT_CONFIG_BLOCKER`.
- Do not convert unresolved behavior into pass-through status.
