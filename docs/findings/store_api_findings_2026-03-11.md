# Store API Findings (2026-03-11)

## Classification
Backend defects. These are not test framework issues.

## Confirmed Defects
1. `STO-009`
- Endpoint: `GET /api/v1/store/999999999`
- Expected: `400` or `404`
- Observed: `500`
- Error payload includes: `"message":"Store not found"`

2. `STO-011`
- Endpoint: `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA`
- Expected: `400` or `404`
- Observed: `500`
- Error payload includes: `"message":"Store with UniqueId UNKNOWN-UNIQUE-ID-QA not found"`

3. `STO-012`
- Endpoint: `GET /api/v1/store/collections`
- Expected: one of `200`, `400`, `404`, `415` per regression expectation set
- Observed: `500`
- Error payload includes: `"message":"Sequence contains no elements."`

## Not A Backend Defect
- `STO-010` is not classified as a backend defect.
- Latest issue was runner-side seed extraction selecting a wrong string field for `uniqueId`.
- Regression runner now uses strict store uniqueId key extraction (`uniqueId`/`storeUniqueId`/`unique_id`) for STO-010.

## Why This Is a Defect
- Not-found conditions are being surfaced as server errors (`5xx`) instead of controlled client/domain errors (`4xx`).
- Regression suite correctly classifies both as `FAIL`.

## Recommended Backend Action
- Normalize not-found paths to domain-safe `404` (or `400`) with stable error schema.
- Ensure no exception path leaks as `500` for invalid identifiers.
- Guard `/store/collections` against empty sequence assumptions and return controlled domain response.

## Evidence
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/API_REGRESSION_FINDINGS.md`
