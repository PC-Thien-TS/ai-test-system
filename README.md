# ai_test_system

## v2.7.0 - Escalation Observability and Evidence UI

Version 2.7.0 upgrades intelligent orchestration observability and completes the escalation UI lifecycle.

### Key Features

- **Project Detail Widgets**: Added execution intelligence widgets (ConfidenceTrendChart, ExecutionDepthChart, FallbackRatioHeatmap, PluginMaturityHeatmap) to project detail page
- **Run Detail Page**: Created new run detail page with SSE integration for real-time confidence, fallback, and evidence updates
- **Escalation Rerun API**: Added POST /runs/{run_id}/escalate endpoint for manual escalation rerun with automatic path promotion (SMOKE -> STANDARD -> DEEP -> INTELLIGENT)
- **Escalation Browser UI**: New /escalations page to view escalation chains, reasons, and path promotions
- **Evidence Browser UI**: New /evidence/{runId} page to browse evidence per run (screenshots, traces, citations, anomalies, matrices) with search/filter
- **Run Detail API**: Added GET /runs/{run_id} endpoint to retrieve individual run details with execution intelligence fields

### New UI Routes

- `/runs/{id}` - Run detail page with SSE live updates and execution intelligence widgets
- `/escalations` - Escalation browser for viewing chains and path promotions
- `/evidence/{runId}` - Evidence browser with search/filter for screenshots, traces, citations, anomalies, matrices

### API Changes

- `GET /runs/{run_id}` - Get specific run details with execution intelligence fields
- `POST /runs/{run_id}/escalate` - Trigger escalation rerun with automatic path promotion

### Backend Changes

- `api/routes/runs.py`: Added GET /runs/{run_id} endpoint, added POST /runs/{run_id}/escalate endpoint
- `dashboard/lib/api-client.ts`: Added getRun API method
- `dashboard/lib/types.ts`: Updated Run type to include execution_path, parent_run_id, confidence_score, fallback_ratio, real_execution_ratio

### Frontend Changes

- `dashboard/app/projects/[id]/page.tsx`: Added 4 execution intelligence widgets
- `dashboard/app/runs/[id]/page.tsx`: New run detail page with SSE integration and intelligence widgets
- `dashboard/app/escalations/page.tsx`: New escalation browser UI page
- `dashboard/app/evidence/[runId]/page.tsx`: New evidence browser UI page with search/filter

### SSE Integration Points

- Run detail page uses SSE endpoint `/runs/{run_id}/updates` for real-time confidence, fallback, and evidence updates
- Live indicator shows when SSE connection is active
- Confidence score, fallback ratio, and real execution ratio update in real-time during run execution

### Escalation Auto-Rerun Flow

1. User triggers run with intelligent path selection
2. Run completes with metrics (confidence_score, fallback_ratio, real_execution_ratio)
3. If escalation conditions are met (high fallback, low real execution, flaky, failed):
   - User can manually trigger escalation via API or UI
   - System automatically promotes execution path (SMOKE -> STANDARD -> DEEP -> INTELLIGENT)
   - Escalation chain is persisted with reasons
4. New run is created with parent_run_id and escalation metadata
5. Process repeats until max depth is reached or INTELLIGENT path is used

### Dashboard Pages Upgraded

- **Project Detail**: Added 4 execution intelligence widgets in grid layout
- **Run Detail**: New page with SSE live updates, 4 intelligence widgets, execution path display, escalation reason display
- **Escalations**: New page showing escalation chains, path promotions, and statistics
- **Evidence**: New page showing evidence items by type with search/filter functionality

### Changed Files

**Backend (2 updated):**
- `api/routes/runs.py`: Added GET /runs/{run_id} and POST /runs/{run_id}/escalate endpoints
- `api/app.py`: Bumped version to 2.7.0
- `orchestrator/compatibility.py`: Updated platform version to 2.7.0

**Frontend (4 new pages, 3 updated):**
- `dashboard/app/projects/[id]/page.tsx`: Added execution intelligence widgets
- `dashboard/app/runs/[id]/page.tsx`: New run detail page with SSE
- `dashboard/app/escalations/page.tsx`: New escalation browser
- `dashboard/app/evidence/[runId]/page.tsx`: New evidence browser
- `dashboard/lib/api-client.ts`: Added getRun method
- `dashboard/lib/types.ts`: Updated Run type

