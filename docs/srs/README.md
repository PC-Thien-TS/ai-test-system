# SRS Import Skeleton

## Purpose

This folder provides an initial SRS structure for QA automation planning before full product SRS import is complete.

The goal is to:

- define module-level requirement skeletons
- establish traceability ID conventions
- connect requirements to test assets progressively
- support safe, additive expansion of automation

## Folder Model

- `docs/srs/modules/`
  - human-readable module SRS skeletons
- `test-assets/srs/raw/`
  - raw source requirements, analyst notes, exported docs
- `test-assets/srs/normalized/`
  - normalized requirement rows for tooling and mapping
- `test-assets/srs/coverage/`
  - requirement-to-test coverage matrix CSV

## Traceability Approach

1. Define requirement IDs in module docs.
2. Normalize requirement rows in `test-assets/srs/normalized/`.
3. Map requirement coverage in `test-assets/srs/coverage/srs_coverage_matrix.csv`.
4. Link to executable tests (`API`, `UI`, `FE Unit/Component`) using testcase IDs.

## Current ID Prefixes

- `AUTH-REQ-xxx`
- `STORE-REQ-xxx`
- `MENU-REQ-xxx`
- `ORDER-REQ-xxx`
- `PAY-REQ-xxx`
- `AORD-REQ-xxx`
- `MORD-REQ-xxx`

## Next Steps

1. Import raw SRS source content into `test-assets/srs/raw/`.
2. Expand each module skeleton with concrete acceptance criteria.
3. Add detailed requirement rows to normalized assets.
4. Update coverage matrix statuses based on executed automation evidence.
