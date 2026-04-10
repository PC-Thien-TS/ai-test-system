# API Regression Layers: CORE / JOURNEYS / EDGE

## Why split
The previous single run mixed stable contract checks, realistic lifecycle journeys, and hard runtime-dependent edge checks. The split provides a clearer release signal.

## Layer definitions
- `CORE`
  - Primary release-confidence run.
  - Stable contract checks and high-confidence module coverage.
  - Keeps known backend defects visible as `FAIL` (`STO-009`, `STO-011`, `ORD-API-014`, `ORD-API-015`, `MEMBER-001`, `STCATADM-004`).
- `JOURNEYS`
  - Manual-proven business-flow style checks with scenario-owned orders.
  - Focuses on create/pay/customer-action/merchant/admin lifecycle behavior.
- `EDGE`
  - Nondeterministic or setup-heavy checks.
  - Preserves deep coverage with explicit blocker classifications.

## Execution model in runner
- Runner now accepts `-Mode CORE|JOURNEYS|EDGE|ALL`.
- Case-to-layer routing is done by testcase id.
- Result schema is unchanged, with an added `layer` field in each result item.
- Artifact paths remain unchanged:
  - `artifacts/test-results/api-regression/api_regression.log`
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.failed.json`

## Layer assignment rules
- `EDGE` explicit ids:
  - `ORD-001`, `ORD-003`, `STO-010`, `NEWS-003`, `ORD-API-008`, `ORD-API-017`, `ORD-API-018`, `ORD-API-019`, `AORD-API-007`, `AORD-API-008`, `ORD-CAN-004`
  - all `NOTI-ORD-*`, `ORD-JOB-*`, `ORD-CAVEAT-*`
- `JOURNEYS` explicit ids:
  - `ORD-API-001`, `004`, `009`, `020`, `021`, `022`, `023`, `028`
  - `ORD-PAY-001`, `003`, `004`, `007`, `008`
  - `ORD-CUS-001..004`
  - `ORD-CAN-001..003`
  - `MORD-API-001..008`
  - `AORD-API-003`, `AORD-API-004`
  - `ORD-ADDON-001`, `ORD-ADDON-002`
- All other cases default to `CORE`.

## Commands
```powershell
.\scripts\run_api_regression_core.ps1
.\scripts\run_api_regression_journeys.ps1
.\scripts\run_api_regression_edge.ps1
```

```cmd
scripts\run_api_regression_core.cmd
scripts\run_api_regression_journeys.cmd
scripts\run_api_regression_edge.cmd
```

## Pass-full interpretation
- "Pass full CORE" means the `CORE` layer passes except currently known backend defects.
- `JOURNEYS` and `EDGE` are tracked separately to avoid polluting release-confidence status while still preserving coverage and defect visibility.

## Latest layer snapshots (2026-03-20)
- `CORE`: `109/102/6/1` (total/passed/failed/skipped)
- `JOURNEYS`: `33/26/1/6`
- `EDGE`: `26/1/0/25`
- `ALL`: `166/128/7/31`

## Latest layer snapshots (2026-03-23, auth/access drift window)
- `CORE`: `109/64/7/38`
- `JOURNEYS`: `33/1/0/32`
- `EDGE`: use `ALL` run evidence; independent edge-only rerun was blocked by host instability after the main run window.
- `ALL`: `166/65/7/94`

Notes:
- `JOURNEYS` still has `0 FAIL`, but skip inflation is caused by customer/merchant auth failures (`400 Incorrect email or password`).
- Admin login and admin scopes remain executable.
