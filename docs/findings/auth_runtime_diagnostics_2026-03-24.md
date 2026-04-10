# Auth Runtime Diagnostics (2026-03-24)

## Scope
- Host: `http://192.168.1.103:19066`
- Endpoint: `POST /api/v1/auth/login`
- Accounts tested:
  - customer account: `tieuphiphi020103+71111@gmail.com`
  - admin execution account: `admin@gmail.com`
  - merchant account: `tieuphiphi020103+71111@gmail.com`

## Observed results
- `tieuphiphi020103+71111@gmail.com / Thien123$`: `PASS 200` (customer token extracted)
- `admin@gmail.com / 123`: `PASS 200` (admin token extracted)
- merchant token path: `PASS 200` in current verification round (merchant-scoped modules execute).

## Regression impact
- Merchant module checks are no longer blocked by login/auth in this host run.
- Remaining merchant limitation is lifecycle state precondition (`accept/reject/arrived/complete` currently return controlled `400` on selected order state).
- Backend defect visibility remains intact (`7 FAIL` unchanged).

## Note
- Earlier 2026-03-24 diagnostics on host `192.168.1.7` observed merchant login `400`.
- Current source-of-truth verification for this round is host `192.168.1.103`, where merchant auth succeeds.
