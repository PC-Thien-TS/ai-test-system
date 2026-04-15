# RANKMATE Wave 1 First Execution Report

Date: `2026-04-14`  
Repo: `C:\Projects\Rankmate\ai_test_system`

## A. Findings
- Existing Wave 1 suite is present and collects correctly (`49` tests).
- Suite is safe-by-default and requires `RANKMATE_WAVE1_ENABLED=1`.
- Local runtime is currently missing `.env` and all required Wave 1 values.
- Backend endpoint was not reachable on expected local ports from `rankmate_be` launch settings.

## B. Changes Made
- Added runtime preflight gating for connectivity:
  - `tests/rankmate_wave1/conftest.py`
  - New session fixture `ensure_wave1_backend_reachable` skips clearly when `API_BASE_URL` is unreachable.
- Added runtime templates/docs:
  - `.env.wave1.example`
  - `docs/wave1_runtime/RANKMATE_WAVE1_RUNTIME_ENV_CONTRACT.md`
  - `docs/wave1_runtime/RANKMATE_WAVE1_RUNNABLE_MATRIX.md`

## C. Commands Actually Run
1. Collect Wave 1 tests
   - `pytest --collect-only -q tests/rankmate_wave1`
2. Run Wave 1 suite in default mode
   - `pytest -q -rs tests/rankmate_wave1`
3. Probe backend ports from `rankmate_be` launch settings
   - HTTP probes to `localhost:5209`, `localhost:5985`, `localhost:7005`
4. Attempt to execute auth phase with suite enabled
   - `RANKMATE_WAVE1_ENABLED=1 API_BASE_URL=http://localhost:5209 pytest -q -rs tests/rankmate_wave1/test_auth_api.py`
5. Attempt full Wave 1 run with suite enabled
   - `RANKMATE_WAVE1_ENABLED=1 API_BASE_URL=http://localhost:5209 pytest -q -rs tests/rankmate_wave1`
6. Attempt to boot backend quickly
   - `dotnet run --project C:\Projects\Rankmate\rankmate_be\CoreV2.MVC\CoreV2.MVC.csproj --urls http://localhost:5209` (timed out; endpoint remained unreachable)

## D. Execution Outcomes

### Run 1: Collect-only
- Result: `49 collected`
- Status: Success

### Run 2: Default Wave 1 run (safe mode)
- Result: `49 skipped`
- Reason: suite disabled by default (`RANKMATE_WAVE1_ENABLED` not set to `1`)

### Run 3: Auth phase attempt with suite enabled
- Result: `10 skipped`, `0 passed`, `0 failed`, `0 xfailed`
- Primary reason:
  - `Wave 1 backend is unreachable at http://localhost:5209`

### Run 4: Full Wave 1 attempt with suite enabled
- Result: `49 skipped`, `0 passed`, `0 failed`, `0 xfailed`
- Primary reason:
  - backend unreachable, preflight skip applied for every case

## E. Runnable vs Blocked (Current Session)
- Runnable now: **0 / 49**
- Blocked: **49 / 49**
- Dominant blocker:
  - **Connectivity**: `API_BASE_URL` endpoint unreachable
- Secondary blockers once connectivity is fixed:
  - missing role credentials
  - missing store/SKU seeds
  - missing order-state seeds
  - missing Stripe/MoMo callback secrets

## F. Case Coverage Status
- `AUTH-API-*`: blocked at connectivity preflight
- `ORD-API-*`: blocked at connectivity preflight
- `PAY-API-*`: blocked at connectivity preflight
- `MER-API-*`: blocked at connectivity preflight
- `CONS-API-*`: blocked at connectivity preflight

## G. Decision
- Stop progression at Phase A because foundational runtime connectivity is blocked.
- Do not force deeper phases (Order/Payment/Merchant/Consistency) until backend is reachable.

## H. Next Unblock Actions
1. Start or expose a reachable backend URL for `API_BASE_URL` (owner: BE/DevOps).
2. Provide Wave 1 role accounts:
   - `API_USER/API_PASS`
   - `API_MERCHANT_USER/API_MERCHANT_PASS`
   - `API_ADMIN_USER/API_ADMIN_PASS`
3. Provide deterministic store+SKU seeds:
   - `API_ORDER_STORE_ID`, `API_ORDER_SKU_ID`
4. Re-run Phase A only:
   - `pytest -q -rs tests/rankmate_wave1/test_auth_api.py`
5. After Phase A passes, proceed to Phase B order/idempotency run.

