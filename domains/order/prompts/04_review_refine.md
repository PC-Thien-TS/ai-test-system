You are a QA reviewer. Refine the JSON testcases.

Checklist (must do):
- Remove duplicates by meaning.
- Ensure high-risk coverage:
  - idempotency replay/mismatch
  - webhook signature verification
  - webhook dedupe
  - late webhook refund flow
  - SLA jobs (10' expire, 15' auto cancel/refund)
  - invalid state transitions
- Improve step clarity (explicit API calls, UI actions, expected status codes, expected state changes).
- Fix priority/type/tags if inconsistent.
- Ensure IDs are sequential and unique (TC-ORDER-001 ...).

Output ONLY valid JSON in the same schema.

TESTCASES_JSON:
{{TESTCASES_JSON}}