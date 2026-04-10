# ai_test_system

## v2.4.0 - Execution Depth Expansion

Version 2.4.0 significantly increases real execution depth across all built-in plugins and reduces fallback-only smoke behavior.

### Key Features

- **Plugin Execution Depth Metrics**: Added execution_depth_score, evidence_richness_score, and confidence_score to all plugins
- **Deeper Validation Layers**: Multi-step journeys, negative paths, retry/rollback, threshold calibration, grounding confidence, safety consistency, schema evolution, and anomaly heuristics
- **Enhanced Result Contracts**: Run and ProjectSummary models now include fallback_ratio and real_execution_ratio metrics
- **Plugin Maturity Trending**: Platform summary includes plugin maturity trend data
- **Upgraded Plugin Capabilities**:
  - web_playwright: Added multi_step_journeys, negative_path_testing, retry_rollback_validation, threshold_calibration
  - api_contract: Added multi_endpoint_journeys, negative_request_testing, retry_mechanism_validation, schema_evolution_detection, anomaly_heuristics
  - model_evaluation: Added multi_dataset_evaluation, negative_sample_testing, threshold_calibration, drift_detection
  - rag_grounding: Added multi_hop_grounding, negative_citation_testing, confidence_threshold_validation, grounding_confidence_scoring
  - llm_consistency: Added multi_turn_consistency, adversarial_input_testing, safety_consistency_validation, output_confidence_scoring
  - workflow_validator: Added multi_workflow_journeys, negative_state_testing, rollback_validation, state_consistency_checks
  - data_pipeline_validator: Added multi_stage_validation, negative_data_testing, anomaly_detection_heuristics, schema_evolution_tracking

### Plugin Maturity Before/After

| Plugin | Before Support Level | After Support Level | Before Depth Score | After Depth Score |
|--------|---------------------|---------------------|-------------------|-------------------|
| web_playwright | FULL | FULL | 0.0 | 0.85 |
| api_contract | FULL | FULL | 0.0 | 0.90 |
| model_evaluation | USABLE | FULL | 0.0 | 0.80 |
| rag_grounding | USABLE | FULL | 0.0 | 0.78 |
| llm_consistency | PARTIAL | USABLE | 0.0 | 0.70 |
| workflow_validator | FULL | FULL | 0.0 | 0.88 |
| data_pipeline_validator | PARTIAL | USABLE | 0.0 | 0.75 |

### Changed Files

- `orchestrator/models.py`: Added execution depth metrics to PluginMetadata, Run, ProjectSummary, PlatformSummary
- `orchestrator/compatibility.py`: Upgraded all built-in plugins with deeper capabilities and execution depth scores
- `orchestrator/platform_summary.py`: Updated report generation to calculate and include new metrics
- `api/app.py`: Bumped version to 2.4.0
- `dashboard/lib/types.ts`: Updated TypeScript types to match new backend models
- `tests/test_compatibility.py`: Added tests for plugin execution depth metrics
- `tests/test_models.py`: Added tests for Run and ProjectSummary execution depth metrics

## v2.2.0 - Dashboard UI + Query UX

Version 2.2.0 introduces a modern web dashboard for the Universal Testing Platform, built with Next.js, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, and Recharts.

### Dashboard Features

- **Platform Overview**: View platform-wide metrics including total projects, active projects, total runs, failing projects, flaky projects, quality gate overview, and plugin usage
- **Projects List**: Browse all projects with search, filter by product type, filter by gate result, and sorting
- **Project Detail**: View project metadata, summary, trend charts, flaky summary, compatibility, and latest runs
- **Runs Explorer**: Explore test runs across all projects with status, duration, timestamps, and artifacts
- **Plugin Catalog**: Browse available plugins with support level, capabilities, compatibility notes, and onboarding completeness

### Quick Start

1. Start the backend API:
   ```bash
   uvicorn api.app:app --reload
   ```

2. Install dashboard dependencies:
   ```bash
   cd dashboard
   npm install
   ```

3. Start the dashboard:
   ```bash
   npm run dev
   ```

4. Open your browser to `http://localhost:3000`

The dashboard will be available with interactive charts, real-time data fetching, and a clean, modern UI.

### Dashboard Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: Beautiful, accessible component library
- **TanStack Query**: Data fetching and state management
- **Recharts**: Chart library for data visualization
- **Lucide React**: Icon library

For detailed dashboard documentation, see [dashboard/README.md](dashboard/README.md).

---

## v2.1.0 - Platform API

Version 2.1.0 introduces a FastAPI-based Platform API with multi-tenant support, transforming the system from a CLI tool to a full testing platform.

### Platform API Features

- **FastAPI Backend**: RESTful API for managing projects, runs, and quality gates
- **Multi-tenant/Workspace Model**: Support for multiple workspaces with role-based access control
- **Project Registry**: File-based project storage with metadata and tags
- **Run Registry**: Track test runs with status, results, and trends
- **Plugin System**: Built-in plugin catalog with compatibility analysis
- **Dashboard-Ready Summaries**: Platform-wide and project-specific summaries for dashboards

