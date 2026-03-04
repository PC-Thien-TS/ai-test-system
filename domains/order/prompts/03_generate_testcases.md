You are a Senior QA.

Generate testcases for the Order system based on:
- STATE_MACHINE_JSON
- RULE_MATRIX_JSON
- API_CONTRACT_DOC
- RULES_DOC
- KB docs (glossary/common_rules/bug_patterns)

Hard requirements:
- Minimum 80 testcases total.
- Must include: positive, negative, boundary, permission, idempotency, timeout/retry, webhook dedupe, late webhook, payment/order consistency, refund.
- Must cover:
  - All allowed transitions at least once
  - A representative set of disallowed transitions (invalid state jumps)
- No duplicates by meaning.
- Each testcase: 3–8 steps, 1–4 expected results.
- Assign priority:
  - P0: money safety, order creation, payment, webhook, core merchant flow
  - P1: cancellation/refund, SLA auto actions, critical notifications
  - P2/P3: minor UI/UX, low-risk edges
- Type:
  - smoke: minimal core checks
  - regression: everything else
- Tags must be meaningful (UI/API/Mobile/Web/Data/Security/Performance/Observability)

Output ONLY valid JSON using this schema:
{
  "feature": {"name":"Order System", "scope":"state-machine-first"},
  "testcases":[
    {
      "id":"TC-ORDER-001",
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

STATE_MACHINE_JSON:
{{STATE_MACHINE_JSON}}

RULE_MATRIX_JSON:
{{RULE_MATRIX_JSON}}

API_CONTRACT_DOC:
{{API_CONTRACT_DOC}}

RULES_DOC:
{{RULES_DOC}}

KB_GLOSSARY:
{{KB_GLOSSARY}}

KB_COMMON_RULES:
{{KB_COMMON_RULES}}

KB_BUG_PATTERNS:
{{KB_BUG_PATTERNS}}