**Tests (1 new file):**
- `tests/test_v27_escalation.py`: New test file for escalation features (9 tests)

### Test Results

**v2.7 Escalation Tests (9 tests):**
- test_trigger_escalation_rerun: ✅
- test_escalation_path_promotion: ✅
- test_escalation_chain_persistence: ✅
- test_max_escalation_depth: ✅
- test_evidence_persistence_location: ✅
- test_api_get_run_endpoint: ✅
- test_api_escalate_endpoint: ✅
- test_sse_endpoint_format: ✅

**Total: 9 new tests added**

### Recommended v2.8 Roadmap

1. **WebSocket Integration**: Replace SSE polling with WebSocket for true bidirectional real-time updates
2. **Escalation Policies**: Allow users to configure custom escalation rules per project (thresholds, auto-escalate)
3. **Evidence Search**: Add advanced search with filters by severity, confidence, timestamp, plugin
4. **Evidence Download**: Add download functionality for evidence items (screenshots, traces, logs)
5. **Escalation Timeline Visualization**: Add visual timeline view of escalation chains
6. **Evidence Comparison**: Add side-by-side comparison of evidence across escalation runs
7. **Real-Time Evidence Streaming**: Stream evidence items as they are collected during run execution
8. **Escalation Analytics**: Add analytics dashboard for escalation patterns, success rates, time to resolution

## v2.6.0 - Intelligent Run Orchestration

Version 2.6.0 integrates the v2.5 execution intelligence layer into the real run lifecycle.

### Key Features

- **Run API Integration**: Run APIs and CLI flows now use execution_intelligence for intelligent path selection
- **Automatic Escalation Workflow**: SMOKE -> STANDARD -> DEEP -> INTELLIGENT escalation chain with automatic reruns
- **Escalation Chain Persistence**: Tracks and persists escalation chains with reasons for audit and learning
- **Evidence Collection Integration**: Connects evidence_collector to real run artifacts for dynamic evidence richness
- **Evidence Persistence**: Persists evidence per run under outputs/evidence/<run_id>/ with JSON serialization
- **Real-Time Updates**: SSE endpoint for real-time confidence and fallback updates during run execution
- **Dashboard Widget Integration**: Confidence trend, execution depth, fallback ratio, and plugin maturity widgets on homepage

### New Modules

- `orchestrator/run_orchestrator.py`: Run orchestration service integrating execution intelligence into run lifecycle
- `orchestrator/models.py`: Added ExecutionPath enum, EscalationChain model, and Run model enhancements (execution_path, parent_run_id, confidence_score)

### API Changes

- `POST /projects/{project_id}/run`: Now accepts optional `execution_path` parameter for forced path selection
- `GET /runs/{run_id}/updates`: SSE endpoint for real-time run updates (confidence_score, fallback_ratio, real_execution_ratio)

### Backend Changes

- `orchestrator/project_service.py`: Integrated RunOrchestrator, added trigger_run with intelligent path selection, added trigger_escalation_run for escalation workflow
- `orchestrator/platform_summary.py`: Updated to generate confidence_trend, plugin_depth_scores, fallback_ratios, plugin_maturity_scores for dashboard widgets
- `api/routes/projects.py`: Updated trigger_run response to include execution_path
- `api/routes/runs.py`: Added SSE endpoint for real-time run updates

### Frontend Changes

- `dashboard/lib/types.ts`: Updated PlatformSummary with new intelligence fields
- `dashboard/app/page.tsx`: Integrated 4 execution intelligence widgets (ConfidenceTrendChart, ExecutionDepthChart, FallbackRatioHeatmap, PluginMaturityHeatmap)

### Real Lifecycle Integration Points

**Before v2.6 (v2.5 Intelligence Only):**
- Execution intelligence was a separate module not connected to actual run execution
- Path selection was theoretical, not applied to real runs
- Evidence collection was standalone, not integrated with run artifacts
- No escalation workflow or chain persistence

**After v2.6 (Real Orchestration):**
- Run APIs use execution intelligence for intelligent path selection
- Automatic escalation workflow (SMOKE -> STANDARD -> DEEP -> INTELLIGENT)
- Escalation chains are persisted with reasons for audit and learning
- Evidence collection is integrated with real run artifacts and persisted to disk
- SSE endpoint provides real-time confidence and fallback updates
- Dashboard widgets display actual intelligence data from platform summary

### Rerun Escalation Workflow

