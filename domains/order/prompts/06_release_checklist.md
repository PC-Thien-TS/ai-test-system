You are a QA lead. Create a release checklist in Markdown for Order system.

Must include sections:
1) Smoke checklist (10–20 items)
2) Regression checklist groups:
   - Order creation & snapshot
   - Payment attempt & expiry
   - Webhook (signature/dedupe/late)
   - Merchant operations (accept/reject/status chain)
   - Cancellation & refund
   - SLA jobs (10', 15')
   - Admin/ops observability checks
3) Data verification checklist (DB/log fields, request_id/order_id correlation)
4) Monitoring checklist (alerts, dashboards, runbook readiness)
5) Risks & rollback notes

STATE_MACHINE_JSON:
{{STATE_MACHINE_JSON}}

REGRESSION_JSON:
{{REGRESSION_JSON}}

TESTCASES_REFINED_JSON:
{{TESTCASES_REFINED_JSON}}