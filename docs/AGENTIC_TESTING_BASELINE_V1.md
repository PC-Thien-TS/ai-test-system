# Agentic Testing Platform v1.2 Baseline

## 1. Executive summary

This document captures the current v1.2 Agentic Testing baseline on `main`.

The platform has expanded beyond the original QA Platform v1.0 baseline into a deterministic analysis and draft-generation layer for:

- requirement ingestion
- test-case generation
- pytest script drafting
- locator self-healing suggestions
- root cause analysis
- bug-report draft generation
- mobile evidence and mobile failure classification
- reusable end-to-end flows
- agentic decision routing

This baseline is intentionally safe and bounded. It does not execute generated scripts, modify source files, create Jira tickets, or call LLMs as part of the new agentic flows.

## 2. Relationship with V1_BASELINE.md

[V1_BASELINE.md](C:/Users/PC-Thien/ai_test_system/docs/V1_BASELINE.md:1) remains the historical QA Platform v1.0 snapshot.

That v1.0 document describes the earlier deterministic QA pipeline centered on:

- decision policy
- failure memory
- self-healing rerun behavior
- dashboard snapshot generation
- notification hooks

This document is different in scope. It describes the newer v1.2 Agentic Testing baseline now present in source. It should be read as an extension of the platform rather than a replacement for the historical v1.0 record.

## 3. Current architecture

The current architecture is layered and additive.

### Historical QA platform foundation

- deterministic pipeline orchestration
- decision policy and release evaluation
- failure memory
- self-healing rerun support
- dashboard snapshot support
- notification hook support

### Requirement and generation layer

- Requirement Ingestion normalizes markdown, SRS-like text, and user-story text into structured requirement JSON.
- Test Case Generator derives deterministic structured test cases from normalized requirements.
- Pytest Script Generator converts generated test cases into safe pytest API script skeletons.

### Failure analysis layer

- Locator Self-Healing classifies locator-related failures and produces evidence-backed locator suggestions.
- Root Cause Analysis classifies failure context into high-level root-cause categories.
- Bug Report Draft Generator converts RCA plus evidence into structured bug-report drafts and markdown.

### Mobile analysis layer

- Mobile Run Service produces bounded exploration artifacts.
- Mobile API Route exposes mobile exploration through HTTP.
- Mobile Orchestrator Adapter maps mobile exploration into a platform-style result shape.
- Mobile Evidence Adapter converts artifacts and orchestrator results into structured evidence.
- Mobile Failure Classifier maps mobile evidence into mobile failure intelligence.

### Flow orchestration layer

- End-to-End AI Testing Flow composes the requirement, failure, and mobile modules into reusable deterministic flows.
- Agentic Testing Decision Loop selects which safe flow to run from available inputs in either `plan_only` or `draft_artifacts` mode.

## 4. Completed capabilities

- Mobile policy compatibility
- MobileRunService
- Mobile API Route
- Mobile Orchestrator Adapter
- Mobile Evidence Adapter
- Mobile Failure Classifier
- Requirement Ingestion
- Test Case Generator
- Pytest Script Generator
- Locator Self-Healing
- Root Cause Analysis
- Bug Report Draft Generator
- End-to-End AI Testing Flow
- Agentic Testing Decision Loop

## 5. Supported flows

### Requirement -> Test Cases -> Pytest Script Draft

Input:

- raw requirement text
- optional source metadata

Flow:

- `ingest_requirement()`
- `generate_test_cases()`
- `generate_pytest_script()`

Output:

- normalized requirement
- generated test cases
- generated pytest script draft
- metadata and warnings

### Failure -> RCA -> Bug Report Draft

Input:

- failure context
- optional locator-healing result
- optional evidence

Flow:

- `analyze_root_cause()`
- `generate_bug_report()`

Output:

- root-cause classification
- bug-report draft
- metadata

### Mobile Run -> Evidence -> Mobile Failure -> RCA -> Bug Report Draft

Input:

- mobile run artifact
- or mobile orchestrator result shape

Flow:

- `collect_mobile_exploration_evidence()`
- `classify_mobile_failure()`
- `analyze_root_cause()`
- `generate_bug_report()`

Output:

- mobile evidence
- mobile failure intelligence
- root cause
- bug-report draft

### Agentic Decision Loop

Input can include:

- `requirement_text`
- `failure_context`
- `mobile_artifact`
- `locator_failure_payload`
- optional `mode`

The decision loop can select:

- `INGEST_REQUIREMENT`
- `GENERATE_TEST_CASES`
- `GENERATE_SCRIPT`
- `ANALYZE_FAILURE`
- `SUGGEST_LOCATOR_HEALING`
- `GENERATE_BUG_REPORT`
- `ANALYZE_MOBILE_FAILURE`
- `SKIP_WITH_REASON`

Modes:

- `plan_only`: return selected actions, skipped actions, trace, and warnings without generating artifacts
- `draft_artifacts`: run only safe draft-producing flows and return generated artifacts

## 6. Safety boundaries

The v1.2 Agentic Testing baseline is intentionally bounded.

- No generated script execution is performed by the new agentic or flow modules.
- No Jira or other external API calls are performed by the new agentic baseline flows.
- No automatic code or test patching is performed.
- No automatic source-file modification is performed.
- No LLM-driven planning or expansion is required in the v1.2 baseline flows.

These boundaries keep the baseline deterministic, reviewable, and safe to tag as a draft-generation and analysis layer.

## 7. Test verification summary

Focused baseline test coverage for the Agentic Testing baseline totals 95 passed tests across the dedicated module slices referenced during baseline validation.

That focused verification covers:

- mobile execution and mobile analysis slices
- requirement ingestion
- test-case generation
- pytest script generation
- locator self-healing
- root cause analysis
- bug-report draft generation
- end-to-end AI testing flows
- agentic testing decision routing

## 8. Known limitations

- The new agentic baseline is deterministic only and does not use LLM reasoning.
- Generated pytest scripts are drafts only and are not executed by the agentic flow.
- Bug-report generation creates drafts only and does not create Jira tickets.
- Mobile evidence is primarily structured data and text, not richer runtime media.
- The new flows are not yet integrated into a broader run registry for traceability.
- Artifact persistence for the new flow outputs is still limited.
- Dashboard integration for the new agentic outputs is not yet in place.
- Learning memory is not yet connected to the new agentic decisions.

## 9. Recommended next roadmap

### Run registry integration

Persist requirement, failure, mobile, and agentic flow runs behind stable run identifiers.

### Artifact persistence

Persist normalized requirements, test cases, script drafts, RCA outputs, and bug-report drafts to stable artifact storage.

### Dashboard integration

Expose the new AI and agentic artifacts in dashboard views without changing the deterministic contracts.

### Controlled script execution

Add an explicit opt-in execution layer for generated pytest scripts with sandboxing and policy gates.

### Jira API integration

Add a controlled transport layer that can convert approved bug-report drafts into real Jira tickets.

### LLM-assisted expansion

Add optional LLM support for requirement enrichment, scenario expansion, and triage assistance on top of the deterministic baseline.

### Real Appium/device evidence

Extend mobile evidence collection to include screenshots, richer logs, and real device or emulator evidence.

### Learning memory integration

Connect the new flows to historical failure memory so agentic decisions can reuse prior failures, known defects, and prior remediation outcomes.
