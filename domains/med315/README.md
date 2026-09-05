# MED315 Full System Regression

This domain is the starting point for applying `ai-test-system` to MED315 healthcare release testing.

## Phase 1 scope

The first phase is intentionally human-in-the-loop. The AI system prepares and selects test coverage, while QC reviews and executes the tests.

### Goals

1. Maintain one reusable Full System Regression Master Suite.
2. Separate permanent core coverage from release-impact regression.
3. Use release branch/environment information to decide test depth.
4. Record known bug patterns so fixed defects become regression coverage.
5. Keep QC responsible for final PASS/FAIL and release sign-off.

## Test layers

### Tier 1 - Core Smoke

Mandatory critical flows that should be verified on every release candidate:

- Authentication and role access
- Patient search/create
- Patient reception
- Reception-to-doctor handoff
- Open examination
- Vital signs
- Diagnosis
- Service indication
- Prescription
- Save and reload
- Basic print validation
- Critical permission checks

### Tier 2 - Core Regression

Reusable functional coverage across the main MED315 modules:

- CRM / MiniCRM
- Examination
- Pharmacy / medicine
- Purchasing / warehouse
- Inventory transfer
- GDP transfer approval
- Return confirmation
- Price update
- Customer allocation
- Print / export
- Permission
- Cross-module data consistency

### Tier 3 - Release Impact Regression

Selected for each release from:

- changed frontend/backend modules
- Jira/work-item scope
- impacted APIs and workflows
- known defect patterns
- historical regression cases

## Environment policy

The current delivery flow contains four branches/environments:

- `DEV`: change analysis and developer-level checks
- `QA`: functional testing, bug retest, targeted regression
- `STAG`: full system testing and release-candidate regression
- `PROD`: non-destructive post-release validation only

See `release_policy.yaml` for the machine-readable policy.

## Current workflow

```text
Release scope / code diff
        +
MED315 Master Suite
        +
Known bug patterns
        |
        v
AI proposes test plan
        |
        v
QC reviews test plan
        |
        v
QC executes manual / automated tests
        |
        v
QC signs off release
```

## Files

- `master_suite.json`: reusable system test scenarios and priorities
- `release_policy.yaml`: testing depth by environment
- `knowledge_base/known_bug_patterns.md`: initial MED315 regression memory

## Phase 1 boundary

Not included yet:

- autonomous Playwright execution
- automatic Jira bug creation
- automatic release sign-off
- destructive PROD testing
- automatic code-diff mapping

These will be introduced gradually after the master suite is stable.