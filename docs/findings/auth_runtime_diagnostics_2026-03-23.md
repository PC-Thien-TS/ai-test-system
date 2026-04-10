# Auth Runtime Diagnostics (2026-03-23)

## Scope
- Host: `http://192.168.1.103:19066`
- Endpoint: `POST /api/v1/auth/login`
- Accounts tested:
  - customer: `tieuphiphi020103+71111@gmail.com`
  - merchant: `tieuphiphi020103+71111@gmail.com`
  - admin: `admin@gmail.com`

## Observed results
- Customer login: `400`
  - message: `Incorrect email or password`
- Merchant login: `400`
  - message: `Incorrect email or password`
- Admin login: `200`
  - token extraction succeeded

## Additional checks
- Historical password candidates (`Thien123$`, `Thien0602$`, variants) were probed for the customer/merchant email:
  - all returned `400 Incorrect email or password`.
- Admin scope checks remained executable for:
  - `/api/v1/admin/orders`
  - `/api/v1/category-admin/list`
  - `/api/v1/Dashboard/user-registrations`
- `member/list` still returns backend `500` and remains defect-classified.

## Impact on regression
- Customer/merchant-token-dependent cases are correctly classified as blockers (`CONFIG_BLOCKER` or `SCOPE_BLOCKER`) and skipped.
- Backend defect visibility is preserved via admin-capable checks and admin fallback probes where designed.

## Required recovery action
1. Provide a currently valid customer credential pair for this host.
2. Provide a currently valid merchant credential pair for this host.
3. Re-run:
   - `.\scripts\run_api_seed_precheck.ps1`
   - `.\scripts\run_api_regression.ps1 -Mode JOURNEYS`
   - `.\scripts\run_api_regression.ps1`
