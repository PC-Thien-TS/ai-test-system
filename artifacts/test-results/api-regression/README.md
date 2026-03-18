# API Regression Artifacts

## Purpose
This folder stores run outputs for API regression execution and order-focused evidence snapshots.

## Core Files
- `api_regression.summary.json`: full result set and run totals.
- `api_regression.log`: line-by-line execution log.
- `api_regression.failed.json`: only failing cases (present only when failures exist).

## Order Evidence
- `order_followup_check.json`: manual follow-up checks for order lifecycle endpoints.
- `order_critical_cases.latest.log`: focused critical order test execution excerpt.

## Latest Proven Order State (2026-03-11)
- `ORD-API-001` create order: `PASS` `200`
- `ORD-API-004` order detail: `PASS` `200`
- Merchant follow-up (`accept/reject/mark-arrived/complete`): `400 FORBIDDEN_SCOPE`
- Admin order endpoints: blocked by `401` for non-admin account

## Active Backend Defects
- `STO-009`: invalid store id returns `500`
- `STO-011`: invalid uniqueId returns `500`
