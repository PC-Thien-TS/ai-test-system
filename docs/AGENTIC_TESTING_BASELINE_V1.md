# Agentic AI Testing Platform v1.2 Baseline

## 1. Executive summary

This document freezes the current Agentic AI Testing Platform baseline after completion of the deterministic roadmap through Agentic Testing v1.

The platform can now:

- normalize raw requirements into structured requirement JSON
- generate deterministic test cases from normalized requirements
- generate safe pytest API script skeletons without executing them
- classify UI locator failures and suggest safe replacement locators
- analyze generic and mobile failure signals into root-cause categories
- generate structured bug-report drafts without creating real tickets
- run thin end-to-end testing flows across the existing modules
- make deterministic agent-style decisions about which flow to run based on available inputs

This is a draft-generation and analysis baseline, not yet a live autonomous execution platform.

## 2. Current architecture

The current architecture is layered and additive.

### Input and normalization layer

- Requirement Ingestion v1 converts markdown, SRS-style text, or user-story text into normalized requirement JSON.
- Mobile adapters convert mobile service outputs into platform-style results and structured evidence.

### Generation layer

- AI Test Case Generator v1 derives deterministic structured test cases from normalized requirements.
- Automation Script Generator v1 converts those test cases into safe pytest API skeletons.

### Analysis and intelligence layer

- Locator Self-Healing v1 classifies locator-related failures and produces safe locator recommendations.
- Root Cause Analysis v1 maps failure signals into high-level root-cause categories.
- Mobile Failure Intelligence v1 classifies mobile exploration failures from evidence and artifact signals.
- Auto Bug Report Draft v1 formats RCA plus evidence into structured bug-report drafts and markdown.

### Flow orchestration layer

- End-to-End AI Testing Flow v1 composes the existing modules into reusable deterministic flows.
- Agentic Testing v1 adds a safe decision loop that selects which existing flow to run in `plan_only` or `draft_artifacts` mode.

### Mobile execution foundation

- Mobile policy compatibility
- Mobile Run Service v1
- Mobile API Route v1
- Mobile Orchestrator Adapter v1
- Mobile Evidence Collector v1
- Mobile Failure Intelligence v1

## 3. Completed capabilities

- Requirement-to-structured-JSON normalization
- Deterministic requirement-to-test-case generation
- Deterministic test-case-to-pytest-script generation
- Locator failure classification with evidence-backed suggestions
- Generic RCA over API, environment, flaky, locator, and mobile signals
- Structured bug-report draft generation with markdown output
- Mobile exploration artifact normalization into evidence
- Mobile failure classification from artifact and evidence signals
- Reusable deterministic requirement, failure, and mobile flows
- Agentic decision selection over requirement, failure, mobile, and locator inputs

## 4. Supported flows

### Requirement to script

`requirement_text` -> `ingest_requirement()` -> `generate_test_cases()` -> `generate_pytest_script()`

Output includes:

- `normalized_requirement`
- `test_cases`
- `generated_script`
- `metadata`
- `warnings`

### Failure to bug report

`failure_context` -> optional locator healing -> `analyze_root_cause()` -> `generate_bug_report()`

Output includes:

- `root_cause`
- `bug_report`
- `metadata`

### Mobile failure to bug report

`mobile_artifact` or mobile orchestrator result -> `collect_mobile_exploration_evidence()` -> `classify_mobile_failure()` -> `analyze_root_cause()` -> `generate_bug_report()`

Output includes:

- `mobile_evidence`
- `mobile_failure`
- `root_cause`
- `bug_report`

### Agentic deterministic loop

`run_agentic_testing(...)` selects actions from:

- `INGEST_REQUIREMENT`
- `GENERATE_TEST_CASES`
- `GENERATE_SCRIPT`
- `ANALYZE_FAILURE`
- `SUGGEST_LOCATOR_HEALING`
- `GENERATE_BUG_REPORT`
- `ANALYZE_MOBILE_FAILURE`
- `SKIP_WITH_REASON`

Modes:

- `plan_only`: returns selected actions, trace, warnings, and skip decisions without generating artifacts
- `draft_artifacts`: runs only safe draft-producing flows and returns artifacts

## 5. Test verification summary

The current baseline is covered by focused deterministic test slices established across the completed roadmap:

- `tests/mobile`: 31 passed
- `tests/test_mobile_api.py`: 3 passed
- `tests/test_mobile_orchestrator_adapter.py`: 4 passed
- `tests/test_mobile_evidence_adapter.py`: 5 passed
- `tests/test_mobile_failure_classifier.py`: 6 passed
- `tests/test_requirement_ingestion.py`: 4 passed
- `tests/testcase_generator.py`: 5 passed
- `tests/test_script_generator.py`: 5 passed
- `tests/test_locator_self_healing.py`: 6 passed
- `tests/test_root_cause_analysis.py`: 8 passed
- `tests/test_bug_report_generator.py`: 6 passed
- `tests/test_ai_testing_flow.py`: 5 passed
- `tests/test_agentic_testing.py`: 7 passed

These tests validate the baseline as a deterministic analysis-and-draft-generation platform rather than a live execution platform.

## 6. Current limitations

- No LLM-assisted planning, ambiguity resolution, or expansion is used yet.
- Generated pytest scripts are skeletons only and are not executed by the platform.
- No real Jira ticket creation occurs.
- No automatic editing of test code or application code occurs.
- Agentic Testing v1 is a decision layer only; it does not introduce autonomous remediation.
- Mobile evidence is text/data oriented only; screenshots, videos, and device-native artifacts are not required in v1.
- Registry and long-lived persistence are still minimal and not fully integrated into the new agentic flows.
- Dashboard integration for the new AI/agentic flows is not wired yet.

## 7. Safety boundaries

- No external API calls are required for the v1.2 baseline flows.
- No generated scripts are executed by the platform in this baseline.
- No source files or test files are modified automatically.
- No real Jira tickets are created.
- No uncontrolled self-healing or code patching is performed.
- Agentic mode is deterministic and rule-based, not LLM-driven.
- Mobile flows can operate in mock mode and do not require a real Appium server for baseline coverage.

## 8. Recommended next roadmap

### Run registry integration

Persist agentic flow runs, requirement flows, and failure-analysis outputs behind a stable run identifier for traceability.

### Artifact persistence

Persist generated requirements, test cases, scripts, RCA outputs, and bug drafts into stable storage paths instead of returning them only in-memory.

### Dashboard integration

Expose the requirement, failure, mobile, and agentic flow artifacts in dashboard views without changing the deterministic contracts.

### Controlled script execution

Add an opt-in execution layer for generated pytest scripts with explicit safety gates, sandboxing, and isolated environments.

### Jira API integration

Add a controlled transport layer that can turn bug-report drafts into real Jira tickets only after explicit enablement and validation.

### LLM-assisted expansion

Layer optional LLM support on top of the deterministic baseline for requirement enrichment, negative-case expansion, triage explanations, and stronger planning.

### Real Appium/device evidence

Extend the mobile evidence path to support screenshots, video, richer driver logs, and real device or emulator evidence capture.

### Learning memory integration

Integrate failure memory and recurrence learning with the new agentic flows so decisions can reuse prior outcomes, known defects, and remediation history.