### Quick Start

Start the API server:

```bash
uvicorn api.app:app --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### API Endpoints

**Health**
- `GET /health/` - Health check

**Projects**
- `GET /projects/` - List projects (supports workspace filtering)
- `POST /projects/` - Create a new project
- `GET /projects/{project_id}` - Get project details
- `POST /projects/{project_id}/run` - Trigger a test run

**Runs**
- `GET /projects/{project_id}/runs` - List runs for a project
- `GET /projects/{project_id}/summary` - Get project summary
- `GET /projects/{project_id}/trends` - Get trend data

**Platform**
- `GET /platform/summary` - Platform-wide summary
- `GET /platform/projects/latest` - Latest status for all projects

**Plugins**
- `GET /plugins/` - List available plugins
- `GET /plugins/{plugin_name}` - Get plugin details
- `GET /plugins/{plugin_name}/compatibility` - Analyze plugin compatibility

### Multi-tenant Support

Use headers to specify user context:

```
X-User-ID: user123
X-Workspace-ID: workspace456
X-User-Role: admin  # viewer, maintainer, or admin
```

### Initialize Platform from Existing Domains

To import existing domain-based configurations into the new platform:

```bash
python scripts/init_platform.py
```

This will:
- Import existing domains (order, store_verify, didaunao_release_audit) as projects
- Import existing output directories as runs
- Initialize the platform registry

### Backward Compatibility

All existing CLI flows remain unchanged:
- Domain-based manual flows (order, store_verify, didaunao_release_audit)
- KB-based workflows
- Orchestrator-based execution
- Validation scripts

The platform API layer is additive and does not replace existing functionality.

---

## Legacy Domain-Based Flows (v2.0 and earlier)

This repository now supports three manual domain flows plus the existing Order orchestrator path:

- `order`: legacy static-doc manual flow
- `store_verify`: local KB (RAG) manual flow
- `didaunao_release_audit`: local KB (RAG) manual flow for release self-inspection
- `order` orchestrator: `core.orchestrator.Orchestrator`

All run folders use the same canonical artifact filenames:

- `01_state_machine.json`
- `02_rule_matrix.json`
- `03_testcases_raw.json`
- `04_testcases_refined.json`
- `05_regression_suite.json`
- `06_release_checklist.md`

## Local KB Workflow

Use this for KB-enabled domains such as `store_verify` and `didaunao_release_audit`.

1. Put business docs in `requirements/<domain>/`.
2. Build the local KB index:
   - `python kb/build_kb.py --domain <domain>`
3. Optionally inspect retrieval:
   - `python kb/query_kb.py --domain <domain> --q "status transitions approve reject" --k 5`
4. Run the manual pipeline:
   - `python scripts/run_domain_manual.py --domain <domain> --run-id <run_id>`

The KB scripts are fully local:

- no OpenAI API keys are required
- no network calls are allowed at runtime
- the embedding model must already exist locally or inside the local Hugging Face cache

Backend behavior:

- `kb/config.yaml` controls chunking, model name, top-k, and output limits
- `index_backend: auto` prefers FAISS
- if FAISS is unavailable, it falls back to `hnswlib`

More KB details are documented in [kb/README.md](C:/Users/PC-Thien/ai_test_system/kb/README.md).

## Store Verify Quickstart

1. Put `.docx`, `.md`, or `.txt` business docs into `requirements/store_verify/`.
2. Build the KB:
   - `python kb/build_kb.py --domain store_verify`
3. Generate prompts and KB context packs:
   - `python scripts/run_domain_manual.py --domain store_verify --run-id demo_verify --allow-incomplete`
4. Open `outputs/store_verify/demo_verify/`.
5. Use `step_01_prompt.txt` through `step_06_prompt.txt` with ChatGPT or Codex.
6. Paste model outputs back into the canonical artifact files.
7. Validate:
   - `python scripts/validate_outputs.py outputs/store_verify/demo_verify`

The runner writes:

- `kb_context_step01.txt` through `kb_context_step06.txt`
- `step_01_prompt.txt` through `step_06_prompt.txt`
- the canonical step output files
- `run_meta.json`

Each `store_verify` prompt is KB-first:

- business truth must come from `KB_CONTEXT`
- if the KB context does not contain a fact, the model should return `UNKNOWN`
- design docs under `domains/store_verify/design/` are code-facts only

## Didaunao Release Audit Quickstart

1. Put the release self-inspection standard documents into `requirements/didaunao_release_audit/`.
   Recommended primary file:
   - `产品上线自检手册_V3-行业通用版.docx`
2. Build the KB:
   - `python kb/build_kb.py --domain didaunao_release_audit`
3. Generate prompts and KB context packs:
   - `python scripts/run_domain_manual.py --domain didaunao_release_audit --run-id demo_release_audit --allow-incomplete`
4. Open `outputs/didaunao_release_audit/demo_release_audit/`.
5. Use `step_01_prompt.txt` through `step_06_prompt.txt` with ChatGPT or Codex.
6. Paste model outputs back into the canonical artifact files.
7. Validate:
   - `python scripts/validate_outputs.py outputs/didaunao_release_audit/demo_release_audit`
8. Export the final consolidated report:
   - `python scripts/export_release_audit_report.py outputs/didaunao_release_audit/demo_release_audit`

The `didaunao_release_audit` prompts are KB-first and optimized for release self-inspection topics:

- UX/UI and commercial acceptance
- performance metrics
- crash and ANR thresholds
- security and OWASP controls
- API p95 and SLA expectations
- monitoring and observability
- rollback readiness
- data quality
- search relevance

The report exporter writes `release_audit_report.md` into the same run folder by default. It summarizes:

- Executive summary with current GO/NO-GO recommendation
- Mandatory checklist results
- Risks and gaps
- Testing plan for this week
- Optimization and upgrade plan for the next 2-4 weeks

## Order Manual Flow

Run:

- `python scripts/run_order_manual.py`

Then:

1. Open the new folder under `outputs/order/<run_id>/`.
2. Copy `step_01_prompt.txt` into ChatGPT or Codex.
3. Paste the model response into `01_state_machine.json`, replacing the placeholder text.
4. Rerun `python scripts/run_order_manual.py --run-id <run_id>`.
5. Repeat until `06_release_checklist.md` is filled.
6. Validate with `python scripts/validate_outputs.py outputs/order/<run_id>`.

`order` keeps its existing behavior and does not depend on the KB module.

## Fail-Fast and `--allow-incomplete`

Default behavior is fail-fast:

- if an upstream artifact is missing or still contains the placeholder text, the runner aborts
- for KB-enabled domains, the runner also aborts if the KB index is missing

Use `--allow-incomplete` only when you intentionally want placeholder prompts and pending markers:

- `python scripts/run_domain_manual.py --domain store_verify --run-id demo_verify --allow-incomplete`
- `python scripts/run_domain_manual.py --domain didaunao_release_audit --run-id demo_release_audit --allow-incomplete`
- `python scripts/run_order_manual.py --run-id order_smoke --allow-incomplete`

When `--allow-incomplete` is enabled:

- downstream prompts may contain `[PENDING INPUT ...]`
- KB-enabled runs may write placeholder `kb_context_stepXX.txt` files if the KB index has not been built yet

## Order Orchestrator Flow

The orchestrated Order pipeline is defined in [core/orchestrator.py](C:/Users/PC-Thien/ai_test_system/core/orchestrator.py). It reads:

- `domains/order/design/state_machine.md`
- `domains/order/design/api_contract.md`
- `domains/order/design/rules.md`
- `domains/order/knowledge_base/*.md`
- `domains/order/prompts/01..06`

It writes the same canonical filenames into `outputs/order/<run_id>/`, so validator mapping is the same:

- `python scripts/validate_outputs.py outputs/order/<run_id>`

## Validation

Run:

- `python scripts/validate_outputs.py outputs/<domain>/<run_id>`

The validator checks:

- `03_testcases_raw.json`
- `04_testcases_refined.json`
- `05_regression_suite.json`

It also enforces:

- testcase ids must match the current domain prefix such as `TC-ORDER-` or `TC-STORE-VERIFY-`
- testcase ids also work for longer KB domains such as `TC-DIDAUNAO-RELEASE-AUDIT-`
- regression ids must be unique
- regression ids must be a subset of refined testcase ids
- all `P0` testcase ids must be included
- target ratio is `25%-40%` unless `P0` tests alone exceed `40%`
- if the ratio override is used, `notes` must explain it

If `run_meta.json` says `allow_incomplete=false`, the validator also flags `[PENDING INPUT ...]` markers inside `step_XX_prompt.txt` and `kb_context_stepXX.txt`.

## Troubleshooting

- If `kb/build_kb.py` fails while loading the model, preload the configured sentence-transformers model locally first.
- If `kb/build_kb.py` fails on Windows with FAISS, switch `index_backend` to `hnsw` in [kb/config.yaml](C:/Users/PC-Thien/ai_test_system/kb/config.yaml).
- If `python scripts/export_release_audit_report.py ...` reports incomplete evidence, finish steps `01/04/05/06` first or resolve `UNKNOWN` items before using the report for a release decision.
- If a later manual prompt still shows `[PENDING INPUT ...]`, rerun without `--allow-incomplete` after filling the required upstream artifact.
- If validation reports JSON parsing errors, remove any prose outside the JSON payload. Fenced code blocks are accepted.
- If the Order orchestrator path fails while parsing JSON, inspect `debug_<step>.txt` in the run folder for the raw model output.
