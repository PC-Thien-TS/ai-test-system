# ADAPTER_VALIDATION_GUIDE

## Why Adapter Validation Is Needed
The platform now supports multiple project adapters.  
Validation ensures every adapter is:
- contract-compliant
- loader-resolvable
- structurally sane
- compatible with core intelligence smoke paths

This prevents weak scaffolds from silently breaking release/rerun/orchestration workflows.

## Validator Entry Point
Run from repo root:

```powershell
python validate_project_adapter.py --name rankmate
python validate_project_adapter.py --name ecommerce_alpha
```

Optional flags:
- `--strict`: escalate warnings to failure
- `--ci`: CI fail-fast behavior on contract/structural violations
- `--verbose`: print all check details
- `--json`: print machine-readable payload

## Output Artifacts
Validator writes:
- `adapter_validation_report.json`

This JSON is CI-consumable and includes:
- contract checks
- loader checks
- structure checks
- core smoke checks
- warnings/errors
- readiness recommendations

## Check Categories
1. **Contract validation**
   - required adapter methods exist and are callable
   - flow/suite/defect/risk/blocker hooks return valid structures
2. **Loader validation**
   - `AI_TESTING_ADAPTER=<name>` resolves requested adapter
3. **Structural validation**
   - non-empty flow and suite registries
   - release-critical flow presence
   - flow/intents consistency
   - defect family shape
   - changed-file mapping signal
4. **Core smoke validation**
   - regression orchestrator plan build
   - change-aware trigger dry-run execution
   - release gate payload compatibility build

## Validation Status Semantics
- `pass`
  - structurally valid and no warnings
- `pass_with_warnings`
  - usable but still includes placeholders/incomplete onboarding content
- `fail`
  - contract or compatibility is broken and onboarding is not safe

## Interpreting Warnings
Common warnings:
- suite paths missing on disk (scaffold placeholders)
- sample defect families still present (`DF-SAMPLE-*`)
- empty/project-generic `build_defect_families`
- weak/empty change mapping signal

Warnings do not always block onboarding, but they indicate low production readiness.

## Strict Mode
`--strict` converts warning debt into blocking status.  
Use strict mode for mature adapters before production onboarding gates.

## CI Usage Pattern
Recommended CI command:

```powershell
python validate_project_adapter.py --name <adapter_name> --ci
```

Behavior:
- fail fast for critical contract/structure violations
- keep checks lightweight (no full product regression run)
- preserve warning visibility in JSON output

## After Scaffold Generation
For a newly generated adapter:
1. Run validator in default mode to confirm structural compatibility.
2. Address warnings (suite paths, sample defect families, mapping rules).
3. Re-run in strict mode:

```powershell
python validate_project_adapter.py --name <adapter_name> --strict
```

4. Promote adapter only after strict mode is clean or warning debt is accepted intentionally.

