# ADAPTER_SDK_GUIDE

## Overview
The AI Testing Platform now separates:
- **Core intelligence engines** (release gate, rerun, healing, orchestrator, dashboard)
- **Project adapters** (flows, suites, defect families, change mapping, risk/blocker rules)

Use the adapter SDK bootstrap to onboard new projects quickly and consistently.

## When To Create A New Adapter
Create a new adapter when:
- the product has different core flows from RankMate
- suite structure and defect semantics differ
- release-critical risk logic should be project-specific

Keep RankMate as reference implementation.

## Bootstrap Command
From repo root:

```powershell
python create_project_adapter.py --name ecommerce_alpha
python create_project_adapter.py --name booking_plus --profile booking
python create_project_adapter.py --name saas_demo --profile saas
```

Optional flags:
- `--dry-run`: show planned files without writing
- `--force`: overwrite scaffold files if adapter directory already exists

## Supported Profiles
- `generic` (default)
- `ecommerce`
- `saas`
- `booking`

Profiles seed initial flow definitions and keyword mapping.

## Generated Files
The bootstrap generates:
- `orchestrator/adapters/<name>/__init__.py`
- `orchestrator/adapters/<name>/adapter.py`
- `orchestrator/adapters/<name>/flow_registry.py`
- `orchestrator/adapters/<name>/suite_registry.py`
- `orchestrator/adapters/<name>/defect_registry.py`
- `orchestrator/adapters/<name>/change_mapping.py`
- `orchestrator/adapters/<name>/risk_rules.py`
- `orchestrator/adapters/<name>/blocker_rules.py`
- `orchestrator/adapters/<name>/README.md`

## Template Source
Templates are stored in:
- `orchestrator/adapters/templates/`

You can update template files to improve all future scaffolds.

## How To Customize A Generated Adapter
1. Replace placeholder suite paths with real project test files.
2. Adjust flow IDs and release-critical flows in `flow_registry.py`.
3. Replace sample defect families with real project families.
4. Extend change mapping keyword rules for your repository structure.
5. Tune scoring and risk rules in `risk_rules.py`.
6. Implement project-specific `build_defect_families(...)` in `adapter.py`.

## Activation
Set active adapter at runtime:

```powershell
$env:AI_TESTING_ADAPTER="ecommerce_alpha"
python ai_regression_orchestrator.py --intent full_app_fast_regression --mode fast
```

Adapter loader defaults to `rankmate` if `AI_TESTING_ADAPTER` is missing or unknown.

## Validation Checklist For New Adapter
1. Dry-run scaffold:
   - `python create_project_adapter.py --name <adapter> --profile <profile> --dry-run`
2. Generate scaffold:
   - `python create_project_adapter.py --name <adapter> --profile <profile>`
3. Validate module import:
   - `python -c "import os; os.environ['AI_TESTING_ADAPTER']='<adapter>'; from orchestrator.adapters import get_active_adapter; print(get_active_adapter().get_adapter_id())"`
4. Run orchestrator in plan mode and review generated flow/suite plan.

## Notes
- Generated adapters are **contract-compliant starter scaffolds**.
- They are not production-ready until project-specific suite and defect mappings are configured.

