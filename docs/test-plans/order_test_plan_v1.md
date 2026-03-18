# Order Module Test Plan v1

## Scope

Initial QA scope for Order module in the existing automation project, with additive integration only.

Included API groups:

- `AdminOrders`
- `MerchantOrders`
- `OrderAddons`
- `OrderingPolicy`
- `OrderingPolicyAdmin`
- `Orders`
- `Payments`
- `Seed` (documented only for future controlled setup)

## Objectives

1. Add structured order test assets and traceability.
2. Wire an initial safe subset into `scripts/run_api_regression.ps1`.
3. Keep current non-order module coverage stable.
4. Prefer deterministic `SKIPPED` over brittle failures when seeds/roles are unavailable.

## Initial Integrated Cases (v1)

- `PAY-001` `GET /api/v1/payments/methods`
- `AORD-001` `GET /api/v1/admin/orders`
- `MORD-001` `GET /api/v1/merchant/orders`
- `ORD-001` `POST /api/v1/orders`
- `ORD-003` `GET /api/v1/orders/{id}`
- `MORD-003` `POST /api/v1/merchant/orders/{id}/accept`
- `POL-001` `GET /api/v1/ordering-policy/store/{storeId}`

## Execution Rules

- If seed `orderId` or `storeId` cannot be inferred safely, mark dependent cases `SKIPPED`.
- For admin-only endpoints:
  - `401/403` => `SKIPPED: requires admin role`.
- For merchant-role endpoints:
  - `401/403` => `SKIPPED: requires merchant role`.
- Unexpected `5xx` remains `FAIL` (regression finding), including for invalid/not-found-style paths.
- Existing output schema remains unchanged.

## Seeds

v1 seed sources:

1. Existing store seeds from current regression run (`STO-*`), reused as fallback for `storeId`.
2. `orderId` and `storeId` inferred from:
   - `AORD-001` response
   - `MORD-001` response
   - `ORD-001` response (if successful)

If none available:

- `ORD-003`, `MORD-003`, `POL-001` are `SKIPPED`.

## Deferred to v2

- Full order lifecycle chaining:
  - `reject`, `mark-arrived`, `complete`
- Order payments and addon-payment flows with stable rollback
- Dispute flow coverage
- Policy admin write flows
- Pilot seed endpoint gating and cleanup policy

## Artifacts

Runner output remains:

- `artifacts/test-results/api-regression/api_regression.log`
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `artifacts/test-results/api-regression/api_regression.failed.json` (only when failures exist)
