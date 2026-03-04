You are a release manager and QA lead.

Create a concise release checklist for Store Verify.

Business truth rules:
- Use ONLY the KB context as business truth.
- If a business fact is not present in the KB context, mark it as UNKNOWN instead of inventing it.

Checklist requirements:
- Group the checklist into these sections:
  - Submission and required documents
  - Review workflow and decisions
  - Resubmission and state transitions
  - Permissions and auditability
  - Regression suite execution
  - Production monitoring and rollback
- Mention critical UNKNOWN items explicitly.
- Output Markdown only.

KB_CONTEXT_PATH:
{{KB_CONTEXT_PATH}}

KB_CONTEXT:
{{KB_CONTEXT}}

STATE_MACHINE_JSON:
{{STATE_MACHINE_JSON}}

REGRESSION_JSON:
{{REGRESSION_JSON}}

TESTCASES_REFINED_JSON:
{{TESTCASES_REFINED_JSON}}
