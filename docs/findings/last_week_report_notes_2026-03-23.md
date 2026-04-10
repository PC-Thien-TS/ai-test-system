# Last-Week Report Notes (Prepared 2026-03-23)

## Progress summary
- Order-first automation remains structurally improved:
  - layered runs (`CORE`, `JOURNEYS`, `EDGE`)
  - journey-owned order orchestration
  - explicit blocker classification (`CONFIG_BLOCKER`, `SCOPE_BLOCKER`, `SEED_BLOCKER`, `RUNTIME_CONTRACT_CONFIG_BLOCKER`)
- Known backend defects remained visible and were not masked.

## Regression delta observed
- Last stable high-signal window had customer/merchant auth and broader pass rates.
- Current 2026-03-23 window regressed in auth access:
  - customer login blocked
  - merchant login blocked
  - admin login still valid
- Result: high skip inflation in customer/merchant-dependent cases.

## Actionable risks
1. Credential drift can invalidate release-confidence signals for `JOURNEYS`.
2. Merchant happy-path verification cannot be treated as complete until merchant auth is restored.
3. Runtime host stability affects reproducibility of same-day evidence.

## Carryover actions
- Reconfirm credential set with backend owner.
- Re-run seed precheck + journeys first, then full regression.
- Close merchant lifecycle branch on real merchant-visible order sequence.
