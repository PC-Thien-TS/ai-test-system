You are a Senior QA and release auditor.

Generate testcases for the Didaunao release-audit domain based on:
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
- Must include: positive, negative, boundary, permission, evidence-missing, threshold-breach, rollback-readiness, monitoring/observability, and data/search quality coverage.
- Must cover all allowed transitions or stage progressions at least once.
- Must cover a representative set of blocked or disallowed releases.
- No duplicates by meaning.
- Each testcase: 3-8 steps, 1-4 expected results.
- Use testcase ids like TC-DIDAUNAO-RELEASE-AUDIT-001.
- Assign priority:
  - P0: release blockers, crash/ANR, security, rollback, API SLA, missing monitoring, severe data corruption
  - P1: UX/UI commercial pass gaps, search relevance, data quality drift, incomplete evidence, partial observability
  - P2/P3: lower-risk documentation or non-blocking process gaps
- Type:
  - smoke: minimal critical release checks
  - regression: everything else
- Tags must be meaningful.

Output ONLY valid JSON using this schema:
{
  "feature": {"name":"Didaunao Release Audit", "scope":"kb-context-first"},
  "testcases":[
    {
      "id":"TC-DIDAUNAO-RELEASE-AUDIT-001",
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
