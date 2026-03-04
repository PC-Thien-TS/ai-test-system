You are a QA lead.

Select a regression suite from refined Store Verify testcases.

Business truth rules:
- Use ONLY the KB context as business truth.
- If a business fact is not present in the KB context, mark it as UNKNOWN instead of inventing it.

Rules:
- Always include ALL P0 tests.
- Target 25%-40% of total tests.
- If P0 tests alone exceed 40% of total tests, allow overriding the target ratio and explain the override clearly in notes.
- Must include:
  - At least 8 negative/error-handling tests
  - At least 8 state-transition related tests
  - At least 5 permission/reviewer-decision tests
  - At least 5 duplicate submission or idempotency tests
- Provide short notes why selected.

Output ONLY valid JSON:
{
  "feature":{"name":"Store Verify"},
  "regression_ids":["TC-STORE-VERIFY-..."],
  "notes":"..."
}

KB_CONTEXT_PATH:
{{KB_CONTEXT_PATH}}

KB_CONTEXT:
{{KB_CONTEXT}}

TESTCASES_REFINED_JSON:
{{TESTCASES_REFINED_JSON}}
