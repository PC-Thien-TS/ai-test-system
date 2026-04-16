# ADAPTER_ARCHITECTURE_VNEXT

## Why This Refactor Was Needed
The QA intelligence stack proved strong in RankMate pilot execution, but orchestration logic was still embedded with RankMate-specific flows, suite mappings, defect families, and blocker assumptions.  
This refactor separates platform engines from project-specific domain knowledge so the same engines can run across multiple products.

## Core vs Adapter Responsibilities
### Core platform intelligence
- `release_decision_gate.py`
- `autonomous_rerun_loop.py`
- `self_healing_loop.py`
- `ai_regression_orchestrator.py`
- `ai_change_aware_regression_trigger.py`
- `ai_qa_lead_dashboard.py`

These now load an active adapter and consume adapter contracts for flow/suite/risk/defect mapping.

### Project adapters
Path: `orchestrator/adapters/`

- Base contract and models:
  - `orchestrator/adapters/base/adapter_contract.py`
  - `orchestrator/adapters/base/models.py`
- Adapter loader:
  - `orchestrator/adapters/loader.py`
- RankMate implementation (Adapter #1):
  - `orchestrator/adapters/rankmate/adapter.py`
  - `orchestrator/adapters/rankmate/flow_registry.py`
  - `orchestrator/adapters/rankmate/suite_registry.py`
  - `orchestrator/adapters/rankmate/defect_registry.py`
  - `orchestrator/adapters/rankmate/change_mapping.py`
  - `orchestrator/adapters/rankmate/risk_rules.py`
  - `orchestrator/adapters/rankmate/blocker_rules.py`

## RankMate as Adapter #1
RankMate adapter currently owns:
- Product flow registry:
  - Auth Foundation
  - Search & Discovery
  - Order Core
  - Merchant Handling
  - Admin Consistency
  - Payment Integrity
- Suite registry for rerun and orchestrator mapping
- Known defect family model:
  - `DF-STORE-NEGATIVE-500`
  - `DF-MERCHANT-STALE-TERMINAL-MUTATION`
  - `DF-STRIPE-WEBHOOK-ENV-BLOCKER`
  - `DF-MERCHANT-SEED-COVERAGE-GAP`
- Changed-file to flow mapping and risk mapping
- Release scoring rule defaults and thresholds
- Blocker classification helpers

## Active Adapter Selection
Set adapter by environment variable:

`AI_TESTING_ADAPTER=rankmate`

Fallback behavior:
- Missing or unknown adapter id defaults to `rankmate`.

Loader entry:
- `orchestrator/adapters/loader.py`

## Modules Made Adapter-Aware
- `ai_regression_orchestrator.py`
  - Uses adapter flow registry, flow order, intents/modes, risk-to-flow mapping.
- `ai_change_aware_regression_trigger.py`
  - New script; uses adapter changed-file mapping to select product flows/suites.
- `release_decision_gate.py`
  - Uses adapter scoring config and defect-to-flow mapping metadata.
- `autonomous_rerun_loop.py`
  - Uses adapter suite catalog and blocker classification integration.
- `self_healing_loop.py`
  - Uses adapter defect family builder (project-specific family logic moved out of core loop).
- `ai_qa_lead_dashboard.py`
  - Uses adapter family-to-flow inference for risk flow labeling and emits adapter metadata.

## Optional Adapter #2
A minimal sample adapter is included to prove multi-project readiness:
- `orchestrator/adapters/sample_ecommerce/adapter.py`

It is intentionally lightweight and non-production, but validates that the platform is no longer structurally RankMate-only.

## How to Add Adapter #2 (Real Project)
1. Create `orchestrator/adapters/<project_id>/`.
2. Implement `ProjectAdapter` contract in `adapter.py`.
3. Define project flow/suite/defect/risk/blocker registries.
4. Register adapter id in `orchestrator/adapters/loader.py`.
5. Set `AI_TESTING_ADAPTER=<project_id>` and run existing core scripts unchanged.

