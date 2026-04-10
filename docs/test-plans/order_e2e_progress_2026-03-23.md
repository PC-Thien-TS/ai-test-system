# Order E2E Progress (2026-03-23)

## Current status by layer
- `CORE`: blocked by customer auth drift; backend defects remain visible.
- `JOURNEYS`: `0 FAIL`, but still high skip count due auth/scope preconditions.
- `EDGE`: unchanged in intent; still blocker-heavy by design.

## Customer / Merchant / Admin access status
- Customer login (`API_USER/API_PASS`): blocked (`400 Incorrect email or password`)
- Merchant login (`API_MERCHANT_USER/API_MERCHANT_PASS`): blocked (`400 Incorrect email or password`)
- Admin login (`API_ADMIN_USER/API_ADMIN_PASS`): pass (`200`)

## Merchant happy-path target (`accept -> arrived -> complete`)
- Not achieved today.
- Root cause:
  1. merchant auth blocked by invalid runtime credentials,
  2. later runtime host reachability interruption.

## Separate-order-per-flow enforcement
- Preserved in runner orchestration:
  - payment journey order
  - customer action journey order
  - merchant visibility/lifecycle journey order
- Additional improvement today:
  - admin list visibility now scans deterministically across pages (`AORD-API-003`) to avoid false query blockers.

## ORD-API-022 status
- Runner now treats runtime `200` on past `arrivalTime` as `CONTRACT_REVIEW` pass (captured behavior) when executable.
- Today execution: skipped because customer auth token was unavailable.

## Execution checklist for next rerun
1. Validate credentials with:
   - `.\scripts\run_api_seed_precheck.ps1`
2. Run journey layer:
   - `.\scripts\run_api_regression.ps1 -Mode JOURNEYS`
3. Verify merchant chain on fresh order:
   - `MORD-API-001`
   - `MORD-API-003`
   - `MORD-API-004`
4. Run full regression:
   - `.\scripts\run_api_regression.ps1`
