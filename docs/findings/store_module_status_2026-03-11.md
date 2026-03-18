# Store Module Status (2026-03-11)

## Source
- `artifacts/test-results/api-regression/api_regression.summary.json`
- Store testcases: `STO-001` to `STO-012`

## Intent and Latest Behavior by Store Case

### Stable (PASS)
- `STO-001` `GET /api/v1/store` -> `200`
- `STO-002` `GET /api/v1/store/list` -> `200`
- `STO-003` `GET /api/v1/store/paged` -> `200`
- `STO-004` `GET /api/v1/store/reviews` -> `200`
- `STO-006` `GET /api/v1/store/verify` -> `200`
- `STO-007` `GET /api/v1/store/verify/detail` -> `200` (allowed set includes `200/400/404`)
- `STO-008` `GET /api/v1/store/{id}` valid id -> `200`

### Deterministic Seed Blocker (SKIPPED, Non-defect)
- `STO-010` `GET /api/v1/store/{uniqueId}` valid uniqueId -> `SKIPPED`  
  Reason: stable uniqueId seed not available in current dataset.

### Expected Non-critical / Capture Behavior (PASS)
- `STO-005` `GET /api/v1/store/views` -> `415`  
  Accepted by expected set (`200/400/415`), treated as capture behavior rather than active defect.

### Active Backend Defects (FAIL)
- `STO-009` `GET /api/v1/store/999999999` -> `500` (expected safe `400/404`)
- `STO-011` `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` -> `500` (expected safe `400/404`)
- `STO-012` `GET /api/v1/store/collections` -> `500` (`Sequence contains no elements.`)

## Defect vs Non-defect Separation
- Active defects:
  - `STO-009`, `STO-011`, `STO-012`
- Not active defects in latest run:
  - `STO-005` (415 capture behavior allowed)
  - `STO-010` (deterministic seed blocker; missing stable uniqueId seed)

## Recommended Next Action After Store Hardening
1. Backend team fixes Store defect paths for `STO-009`, `STO-011`, and `STO-012` with controlled non-`5xx` responses.
2. Re-run full API regression and verify Store module reaches all-pass state without masking these three defect checks.
