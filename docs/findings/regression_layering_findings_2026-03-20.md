# Regression Layering Findings (2026-03-20)

## Change summary
- Added execution-layer support in `run_api_regression.ps1`:
  - `-Mode CORE`
  - `-Mode JOURNEYS`
  - `-Mode EDGE`
  - default `ALL`
- Added wrapper scripts:
  - `scripts/run_api_regression_core.ps1/.cmd`
  - `scripts/run_api_regression_journeys.ps1/.cmd`
  - `scripts/run_api_regression_edge.ps1/.cmd`
- Preserved artifact output paths and result schema compatibility.

## Key behavior
- Case selection now routes by testcase id to one layer.
- Known backend defects remain detectable and are not downgraded.
- `layer` is now included on each result row for traceability.

## Layer run evidence
- `CORE`: `total=109`, `passed=102`, `failed=6`, `skipped=1`
- `JOURNEYS`: `total=33`, `passed=26`, `failed=1`, `skipped=6`
- `EDGE`: `total=26`, `passed=1`, `failed=0`, `skipped=25`
- `ALL`: `total=166`, `passed=128`, `failed=7`, `skipped=31`

Evidence source:
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.log`

## Defect visibility status
Still preserved as `FAIL` in latest baseline:
- `STO-009`
- `STO-011`
- `ORD-API-014`
- `ORD-API-015`
- `MEMBER-001`
- `STCATADM-004`

`ORD-API-022` is isolated in `JOURNEYS` and remains `FAIL` because past `arrivalTime` is accepted (`200`) instead of controlled reject.

## Additional improvement in this cycle
- Fixed journey-layer dependency on CORE-only response variables for:
  - `MORD-API-005`
  - `MORD-API-008`
  - `AORD-API-003`
- JOURNEYS now probes merchant/admin list endpoints directly when bootstrap responses are unavailable in the selected layer.

## Risk notes
- Some direct scenario orchestration code paths still execute setup calls even when their case id is excluded from selected layer. This does not change reported outcomes, but can add runtime noise.
- Follow-up hardening should migrate those paths behind explicit per-case/layer guards.
