# ai_test_system

This repository supports two aligned Order pipelines:

- a manual pipeline that generates prompts and expects you to paste model outputs back into a run folder
- an orchestrated pipeline driven by `core.orchestrator.Orchestrator`

Both paths now use the same artifact filenames for the Order domain.

## Order Artifacts

Every Order run folder is expected to contain these files:

- `01_state_machine.json`
- `02_rule_matrix.json`
- `03_testcases_raw.json`
- `04_testcases_refined.json`
- `05_regression_suite.json`
- `06_release_checklist.md`

The validator accepts a run folder produced by either path as long as those files exist with the expected formats.

## Manual Flow

1. Run `python scripts/run_order_manual.py`.
2. Open the new folder under `outputs/order/<run_id>/`.
3. Copy `step_01_prompt.txt` into ChatGPT or Codex.
4. Paste the model response into `01_state_machine.json`, replacing the placeholder text.
5. Rerun `python scripts/run_order_manual.py --run-id <run_id>`.
6. Repeat until `06_release_checklist.md` is filled.
7. Validate with `python scripts/validate_outputs.py outputs/order/<run_id>`.

Default behavior is fail-fast. If a downstream prompt depends on an upstream artifact that is missing or still contains the placeholder text, the runner aborts with a clear error.

On a brand-new run, this means the command writes `step_01_prompt.txt` and then stops when step `02` cannot be composed yet. Fill `01_state_machine.json` and rerun with the same `--run-id`.

Use `--allow-incomplete` only when you intentionally want downstream prompt files to be generated with `[PENDING INPUT ...]` markers:

- `python scripts/run_order_manual.py --run-id <run_id> --allow-incomplete`

Manual flow required artifacts:

- Step `02` requires `01_state_machine.json`
- Step `03` requires `01_state_machine.json` and `02_rule_matrix.json`
- Step `04` requires `03_testcases_raw.json`
- Step `05` requires `04_testcases_refined.json`
- Step `06` requires `01_state_machine.json`, `04_testcases_refined.json`, and `05_regression_suite.json`

The manual runner prints each composed prompt to stdout and also writes `step_01_prompt.txt` through `step_06_prompt.txt` into the run folder.

## Orchestrator Flow

The orchestrated Order pipeline is defined in [core/orchestrator.py](C:/Users/PC-Thien/ai_test_system/core/orchestrator.py). It reads:

- `domains/order/design/state_machine.md`
- `domains/order/design/api_contract.md`
- `domains/order/design/rules.md`
- `domains/order/knowledge_base/*.md`
- `domains/order/prompts/01..06`

Programmatic usage:

```python
from pathlib import Path

from core.orchestrator import Orchestrator

root = Path(".").resolve()
orchestrator = Orchestrator(root=root)
ctx = orchestrator.run(domain="order", llm=your_llm_adapter)
print(ctx.output_dir)
```

The orchestrator writes the same artifact filenames listed above into `outputs/order/<run_id>/`, so the same validator command applies:

- `python scripts/validate_outputs.py outputs/order/<run_id>`

## Validation

Run:

- `python scripts/validate_outputs.py outputs/order/<run_id>`

The validator checks:

- `03_testcases_raw.json` against `schemas/test_case.schema.json`
- `04_testcases_refined.json` against `schemas/test_case.schema.json`
- `05_regression_suite.json` against `schemas/regression.schema.json`

It also applies logic checks for the regression suite:

- regression ids must be unique
- regression ids must be a subset of refined testcase ids
- all `P0` testcase ids must be included
- target ratio is `25%-40%` unless `P0` tests alone exceed `40%`
- if the ratio override is used, `notes` must explain it

## Troubleshooting

- If a later manual prompt still shows `[PENDING INPUT ...]`, rerun without `--allow-incomplete` after filling the required upstream artifact.
- If validation reports JSON parsing errors, remove any prose outside the JSON payload. Fenced code blocks are accepted.
- If the orchestrator path fails while parsing JSON, inspect `debug_<step>.txt` in the run folder for the raw model output.
- If validation fails on step `05`, check whether the refined testcase suite contains too many `P0` cases for the normal `25%-40%` target and ensure the override is explained in `notes`.
