# Regression Layering Findings (2026-03-23)

## Layer status snapshot
- Full run: `166/65/7/94`
- `CORE`: `109/64/7/38`
- `JOURNEYS`: `33/1/0/32`
- `EDGE`: use full-run outcome (edge-heavy cases remain mostly skipped by design).

## What changed today
- `AORD-API-003` admin visibility logic now performs bounded multi-page scanning to avoid false skip on older order ids.
- `JOURNEYS` remains at `0 FAIL` in the current run window.

## Why targets are still missed
- Customer and merchant credentials are rejected by runtime login (`400 Incorrect email or password`).
- This inflates blocker-driven skips across `CORE` and `JOURNEYS`.
- Merchant E2E lifecycle cannot be proven without a valid merchant token.

## Defect visibility check
- Known backend defects remained `FAIL` and visible:
  - `STO-009`, `STO-011`, `STO-012`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`.

## Next rerun gate
1. Recover valid customer and merchant credentials.
2. Re-run `JOURNEYS` immediately.
3. Confirm merchant chain (`accept -> arrived -> complete`) on dedicated order.
