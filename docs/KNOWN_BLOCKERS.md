# Known Blockers

## Active Blockers

| Blocker ID | Area | Symptom | Impact | Affected Assets | Current State |
|---|---|---|---|---|---|
| `BLK-UI-001` | Admin web login | `GET /en/login` can render `Internal Server Error` | Prevents stable admin UI E2E entry and causes dependent flow skips | `scripts/run_ui_e2e.ps1`, `tests/ui_e2e/tests/admin_e2e.spec.js` | Open |
| `BLK-API-001` | Store API | `GET /api/v1/store/999999999` returns `500` | Invalid-id regression remains a backend defect | `scripts/run_api_regression.ps1` `STO-009` | Open |
| `BLK-API-002` | Store API | `GET /api/v1/store/UNKNOWN-UNIQUE-ID-QA` returns `500` | Invalid unique id path is not safely handled | `scripts/run_api_regression.ps1` `STO-011` | Open |
| `BLK-API-003` | Store API | `GET /api/v1/store/collections` returns `500` (`Sequence contains no elements.`) | Store collections path is unstable and server-side exception is exposed | `scripts/run_api_regression.ps1` `STO-012` | Open |
| `BLK-API-004` | Member API | `GET /api/v1/member/list` returns `500` mapping/configuration error | Admin member list flow cannot be trusted for regression gates | `scripts/run_api_regression.ps1` `MEMBER-001` | Open |
| `BLK-API-005` | Store-category admin API | `GET /api/v1/store-category/admin/detail/{invalidId}` returns `500` | Invalid-id path should be controlled `4xx`, not server error | `scripts/run_api_regression.ps1` `STCATADM-004` | Open |
| `BLK-ROLE-001` | Admin/business modules | Positive API cases can return `401/403` for non-admin accounts | `category-admin`, `dashboard`, `member`, and `store-category-admin` may skip instead of executing | `scripts/run_api_regression.ps1`, admin UI flows | Open |

## Review Items That Are Not Confirmed Defects

| Review ID | Area | Observed Behavior | Why It Matters | Current Decision |
|---|---|---|---|---|
| `REV-ORG-001` | Organization detail | Invalid id can return `200` with `data:null` | Contract may be acceptable but should be reviewed against product expectation | Keep aligned to Swagger until contract is tightened |
| `REV-NOTI-001` | Notification actions | `mark-read` and `delete` accept empty payload and can still return `200` | Semantics may be weaker than product expectation | Keep current tests aligned to Swagger |
| `REV-ORDER-001` | Order detail under admin account | `ORD-003` and `ORD-API-004` can return `400 FORBIDDEN_SCOPE` | Scope/account mismatch can look like failure but is not a backend defect | Keep classified as scope mismatch; rerun with scope-matching account |

## Recommended Next Actions

1. Fix the five active backend defects first (`STO-009`, `STO-011`, `STO-012`, `MEMBER-001`, `STCATADM-004`) because they are confirmed `500` defects.
2. Stabilize the admin login route so UI E2E can execute beyond preflight.
3. Decide whether admin-only suites should always run with a dedicated admin account instead of a general test account.
4. Promote these blockers into formal requirement status once the SRS is imported.
