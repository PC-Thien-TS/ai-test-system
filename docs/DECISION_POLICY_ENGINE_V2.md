# Decision Policy Engine v2

## Purpose

Deterministic policy engine that turns memory + triage + recurrence + severity + execution context into operational decisions.

Layering:

- Storage: persistence
- Failure Memory Engine: learned failure memory
- Decision Policy Engine: deterministic decision policy
- Self-healing loop: executes policy instructions

## Inputs

`DecisionPolicyInput` includes:

- adapter/project/run context
- severity/confidence
- memory resolution type
- recurrence/occurrence
- flaky signal
- best action + effectiveness
- release-critical/protected-path flags
- governance flags

## Outputs

`DecisionPolicyResult` includes:

- primary decision
- strategy
- rationale
- decision score
- release/rerun/escalation/manual flags
- bug/incident candidate flags
- owner hints
- explainable score components

## Integration Flow

1. Memory Engine resolves failure and returns memory context.
2. Decision Policy Engine evaluates deterministic rules and score.
3. Bridges convert result for:
   - CI gate (`build_ci_policy_hint`)
   - Self-healing (`build_self_healing_policy_instruction`)
   - Release scoring (`build_release_policy_signal`)

## Migration

1. After memory resolution, build `DecisionPolicyInput`.
2. Evaluate policy before self-healing actions.
3. Feed decision hint into CI smart gate and release scoring.
4. Persist decision distribution metrics for dashboard trend panels.
