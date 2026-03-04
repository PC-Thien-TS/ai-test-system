You are a careful QA/BA analyst.

Input includes:
- STATE_MACHINE_DOC (human draft)
- API_CONTRACT_DOC (human draft)
- RULES_DOC (human draft)

Task:
1) Normalize order states list (unique, uppercase).
2) Extract transitions with fields: from, to, actor, condition, source (doc name).
3) Identify unknowns / ambiguities and list them explicitly. DO NOT invent missing details.
4) Output ONLY valid JSON.

OUTPUT JSON SCHEMA:
{
  "states": ["..."],
  "transitions": [
    {
      "from": "STATE",
      "to": "STATE",
      "actor": "user|merchant|admin|system|UNKNOWN",
      "condition": "string",
      "source": "state_machine|api_contract|rules"
    }
  ],
  "terminal_states": ["..."],
  "invariants": ["..."],
  "unknowns": ["..."]
}

STATE_MACHINE_DOC:
{{STATE_MACHINE_DOC}}

API_CONTRACT_DOC:
{{API_CONTRACT_DOC}}

RULES_DOC:
{{RULES_DOC}}