1. Initial run with intelligent path selection (based on project health, plugin depth, historical performance)
2. Run completes with fallback_ratio and real_execution_ratio metrics
3. If escalation conditions are met:
   - fallback_ratio > 0.5
   - real_execution_ratio < 0.3
   - smoke failure
   - flaky standard run
4. Automatic rerun with escalated path (STANDARD -> DEEP -> INTELLIGENT)
5. Escalation chain persisted with reasons
6. Maximum escalation depth configurable (default: 3)

### Dashboard Pages Upgraded

- **Homepage**: Added 4 execution intelligence widgets in a grid layout
- **Project Detail**: Ready for widget integration (uses same data structures)
- **Run Detail**: Ready for widget integration (uses SSE endpoint for real-time updates)

### Changed Files

**Backend (1 new module, 4 updated):**
- `orchestrator/run_orchestrator.py`: New module - run orchestration service
- `orchestrator/models.py`: Added ExecutionPath, EscalationChain, updated Run model
- `orchestrator/project_service.py`: Integrated RunOrchestrator, added orchestration methods
- `orchestrator/platform_summary.py`: Added intelligence data generation
- `api/routes/projects.py`: Updated trigger_run endpoint
- `api/routes/runs.py`: Added SSE endpoint
- `api/app.py`: Bumped version to 2.6.0
- `orchestrator/compatibility.py`: Updated platform version to 2.6.0

**Frontend (2 updated):**
- `dashboard/lib/types.ts`: Updated PlatformSummary with intelligence fields
- `dashboard/app/page.tsx`: Integrated 4 execution intelligence widgets

**Tests (1 new file):**
- `tests/test_run_orchestrator.py`: New test file for orchestration integration (11 tests)

### Test Results

**Run Orchestrator Tests (11 tests):**
- test_plan_run_with_intelligence: ✅
- test_plan_run_forced_path: ✅
- test_should_escalate_high_fallback: ✅
- test_should_escalate_max_depth: ✅
- test_create_escalation_chain: ✅
- test_get_escalation_chain: ✅
- test_collect_evidence: ✅
- test_persist_evidence: ✅
- test_calculate_confidence: ✅
- test_escalation_chain_persistence: ✅

**Total: 11 new tests added**

### Recommended v2.7 Roadmap

1. **Project Detail Page Integration**: Add execution intelligence widgets to project detail page with project-specific data
2. **Run Detail Page Integration**: Add execution intelligence widgets to run detail page with SSE real-time updates
3. **Automatic Escalation Execution**: Implement automatic escalation rerun trigger after run completion
4. **Escalation Dashboard UI**: Add UI to view escalation chains and reasons
5. **Evidence Browser UI**: Add UI to browse persisted evidence per run
6. **WebSocket Integration**: Replace SSE polling with WebSocket for true real-time updates
7. **Escalation Policies**: Allow users to configure custom escalation rules per project
8. **Evidence Search**: Add search and filtering capabilities for evidence items

## v2.5.0 - Execution Intelligence Engine

Version 2.5.0 converts v2.4 metadata-only execution depth into a real execution intelligence layer with adaptive validation.

### Key Features

- **Execution Intelligence Engine**: Chooses between smoke, standard, deep, and intelligent execution paths based on project health, plugin depth, and historical performance
- **Evidence Collection Framework**: Per-plugin evidence adapters (web_playwright, api_contract, rag_grounding) with dynamic evidence_richness_score calculation
- **Confidence Scoring Algorithms**: Plugin-specific confidence strategies (web_playwright, api_contract, rag_grounding) with factor breakdown (evidence richness, run stability, anomaly-free, historical performance, plugin maturity, fallback penalty)
- **Fallback Escalation**: Automatic detection of excessive fallback usage, low real execution, smoke failures, and flakiness with persistence in run metadata
- **Dashboard Widgets**: Confidence trend chart, execution depth chart, fallback ratio heatmap, plugin maturity heatmap

### New Modules

- `orchestrator/execution_intelligence.py`: Execution intelligence engine with path selection and escalation logic
- `orchestrator/evidence_collector.py`: Evidence collection framework with plugin-specific adapters
- `orchestrator/confidence_scorer.py`: Confidence scoring algorithms with plugin-specific strategies

### New Dashboard Components

