# Order Test Preconditions

## Purpose

Define mandatory business and technical setup before executing Order-module tests to avoid false failures caused by missing prerequisites.

## Environment

- Target API base URL is reachable and stable.
- Swagger contract endpoint is reachable.
- Test environment data is isolated enough for repeated QA execution.

## Required Accounts

- Admin account with access to verification and admin-order endpoints.
- Merchant account that can log in to merchant web and access merchant-order endpoints.
- Customer/test ordering account (if order creation requires authenticated user).

## Store Readiness Checklist

- [ ] Store is created.
- [ ] Store is verified.
- [ ] Required admin approval/verification is completed.
- [ ] Merchant account is linked to the verified store.
- [ ] Store status is active/ready for ordering.

## Catalog/Menu Readiness Checklist

- [ ] At least one menu or category exists.
- [ ] At least one orderable item/service exists.
- [ ] Item/service price is configured.
- [ ] Item/service and menu/category publish/active status is correct.

## Ordering Readiness Checklist

- [ ] Ordering policy exists for target store if required by system rules.
- [ ] Any ordering windows or guard rules are satisfied.
- [ ] At least one valid seed order ID can be inferred or created for lifecycle actions.
- [ ] Merchant order actions (accept/reject/arrived/complete) are tested only on eligible order states.

## Payment Readiness Checklist

- [ ] Payment methods are retrievable (`GET /api/v1/payments/methods`).
- [ ] Payment-related dependencies are configured for the environment.
- [ ] Order/addon payment test payload prerequisites are known.

## Evidence Required

- API response artifacts from regression runner:
  - `artifacts/test-results/api-regression/api_regression.summary.json`
  - `artifacts/test-results/api-regression/api_regression.log`
- Screenshots or admin pages proving:
  - store verified state
  - merchant-store linkage
  - published menu/item/service
- Optional seed tracking notes:
  - store ID
  - order ID
  - account used

## Blockers / Dependencies

- Missing verified store.
- Merchant account not linked to store.
- No active catalog/menu/item configured.
- Missing ordering policy where required.
- Insufficient account role permission (admin/merchant).
- Environment instability causing non-deterministic failures.

## Execution Notes

- If prerequisites are missing, classify dependent order cases as `SKIPPED` with explicit notes.
- Do not force lifecycle calls without known eligible order state.
- Treat unexpected `5xx` as regression findings.
- Capture exact status/body for invalid/not-found paths to support contract review.
