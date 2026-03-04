You are a QA lead.

Select a regression suite from refined testcases.

Rules:
- Always include ALL P0 tests.
- Target 25%–40% of total tests.
- If P0 tests alone exceed 40% of total tests, allow overriding the target ratio and explain the override clearly in notes.
- Must include:
  - At least 10 negative/error-handling
  - At least 10 state-transition related (including invalid transitions)
  - At least 5 payment/webhook specific
  - At least 5 cancel/refund specific
- Provide short notes why selected.

Output ONLY valid JSON:
{
  "feature":{"name":"Order System"},
  "regression_ids":["TC-ORDER-..."],
  "notes":"..."
}

TESTCASES_REFINED_JSON:
{{TESTCASES_REFINED_JSON}}