- `dashboard/components/confidence-trend-chart.tsx`: Line chart showing confidence score trends over time
- `dashboard/components/execution-depth-chart.tsx`: Bar chart showing plugin execution depth scores
- `dashboard/components/fallback-ratio-heatmap.tsx`: Pie chart showing fallback ratio distribution
- `dashboard/components/plugin-maturity-heatmap.tsx`: Area chart showing plugin maturity scores

### New TypeScript Types

- `ExecutionPath`: Enum for execution path types (SMOKE, STANDARD, DEEP, INTELLIGENT)
- `ExecutionStrategy`: Interface for execution strategy configuration
- `ConfidenceFactors`: Interface for confidence scoring factors
- `ConfidenceScore`: Interface for confidence score with breakdown
- `EvidenceItem`: Interface for individual evidence items
- `EvidenceSummary`: Interface for evidence summary per plugin
- `EscalationReason`: Interface for escalation reason tracking

### Metadata vs Real Execution Differences

**v2.4 (Metadata Only):**
- Plugin depth scores were static metadata
- Evidence richness scores were static metadata
- Confidence scores were static metadata
- No actual execution intelligence

**v2.5 (Real Execution):**
- Execution intelligence engine dynamically chooses execution paths
- Evidence collection framework calculates richness scores dynamically from actual evidence
- Confidence scorer calculates scores dynamically from run results, evidence, and historical data
- Fallback escalation automatically promotes to deeper validation when needed

### Changed Files

**Backend:**
- `orchestrator/execution_intelligence.py`: New module - execution intelligence engine
- `orchestrator/evidence_collector.py`: New module - evidence collection framework
- `orchestrator/confidence_scorer.py`: New module - confidence scoring algorithms
- `api/app.py`: Bumped version to 2.5.0
- `orchestrator/compatibility.py`: Updated platform version to 2.5.0

**Frontend:**
- `dashboard/lib/types.ts`: Added execution intelligence TypeScript types
- `dashboard/components/confidence-trend-chart.tsx`: New widget
- `dashboard/components/execution-depth-chart.tsx`: New widget
- `dashboard/components/fallback-ratio-heatmap.tsx`: New widget
- `dashboard/components/plugin-maturity-heatmap.tsx`: New widget

**Tests:**
- `tests/test_execution_intelligence.py`: New test file for execution intelligence
- `tests/test_evidence_collector.py`: New test file for evidence collector
- `tests/test_confidence_scorer.py`: New test file for confidence scorer

### Test Results

**Execution Intelligence Tests (9 tests):**
- test_choose_execution_path_smoke: ✅
- test_choose_execution_path_deep: ✅
- test_choose_execution_path_forced: ✅
- test_should_escalate_high_fallback: ✅
- test_should_escalate_low_real_execution: ✅
- test_should_escalate_smoke_failure: ✅
- test_should_escalate_flaky_standard: ✅
- test_should_not_escalate_healthy: ✅
- test_escalation_history: ✅

**Evidence Collector Tests (8 tests):**
- test_web_playwright_adapter_collect_evidence: ✅
- test_web_playwright_adapter_richness: ✅
- test_api_contract_adapter_collect_evidence: ✅
- test_rag_grounding_adapter_collect_evidence: ✅
- test_evidence_collector_collect_all: ✅
- test_evidence_collector_richness_scores: ✅
- test_evidence_collector_generate_summary: ✅

**Confidence Scorer Tests (8 tests):**
- test_web_playwright_confidence_strategy: ✅
- test_api_contract_confidence_strategy: ✅
- test_rag_grounding_confidence_strategy: ✅
- test_confidence_sorer_calculate_confidence: ✅
- test_confidence_sorer_aggregate_confidence: ✅
- test_confidence_sorer_generic_strategy: ✅
- test_confidence_factors_defaults: ✅

**Total: 25 new tests added**

### Recommended v2.6 Roadmap

1. **Execution Engine Integration**: Integrate execution intelligence engine into the actual run execution flow
2. **Real Evidence Collection**: Connect evidence collectors to actual plugin execution outputs
3. **Dynamic Confidence Updates**: Update confidence scores in real-time during run execution
4. **Dashboard Integration**: Add execution intelligence widgets to actual dashboard pages
5. **Escalation Workflows**: Implement automatic re-run with escalated paths
6. **Custom Strategies**: Allow users to define custom confidence strategies
7. **Evidence Storage**: Persist evidence items to database for historical analysis
8. **ML-Based Confidence**: Add machine learning models for confidence prediction

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
