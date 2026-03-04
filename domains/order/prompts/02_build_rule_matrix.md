You are a strict QA designing a rules matrix for an Order State Machine.

Given STATE_MACHINE_JSON:
- Create a transition rule matrix.
- Include BOTH allowed and disallowed transitions for coverage.
- For disallowed transitions, set allowed=false and explain reason.
- Add action_name for each transition (e.g., CREATE_ORDER, CREATE_PAYMENT, WEBHOOK_SUCCESS, MERCHANT_ACCEPT, USER_CANCEL, JOB_EXPIRE, MERCHANT_STATUS_UPDATE).
- Output ONLY valid JSON.

OUTPUT JSON:
{
  "matrix": [
    {
      "from": "STATE",
      "action": "ACTION_NAME",
      "actor": "user|merchant|admin|system|UNKNOWN",
      "allowed": true,
      "to": "STATE|UNCHANGED|UNKNOWN",
      "guards": ["..."],
      "reason": "..."
    }
  ],
  "coverage_notes": ["..."],
  "high_risk_rules": ["..."]
}

STATE_MACHINE_JSON:
{{STATE_MACHINE_JSON}}