# Auth Runtime Diagnostics (2026-03-20)

## Scope
- Environment baselines:
  - initial check: `http://192.168.1.7:19066`
  - rerun check: `http://192.168.1.103:19066`
- Endpoint: `POST /api/v1/auth/login`
- Inputs checked:
  - customer (`API_USER` / `API_PASS`)
  - merchant (`API_MERCHANT_USER` / `API_MERCHANT_PASS`)
  - admin (`API_ADMIN_USER` / `API_ADMIN_PASS`)

## Swagger contract check
- Source: `GET /swagger/v1/swagger.json`
- Login path: `/api/v1/auth/login`
- Request schema: `CoreV2.Application.Features.Auth.Queries.LoginQuery`
- Supported request content types:
  - `application/json`
  - `text/json`
  - `application/*+json`
- Relevant properties present: `email`, `password`, `deviceID` (plus optional fields).
- Conclusion: no observable login contract drift.

## Runtime evidence
- Customer login request body:
  - `{"email":"tieuphiphi020103+71111@gmail.com","password":"***","deviceID":"qa-seed-precheck"}`
- Customer login response:
  - status `400`
  - body `{"result":90,"errors":{},"message":"Incorrect email or password","data":null}`

- Merchant login request body:
  - `{"email":"tieuphiphi020103+71111@gmail.com","password":"***","deviceID":"qa-seed-precheck-merchant"}`
- Merchant login response:
  - status `400`
  - body `{"result":90,"errors":{},"message":"Incorrect email or password","data":null}`

- Admin login response:
  - status `200`
  - token extracted successfully
  - admin precheck (`GET /api/v1/admin/orders?pageNumber=1&pageSize=1`) returns `200`

## Diagnosis
- Primary blocker is runtime credential validity for customer/merchant accounts.
- This is not a parser/framework defect and not a login contract-shape mismatch.
- Most likely causes:
  - account/password drift
  - wrong account set for this environment
  - account disabled/locked or moved to a different auth data source

## Regression impact
- Customer/merchant scoped cases are classified as blockers (`CONFIG_BLOCKER` / `SCOPE_BLOCKER`) instead of false PASS/FAIL.
- Backend defect visibility is preserved:
  - `ORD-API-014` and `ORD-API-015` run via explicit admin fallback probe.
  - Store/admin defects remain directly observable.

## Next actions
1. Replace `API_USER`/`API_PASS` with a verified customer account for this environment.
2. Replace `API_MERCHANT_USER`/`API_MERCHANT_PASS` with a verified merchant account.
3. Re-run:
   - `.\scripts\run_api_seed_precheck.ps1`
   - `.\scripts\run_api_regression.ps1`

---

## Rerun update (same date, new host `192.168.1.103`)

Runtime with:
- `API_BASE_URL=http://192.168.1.103:19066`
- `API_USER=tieuphiphi020103+71111@gmail.com`
- `API_PASS=Thien123$`
- `API_MERCHANT_USER=tieuphiphi020103+71111@gmail.com`
- `API_MERCHANT_PASS=Thien123$`
- `API_ADMIN_USER=admin@gmail.com`
- `API_ADMIN_PASS=123`

Observed:
- customer login: `PASS 200`
- merchant login: `PASS 200`
- admin login: `PASS 200`
- regression impact:
  - auth-driven blockers dropped significantly
  - `AUTH-001` and `SEA-007` became executable and passing
  - merchant flow moved from auth-blocked to partial lifecycle execution

## Latest rerun update (same host, auth volatility observed)

Seed-precheck evidence:
- customer login: `BLOCKED 400 Incorrect email or password`
- merchant login: `BLOCKED 400 Incorrect email or password`
- admin login: `PASS 200`

Interpretation:
- Customer and merchant auth on this host is currently non-deterministic across reruns.
- Admin auth remains stable.
- Regression classification must continue to treat customer/merchant-dependent failures as config/scope blockers unless credentials are freshly revalidated before run.
