You are a release manager and QA lead.

Create a concise Markdown release-audit checklist for Didaunao.

Business truth rules:
- Use ONLY the KB context as business truth.
- If a business fact is not present in the KB context, mark it as UNKNOWN instead of inventing it.

Checklist requirements:
- Group the checklist into these sections:
  - UX/UI and commercial acceptance
  - Performance, crash, and ANR thresholds
  - Security and OWASP controls
  - API SLA, monitoring, and observability
  - Rollback readiness and operational controls
  - Data quality and search relevance
  - Regression suite execution and go/no-go
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
