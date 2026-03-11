# Store Module Status (2026-03-11)

## Summary
- Module state: **Backend Defect**
- Latest Store result split: `8 PASS`, `3 FAIL`, `1 SKIPPED`
- Active defects: `STO-009`, `STO-011`, `STO-012`

## Active Defects Only
- `STO-009`: `GET /api/v1/store/999999999` -> `500` (expected controlled `400/404`)
- `STO-011`: `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` -> `500` (expected controlled `400/404`)
- `STO-012`: `GET /api/v1/store/collections` -> `500` (`Sequence contains no elements.`; expected status set excludes `5xx`)

## Expected Non-defect Behaviors
- `STO-005` `/api/v1/store/views` -> `415` (accepted capture behavior in expected status set)
- `STO-010` `/api/v1/store/{uniqueId}` -> `SKIPPED` (missing stable uniqueId seed in current dataset; not a backend defect)

## References
- Detailed Store findings: `docs/findings/store_api_findings_2026-03-11.md`
- Endpoint-level Store status: `docs/findings/store_module_status_2026-03-11.md`
- Health snapshot: `docs/API_REGRESSION_HEALTH_2026-03-11.md`
- Latest run artifact: `artifacts/test-results/api-regression/api_regression.summary.json`
