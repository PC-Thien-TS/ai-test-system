# ai_test_system

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
