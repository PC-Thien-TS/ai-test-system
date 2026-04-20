# Decision Policy Engine v2

## Purpose
`DecisionPolicyEngine` is the deterministic decision layer between:

- Failure Memory Engine outputs
- self-healing action execution
- CI smart regression gate
- release scoring and dashboarding

It converts normalized failure + memory context into operational decisions such as rerun, suppression, escalation, manual investigation, and release blocking.

## Package

- `orchestrator/decision/domain/models.py`
  - input/output contracts
  - enums for decisions and strategies
  - governance flags and profile model
- `orchestrator/decision/domain/profiles.py`
  - builtin policy profiles and env overrides
- `orchestrator/decision/domain/scoring.py`
  - deterministic score computation
- `orchestrator/decision/domain/rules.py`
  - hard rules and strategy derivation
- `orchestrator/decision/application/engine.py`
  - end-to-end policy evaluation
- `orchestrator/decision/integration/*`
  - CI/self-healing/release bridges

## Deterministic Decision Signals

The engine evaluates:

- severity
- confidence (triage + memory combined)
- memory resolution type (`EXACT_MATCH`, `SIMILAR_MATCH`, `AMBIGUOUS_MATCH`, `NEW_MEMORY`)
- recurrence
- flaky signal
- best action effectiveness
- release criticality and protected path context
- governance flags

## Supported Decisions

- `NO_ACTION`
- `RERUN`
- `RERUN_WITH_STRATEGY`
- `SUPPRESS_KNOWN_FLAKY`
- `ESCALATE`
- `MANUAL_INVESTIGATION`
- `BLOCK_RELEASE`
- secondary candidate signals:
  - `BUG_CANDIDATE`
  - `INCIDENT_CANDIDATE`

## Profiles

- `conservative`
- `balanced` (default)
- `aggressive`
- `release_hardening`
- `flaky_tolerant`

Env overrides supported:

- `DECISION_POLICY_PROFILE`
- `DECISION_BLOCK_THRESHOLD`
- `DECISION_ESCALATE_THRESHOLD`
- `DECISION_RERUN_THRESHOLD`
- `DECISION_AMBIGUITY_PENALTY`
- `DECISION_CRITICAL_RECURRENCE_BLOCK_COUNT`
- `DECISION_RELEASE_CRITICAL_BOOST`
- `DECISION_MIN_ACTION_EFFECTIVENESS_FOR_RERUN`
- `DECISION_ALLOW_AUTO_RERUN`
- `DECISION_ALLOW_AUTO_SUPPRESS`
- `DECISION_ALLOW_AUTO_BLOCK_RELEASE`
- `DECISION_REQUIRE_MANUAL_REVIEW_ON_CRITICAL`
- `DECISION_ALLOW_BUG_CANDIDATE`
- `DECISION_ALLOW_INCIDENT_CANDIDATE`

## Integration Pattern

1. Triage/Memory resolves failure context and best historical action.
2. Build `DecisionPolicyInput`.
3. Call `DecisionPolicyEngine.evaluate(...)`.
4. Feed output:
   - CI gate via `build_ci_decision_hint(...)`
   - self-healing via `build_self_healing_instruction(...)`
   - release scoring via `build_release_policy_signal(...)`

## Minimal Example

```python
from orchestrator.decision import DecisionPolicyEngine, DecisionPolicyInput

engine = DecisionPolicyEngine(default_profile_name="balanced")
result = engine.evaluate(
    DecisionPolicyInput(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        severity="high",
        confidence=0.86,
        memory_resolution_type="EXACT_MATCH",
        memory_confidence=0.90,
        occurrence_count=4,
        release_critical=True,
        best_action="retry_with_backoff",
        best_action_effectiveness=0.68,
    )
)
```

