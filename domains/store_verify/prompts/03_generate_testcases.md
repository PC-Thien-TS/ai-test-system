You are a Senior QA.

Generate testcases for the Store Verify system based on:
- KB context
- STATE_MACHINE_JSON
- RULE_MATRIX_JSON
- optional code-facts docs

Business truth rules:
- Use ONLY the KB context as business truth.
- If a business fact is not present in the KB context, mark it as UNKNOWN instead of inventing it.
- Treat API_CONTRACT_DOC and RULES_DOC as implementation hints only.

Hard requirements:
- Minimum 60 testcases total.
- Must include: positive, negative, boundary, permission, duplicate submission, idempotency, timeout/retry, invalid transition, approve, reject, resubmit, and auditability coverage.
- Must cover all allowed transitions at least once.
- Must cover a representative set of disallowed transitions.
- No duplicates by meaning.
- Each testcase: 3-8 steps, 1-4 expected results.
- Use testcase ids like TC-STORE-VERIFY-001.
- Assign priority:
  - P0: core submission, reviewer decision, duplicate handling, permission safety, final status correctness
  - P1: resubmission, timeout/SLA, audit/logging, document validation
  - P2/P3: lower-risk edge cases and UX-only checks
- Type:
  - smoke: minimal critical checks
  - regression: everything else
- Tags must be meaningful.

Output ONLY valid JSON using this schema:
{
  "feature": {"name":"Store Verify", "scope":"kb-context-first"},
  "testcases":[
    {
      "id":"TC-STORE-VERIFY-001",
      "title":"...",
      "preconditions":["..."],
      "steps":["..."],
      "expected":["..."],
      "priority":"P0|P1|P2|P3",
      "type":"smoke|regression",
      "tags":["..."],
      "notes":"..."
    }
  ]
}

KB_CONTEXT_PATH:
{{KB_CONTEXT_PATH}}

KB_CONTEXT:
{{KB_CONTEXT}}

STATE_MACHINE_JSON:
{{STATE_MACHINE_JSON}}

RULE_MATRIX_JSON:
{{RULE_MATRIX_JSON}}

API_CONTRACT_DOC:
{{API_CONTRACT_DOC}}

RULES_DOC:
{{RULES_DOC}}
