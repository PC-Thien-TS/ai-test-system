# TEST_SUGGESTIONS

Generated at: 2026-03-05T03:16:16.539981+00:00

Smoke suggestions are generated from discovered routes/endpoints only. Where behavior details are missing from code/evidence, expectations should remain `UNKNOWN` until clarified.

## Authentication

- Evidence: 41 API endpoint(s), 5 route(s).
- Login with valid credentials returns token/session and redirects to authenticated route.
- Login with invalid credentials is rejected with stable error contract and no session created.
- Refresh token and logout invalidate old session; subsequent protected call fails.

## User management

- Evidence: 34 API endpoint(s), 10 route(s).
- Fetch and update account/profile data, verify persisted changes are returned by follow-up GET.
- Attempt unauthorized profile/member mutation and verify permission enforcement.
- Organization/member switch updates effective access scope across dependent endpoints.

## Store / merchant features

- Evidence: 54 API endpoint(s), 16 route(s).
- Submit store verification, then verify status retrieval reflects transition.
- Approve/reject verification via admin endpoints and confirm resulting state + audit visibility.
- Store category/location operations enforce validation on required fields and invalid IDs.

## Search

- Evidence: 8 API endpoint(s), 5 route(s).
- Keyword search returns deterministic schema for posts/authors/stores.
- Suggestions/hot-keywords endpoints respond under expected latency budget (threshold UNKNOWN).
- Search history create/delete flow persists and removes entries correctly.

## Menu / catalog

- Evidence: 43 API endpoint(s), 4 route(s).
- Create/update/delete product/category and verify listing endpoints reflect changes.
- Invalid catalog payloads are rejected with consistent validation messages.
- Document/folder retrieval endpoints return expected metadata and pagination semantics.

## Payment

- Evidence: 7 API endpoint(s), 3 route(s).
- Payment initiation returns expected redirect/result payload and transaction identifier.
- Wallet balance and transaction history stay consistent after payment/topup events.
- Failed payment flow does not mutate wallet/order state unexpectedly.

## Notifications

- Evidence: 24 API endpoint(s), 3 route(s).
- Send notification endpoint accepts valid payload and records delivery attempt.
- Notification template/policy CRUD updates are visible in admin retrieval endpoints.
- Anonymous vs authorized notification endpoints enforce intended access control.

## Admin panel

- Evidence: 50 API endpoint(s), 11 route(s).
- Dashboard/admin list endpoints return data for authorized users and deny unauthorized users.
- Moderation flows (reports/posts approval/support) update statuses consistently.
- Bulk admin operations (remove multiple/patch) are atomic or document partial-failure behavior.

## Monitoring / operations

- Evidence: 2 API endpoint(s), 0 route(s).
- Hot-update manifest/admin flows expose correct active version metadata.
- Operational telemetry endpoints (user behavior, dashboard metrics) return schema-stable payloads.
- Release-critical endpoints have observable audit trails/log events (details UNKNOWN if not exposed).

## Content / community

- Evidence: 38 API endpoint(s), 4 route(s).
- Post/comment/media CRUD and retrieval endpoints preserve content integrity across refresh.
- Community moderation/reporting endpoints handle abusive content and state changes correctly.
- Anonymous content access is limited to intended routes while protected operations require auth.

## Infrastructure / platform

- Evidence: 45 API endpoint(s), 24 route(s).
- Verify endpoint/service availability and error handling for invalid payloads.
- Verify authentication and authorization behavior on protected operations.
- Verify observability signal exists for failure cases (logs/metrics/audit, if available).

