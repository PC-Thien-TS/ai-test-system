# Order Execution Findings (2026-03-24)

## Scope
- Repository: `C:\Users\PC-Thien\ai_test_system`
- Runtime host: `http://192.168.1.103:19066`
- Runner: `scripts/run_api_regression.ps1`
- Verification objective: rerun `CORE` + `JOURNEYS` and manually inspect all non-pass cases before any status claim.

## Commands executed
```powershell
$env:API_BASE_URL='http://192.168.1.103:19066'
$env:API_USER='tieuphiphi020103+71111@gmail.com'
$env:API_PASS='Thien123$'
$env:API_MERCHANT_USER='tieuphiphi020103+71111@gmail.com'
$env:API_MERCHANT_PASS='Thien123$'
$env:API_ADMIN_USER='admin@gmail.com'
$env:API_ADMIN_PASS='123'
$env:API_STORE_ID='9768'
$env:API_ORDER_STORE_ID='9768'
$env:API_ORDER_SKU_ID='14'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode CORE
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode JOURNEYS
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode CORE
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api_regression.ps1 -Mode EDGE
```

## Fresh layer summaries
- `CORE`: `total=109`, `passed=102`, `failed=7`, `skipped=0`
- `JOURNEYS`: `total=33`, `passed=33`, `failed=0`, `skipped=0`
- `EDGE` (diagnostic skip-cluster verification): `total=26`, `passed=1`, `failed=0`, `skipped=25`

## FAIL verification (stable across rerun)
Repeated CORE execution produced the same FAIL set with unchanged endpoint/expected/actual/body:
- `STO-009`: `GET /api/v1/store/999999999` expected `400/404`, actual `500`, body message `Store not found`
- `STO-011`: `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA?UniqueId=UNKNOWN-UNIQUE-ID-QA` expected `400/404`, actual `500`, body message `Store with UniqueId ... not found`
- `STO-012`: `GET /api/v1/store/collections` expected `200/400/404/415`, actual `500`, body message `Sequence contains no elements.`
- `ORD-API-014`: `POST /api/v1/orders` invalid `storeId=999999999` expected `400/404/422`, actual `500`, body message `Store with id 999999999 not found.`
- `ORD-API-015`: `POST /api/v1/orders` missing/zero storeId expected `400/422`, actual `500`, body message `Store with id 0 not found.`
- `MEMBER-001`: `GET /api/v1/member/list` expected `200`, actual `500`, body message `Missing type map configuration or unsupported mapping...`
- `STCATADM-004`: `GET /api/v1/store-category/admin/detail/999999999` expected `400/404`, actual `500`, body message `Store category not found`

## Skip-cluster verification
- `MORD-* merchant auth blocker`: **not reproduced** in this round.
  - merchant token path executed; merchant cases in `JOURNEYS` are no longer skipped.
  - remaining merchant issue is lifecycle business-state precondition (`400` controlled responses).
- `STO-010`: still `SEED_BLOCKER` (uniqueId route ambiguous; deterministic uniqueId seed not proven).
- `ORD-API-018`: still `RUNTIME_CONTRACT_CONFIG_BLOCKER` (no deterministic closed/ordering-disabled store seed).
- `ORD-API-019`: still `SEED_BLOCKER` (no deterministic disabled/out-of-stock sku seed).
- `NEWS-003`: still `SEED_BLOCKER` (no deterministic slug from current news list payload).
- `NOTI-ORD-*`: still blocked due missing deterministic event correlation keys and merchant lifecycle happy-path proof.

## Contract review item
- `ORD-API-022`: remains `CLASS=CONTRACT_REVIEW` because runtime still accepts past `arrivalTime` with `200`.

## Artifacts
- `artifacts/test-results/api-regression/api_regression.summary.core.json`
- `artifacts/test-results/api-regression/api_regression.summary.journeys.json`
- `artifacts/test-results/api-regression/api_regression.summary.edge.json`
- `artifacts/test-results/api-regression/api_regression.core.log`
- `artifacts/test-results/api-regression/api_regression.journeys.log`
- `artifacts/test-results/api-regression/api_regression.edge.log`
