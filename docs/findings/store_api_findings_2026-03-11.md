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

## Why This Is a Defect
- Not-found conditions are being surfaced as server errors (`5xx`) instead of controlled client/domain errors (`4xx`).
- Regression suite correctly classifies both as `FAIL`.

## Recommended Backend Action
- Normalize not-found paths to domain-safe `404` (or `400`) with stable error schema.
- Ensure no exception path leaks as `500` for invalid identifiers.

## Evidence
- `artifacts/test-results/api-regression/api_regression.failed.json`
- `artifacts/test-results/api-regression/api_regression.summary.json`
- `docs/API_REGRESSION_FINDINGS.md`
