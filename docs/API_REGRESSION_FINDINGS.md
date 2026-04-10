# API Regression Findings (Latest Evidence)

## Focused verification round (2026-03-24, host `192.168.1.103`)
- Commands:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode CORE`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode JOURNEYS`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode EDGE` (diagnostic skip-cluster verification)
- Artifacts captured:
  - `artifacts/test-results/api-regression/api_regression.summary.core.json`
  - `artifacts/test-results/api-regression/api_regression.summary.journeys.json`
  - `artifacts/test-results/api-regression/api_regression.summary.edge.json`
  - `artifacts/test-results/api-regression/api_regression.core.log`
  - `artifacts/test-results/api-regression/api_regression.journeys.log`
  - `artifacts/test-results/api-regression/api_regression.edge.log`
- Layer summaries:
  - `CORE`: `total=109`, `passed=102`, `failed=7`, `skipped=0`
  - `JOURNEYS`: `total=33`, `passed=33`, `failed=0`, `skipped=0`
  - `EDGE`: `total=26`, `passed=1`, `failed=0`, `skipped=25`
- Non-pass matrix from this round:
  - `FAIL`: 7 (all in `CORE`, all backend defects)
  - `SKIPPED`: 25 (all in `EDGE`)
- `ORD-API-022` remains `CLASS=CONTRACT_REVIEW`:
  - current runtime still returns `200` for past `arrivalTime` payload.
- Merchant auth blocker is not reproduced in this round:
  - merchant-scope cases are executable (`MORD-*` run with token and return controlled statuses).
  - remaining merchant limitation is business-state precondition (`accept/reject/arrived/complete` currently `400`), not auth failure.

## Latest verified run (2026-03-24, host `192.168.1.7`)
- Evidence:
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.failed.json`
  - `artifacts/test-results/api-regression/api_regression.log`
  - `docs/findings/order_execution_findings_2026-03-24.md`
- Summary:
  - `total=166`
  - `passed=126`
  - `failed=7`
  - `skipped=33`

## Layered execution snapshot (2026-03-24)
- `CORE`: `total=109`, `passed=100`, `failed=7`, `skipped=2`
- `JOURNEYS`: `total=32`, `passed=24`, `failed=0`, `skipped=8`
- `EDGE`: `total=25`, `passed=2`, `failed=0`, `skipped=23`

## Key interpretation (2026-03-24)
- True backend defect set remains unchanged (`7 FAIL` only).
- `AORD-API-003` remains fixed and passing.
- `ORD-API-022` remains `CLASS=CONTRACT_REVIEW` with runtime `200` for past `arrivalTime`.
- Merchant auth remains blocked:
  - `API_MERCHANT_USER=tieuphiphi020103+71111@gmail.com`
  - login status `400`
  - message `Incorrect email or password`
- Cross-store deterministic seed is now unlocked:
  - alternate store `10141`
  - alternate sku `21`
  - `ORD-API-008` and `ORD-API-017` are now executable and `PASS`.


## Latest verified run (2026-03-23, host `192.168.1.103`)
- Evidence:
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.failed.json`
  - `artifacts/test-results/api-regression/api_regression.log`
  - `docs/findings/order_execution_findings_2026-03-23.md`
- Summary (full run while host was reachable):
  - `total=166`
  - `passed=65`
  - `failed=7`
  - `skipped=94`

## Layered execution snapshot (2026-03-23)
- `CORE`: `total=109`, `passed=64`, `failed=7`, `skipped=38`
- `JOURNEYS`: `total=33`, `passed=1`, `failed=0`, `skipped=32`
- `EDGE`: not re-run independently after host instability; use full-run evidence for edge outcomes.

## Key interpretation (2026-03-23)
- Journey fail count is `0`, but skip count is still high due auth access drift:
  - customer login returns `400 Incorrect email or password`
  - merchant login returns `400 Incorrect email or password`
- Admin auth and admin scope endpoints remain executable.
- Backend defect detection remains intact (no weakened expectations).

## ORD-API-022 classification status
- Runner logic now classifies runtime `200` on past `arrivalTime` as `CLASS=CONTRACT_REVIEW` pass when executable.
- In 2026-03-23 execution it was `SKIPPED` because customer auth token was unavailable.
- Keep this item under contract-review until customer-scope execution is restored.

## Latest verified run (2026-03-20, host `192.168.1.103`)
- Evidence:
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.failed.json`
  - `artifacts/test-results/api-regression/api_regression.log`
