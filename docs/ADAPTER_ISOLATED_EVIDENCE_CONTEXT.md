# ADAPTER_ISOLATED_EVIDENCE_CONTEXT

## Why This Exists

The platform was adapter-aware at the flow/risk mapping layer, but evidence artifacts were still effectively shared at repo root.  
That caused cross-project leakage where a scaffold adapter (for example `ecommerce_alpha`) could inherit RankMate release state (`block_release`, score `57`) even without local evidence.

This document defines the v1 isolation model that prevents cross-adapter evidence contamination.

## Isolation Model

Adapter-local artifacts are stored under:

`artifacts/adapter_evidence/<adapter_id>/`

Example:

- `artifacts/adapter_evidence/rankmate/release_decision.json`
- `artifacts/adapter_evidence/ecommerce_alpha/release_decision.json`
- `artifacts/adapter_evidence/<adapter_id>/dashboard_snapshot.json`
- `artifacts/adapter_evidence/<adapter_id>/defect_cluster_report.json`
- `artifacts/adapter_evidence/<adapter_id>/autonomous_rerun_plan.json`
- `artifacts/adapter_evidence/<adapter_id>/qa_snapshot_history.json`
- `artifacts/adapter_evidence/<adapter_id>/reports/*.md`

All adapter-aware engines now resolve artifact paths through `AdapterEvidenceContext`:

- `release_decision_gate.py`
- `ai_qa_lead_dashboard.py`
- `autonomous_rerun_loop.py`
- `self_healing_loop.py`
- `ai_regression_orchestrator.py`
- `ci_smart_regression_gate.py`
- `ai_change_aware_regression_trigger.py`
- `validate_project_adapter.py`

## Bootstrap / Insufficient Evidence Semantics

If an adapter has no local evidence:

- the system **must not** read another adapter's artifacts
- release state is emitted as `insufficient_evidence`
- CI gate returns caution-style bootstrap semantics (warning), not inherited fail from another project

This applies in particular to scaffold adapters such as `ecommerce_alpha`.

## RankMate Backward Compatibility

RankMate remains the reference adapter and preserves legacy compatibility:

- local writes go to `artifacts/adapter_evidence/rankmate/...`
- outputs are mirrored to legacy root/report paths for existing workflows and demos
- fallback to legacy root artifacts is allowed only for `rankmate`

No cross-adapter fallback is allowed.

## Practical Outcomes

After isolation:

- `rankmate` retains current real release intelligence.
- non-rankmate adapters produce local bootstrap states until they generate local evidence.
- CI and dashboard decisions become multi-project-safe and auditable.
