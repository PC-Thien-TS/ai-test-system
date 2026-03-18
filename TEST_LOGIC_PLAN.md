# TEST_LOGIC_PLAN

## Goal

Prioritize business logic verification (unit/integration) before performance/security load testing.

## Detected Project Structure

- Backend (.NET):
  - Path: `C:\Projects\Rankmate\rankmate_be`
  - Solution: `CoreV2.sln`
  - Core projects: `CoreV2.Application`, `CoreV2.Domain`, `CoreV2.MVC`, `CoreV2.Infrastructure`, `CoreV2.Persistence`
- Frontend (React / Next.js):
  - Path: `C:\Projects\Rankmate\rankmate_fe`
  - Package manifest: `package.json`

## Added Test Suites

### Backend unit tests (xUnit)

- Project: `C:\Projects\Rankmate\rankmate_be\tests\Backend.UnitTests\Backend.UnitTests.csproj`
- Coverage focus:
  - API key predicate logic
  - Store predicate logic
  - Product predicate logic
  - Category predicate logic
  - Search-related technical invariant (`StringHelper` invalid JSON behavior)
- Minimum delivered:
  - `10` unit tests

### Backend integration tests (controller-level, xUnit)

- Project: `C:\Projects\Rankmate\rankmate_be\tests\Backend.IntegrationTests\Backend.IntegrationTests.csproj`
- Coverage focus:
  - Auth required/anonymous access invariants
  - Store verification approve/reject endpoint behavior
  - Search history create endpoint technical invariant (IP propagation + no-content response)
  - API key create endpoint response contract
  - Category CRUD route presence
- Minimum delivered:
  - `7` integration tests

### Frontend unit tests (Vitest)

- Config: `C:\Projects\Rankmate\rankmate_fe\vitest.config.ts`
- Test file: `C:\Projects\Rankmate\rankmate_fe\src\utilities\logic.hotspots.test.ts`
- Coverage focus:
  - Preferences parsing and cookie-state helpers
  - Date formatting utility
- Minimum delivered:
  - `8` unit tests

## UNKNOWN Areas (Business Rules Not Explicit)

The following tests intentionally assert technical invariants only because explicit business rules are not fully defined in the repository artifacts:

- Store verify approve/reject:
  - assert command dispatch, endpoint availability, and response type only
- Search history create/list/delete:
  - assert endpoint behavior invariants (no crash, expected action result shape)
- API key lifecycle:
  - assert response contract and endpoint invocation path only
- Category/product deep validation rules:
  - assert route and filtering invariants from existing predicate logic

## How To Run

### Windows (PowerShell)

```powershell
pwsh ./scripts/run_logic_tests.ps1
```

### Linux/macOS (bash)

```bash
bash ./scripts/run_logic_tests.sh
```

## Report Artifacts

All reports are written to:

- `artifacts/test-results/backend/`
  - `.trx` backend test report
  - `.junit.xml` backend test report
- `artifacts/test-results/frontend/`
  - `.junit.xml` frontend unit test report

## Notes

- Runtime application code was not changed in this task.
- Only tests, test projects, test config, and runner/docs were added.
- If `dotnet` is not installed, backend tests cannot run; install .NET SDK 8+ and rerun the script.