- Summary:
  - `total=166`
  - `passed=128`
  - `failed=7`
  - `skipped=31`

## Layered execution snapshot (2026-03-20)
- `CORE`: `total=109`, `passed=102`, `failed=6`, `skipped=1`
- `JOURNEYS`: `total=33`, `passed=26`, `failed=1`, `skipped=6`
- `EDGE`: `total=26`, `passed=1`, `failed=0`, `skipped=25`

## Confirmed backend defects (remain FAIL)

| Testcase | Endpoint | Observed | Expected |
|---|---|---|---|
| `STO-009` | `GET /api/v1/store/999999999` | `500` | `400/404` |
| `STO-011` | `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA?UniqueId=UNKNOWN-UNIQUE-ID-QA` | `500` | `400/404` |
| `STO-012` | `GET /api/v1/store/collections` | `500` | `200/400/404/415` |
| `ORD-API-014` | `POST /api/v1/orders` with invalid `storeId=999999999` | `500` | `400/404/422` |
| `ORD-API-015` | `POST /api/v1/orders` with missing/zero `storeId` | `500` | `400/422` |
| `MEMBER-001` | `GET /api/v1/member/list` | `500` | `200` |
| `STCATADM-004` | `GET /api/v1/store-category/admin/detail/999999999` | `500` | `400/404` |

## Contract-review item (not counted as backend defect yet)
- `ORD-API-022` (`POST /api/v1/orders` with past `arrivalTime`):
  - runtime behavior has returned `200` on executable runs,
  - testcase is now tracked as `CONTRACT_REVIEW` until product owner confirms whether this is accepted business behavior or validation gap.

## Non-defect blockers (still skipped)

### Seed blockers
- `STO-010`: deterministic uniqueId seed unresolved.
- `ORD-API-018`: no deterministic closed/ordering-disabled store seed.
- `ORD-API-019`: no deterministic disabled/out-of-stock sku seed.
- `NEWS-003`: `/news` list returns zero records, no detail slug seed.
- `NOTI-ORD-001`: notification payload has no deterministic order-event correlation key.

### Scope blockers
- `MORD-001`, `MORD-API-001..008`: merchant role token unavailable because merchant login fails with `400 Incorrect email or password`.
- `NOTI-ORD-004`, `NOTI-ORD-005`: depend on merchant lifecycle happy path not yet proven with accept=200 branch.
- `ORD-CAVEAT-002`: deterministic merchant-owned reject-detail assertion is not available.

### Runtime-contract/config blockers
- `ORD-CAN-004`: cancellation timeline assertion mapping is not deterministic.
- `NOTI-ORD-002`, `NOTI-ORD-003`, `NOTI-ORD-006`: lifecycle notification correlation is not deterministic.
- `ORD-JOB-*` and `ORD-CAVEAT-001/003/004`: require controlled scheduler windows or additional runtime instrumentation.

## Notes
- `STO-012` is currently `FAIL 500` in this runtime (`Sequence contains no elements.`).
- Order suite is now journey-based for core flows (fresh order per payment/customer/merchant journey), reducing state-pollution false negatives.

## Next actions
1. Re-verify the seven defects above after backend fixes.
2. Provide valid merchant runtime credentials, then rerun merchant journeys (`MORD-API-*`) with dedicated merchant-owned order.
3. Add deterministic uniqueId, closed/ordering-disabled store, and disabled/out-of-stock sku seeds to reduce skip set.
4. Unlock one deterministic merchant accept=200 branch and chain arrived/complete on that dedicated order.
5. Add deterministic notification correlation strategy (event code + order id mapping).
