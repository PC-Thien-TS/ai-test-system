from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict


PLACEHOLDER_MARKER = "MANUAL OUTPUT PLACEHOLDER"


@dataclass(frozen=True)
class StepSpec:
    number: int
    prompt_template: str
    prompt_file: str
    output_file: str
    output_format: str
    replacements: Dict[str, Dict[str, str]]


STEPS = [
    StepSpec(
        number=1,
        prompt_template="domains/order/prompts/01_extract_state_machine.md",
        prompt_file="step_01_prompt.txt",
        output_file="01_state_machine.json",
        output_format="JSON",
        replacements={
            "STATE_MACHINE_DOC": {"type": "static", "path": "domains/order/design/state_machine.md"},
            "API_CONTRACT_DOC": {"type": "static", "path": "domains/order/design/api_contract.md"},
            "RULES_DOC": {"type": "static", "path": "domains/order/design/rules.md"},
        },
    ),
    StepSpec(
        number=2,
        prompt_template="domains/order/prompts/02_build_rule_matrix.md",
        prompt_file="step_02_prompt.txt",
        output_file="02_rule_matrix.json",
        output_format="JSON",
        replacements={
            "STATE_MACHINE_JSON": {
                "type": "run_output",
                "path": "01_state_machine.json",
                "producer_step": "01",
            }
        },
    ),
    StepSpec(
        number=3,
        prompt_template="domains/order/prompts/03_generate_testcases.md",
        prompt_file="step_03_prompt.txt",
        output_file="03_testcases_raw.json",
        output_format="JSON",
        replacements={
            "STATE_MACHINE_JSON": {
                "type": "run_output",
                "path": "01_state_machine.json",
                "producer_step": "01",
            },
            "RULE_MATRIX_JSON": {
                "type": "run_output",
                "path": "02_rule_matrix.json",
                "producer_step": "02",
            },
            "API_CONTRACT_DOC": {"type": "static", "path": "domains/order/design/api_contract.md"},
            "RULES_DOC": {"type": "static", "path": "domains/order/design/rules.md"},
            "KB_GLOSSARY": {"type": "static", "path": "domains/order/knowledge_base/glossary.md"},
            "KB_COMMON_RULES": {
                "type": "static",
                "path": "domains/order/knowledge_base/common_rules.md",
            },
            "KB_BUG_PATTERNS": {
                "type": "static",
                "path": "domains/order/knowledge_base/bug_patterns.md",
            },
        },
    ),
    StepSpec(
        number=4,
        prompt_template="domains/order/prompts/04_review_refine.md",
        prompt_file="step_04_prompt.txt",
        output_file="04_testcases_refined.json",
        output_format="JSON",
        replacements={
            "TESTCASES_JSON": {
                "type": "run_output",
                "path": "03_testcases_raw.json",
                "producer_step": "03",
            }
        },
    ),
    StepSpec(
        number=5,
        prompt_template="domains/order/prompts/05_build_regression.md",
        prompt_file="step_05_prompt.txt",
        output_file="05_regression_suite.json",
        output_format="JSON",
        replacements={
            "TESTCASES_REFINED_JSON": {
                "type": "run_output",
                "path": "04_testcases_refined.json",
                "producer_step": "04",
            }
        },
    ),
    StepSpec(
        number=6,
        prompt_template="domains/order/prompts/06_release_checklist.md",
        prompt_file="step_06_prompt.txt",
        output_file="06_release_checklist.md",
        output_format="Markdown",
        replacements={
            "STATE_MACHINE_JSON": {
                "type": "run_output",
                "path": "01_state_machine.json",
                "producer_step": "01",
            },
            "REGRESSION_JSON": {
                "type": "run_output",
                "path": "05_regression_suite.json",
                "producer_step": "05",
            },
            "TESTCASES_REFINED_JSON": {
                "type": "run_output",
                "path": "04_testcases_refined.json",
                "producer_step": "04",
            },
        },
    ),
]


class ManualRunner:
    def __init__(
        self,
        repo_root: Path,
        run_id: str | None = None,
        allow_incomplete: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.repo_root / "outputs" / "order" / self.run_id
        self.allow_incomplete = allow_incomplete

    def run(self) -> Path:
        self.ensure_required_files()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.write_run_guide()
        self.ensure_output_placeholders()
        self.write_prompt_files()
        return self.run_dir

    def ensure_required_files(self) -> None:
        required_paths = [
            "domains/order/design/state_machine.md",
            "domains/order/design/api_contract.md",
            "domains/order/design/rules.md",
            "domains/order/knowledge_base/glossary.md",
            "domains/order/knowledge_base/common_rules.md",
            "domains/order/knowledge_base/bug_patterns.md",
        ]
        required_paths.extend(step.prompt_template for step in STEPS)
        missing = [path for path in required_paths if not (self.repo_root / path).exists()]
        if missing:
            lines = "\n".join(f"- {path}" for path in missing)
            raise FileNotFoundError(f"Missing required files:\n{lines}")

    def write_run_guide(self) -> None:
        guide_path = self.run_dir / "HOW_TO_USE.txt"
        guide = "\n".join(
            [
                f"Manual Order pipeline run: {self.run_id}",
                "",
                "Workflow:",
                "1. Open the next step_XX_prompt.txt file in this folder.",
                "2. Paste the full prompt into ChatGPT or Codex.",
                "3. Replace the matching output file contents with only the model output.",
                f"4. Rerun: python scripts/run_order_manual.py --run-id {self.run_id}",
                f"5. Validate testcase JSON with: python scripts/validate_outputs.py outputs/order/{self.run_id}",
                "6. Use --allow-incomplete only if you intentionally want downstream prompts with pending-input markers.",
                "7. Default behavior is fail-fast, so a fresh run normally stops after writing step_01_prompt.txt.",
                "",
                "Output files for this run:",
                "01_state_machine.json",
                "02_rule_matrix.json",
                "03_testcases_raw.json",
                "04_testcases_refined.json",
                "05_regression_suite.json",
                "06_release_checklist.md",
            ]
        )
        guide_path.write_text(guide + "\n", encoding="utf-8")

    def ensure_output_placeholders(self) -> None:
        for step in STEPS:
            output_path = self.run_dir / step.output_file
            if output_path.exists():
                continue
            output_path.write_text(self.placeholder_text(step), encoding="utf-8")

    def placeholder_text(self, step: StepSpec) -> str:
        return "\n".join(
            [
                PLACEHOLDER_MARKER,
                "",
                f"Step {step.number:02d} output belongs here.",
                f"Prompt file: {step.prompt_file}",
                f"Expected format: {step.output_format}",
                "",
                "Instructions:",
                f"1. Open {step.prompt_file} from this run folder.",
                "2. Paste the full prompt into ChatGPT or Codex.",
                "3. Replace this entire file with only the model output.",
                f"4. Rerun: python scripts/run_order_manual.py --run-id {self.run_id}",
            ]
        )

    def write_prompt_files(self) -> None:
        for step in STEPS:
            prompt_text = self.compose_prompt(step)
            prompt_path = self.run_dir / step.prompt_file
            prompt_path.write_text(prompt_text, encoding="utf-8")
            self.print_prompt(step, prompt_text)

    def compose_prompt(self, step: StepSpec) -> str:
        template_text = self.read_text(self.repo_root / step.prompt_template)
        for placeholder, source in step.replacements.items():
            replacement = self.resolve_source(source, step.number)
            template_text = template_text.replace(f"{{{{{placeholder}}}}}", replacement)

        unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", template_text)))
        if unresolved:
            raise ValueError(
                f"Unresolved placeholders remain in step {step.number:02d}: {', '.join(unresolved)}"
            )
        return template_text

    def resolve_source(self, source: Dict[str, str], current_step: int) -> str:
        source_type = source["type"]
        if source_type == "static":
            return self.read_text(self.repo_root / source["path"])
        if source_type == "run_output":
            return self.read_run_output(source["path"], source["producer_step"], current_step)
        raise ValueError(f"Unsupported source type: {source_type}")

    def read_run_output(self, relative_path: str, producer_step: str, current_step: int) -> str:
        output_path = self.run_dir / relative_path
        if not output_path.exists():
            self.raise_if_incomplete(output_path.name, producer_step, current_step)
            return self.pending_input_message(output_path.name, producer_step)

        raw_text = self.read_text(output_path)
        if self.is_placeholder(raw_text):
            self.raise_if_incomplete(output_path.name, producer_step, current_step)
            return self.pending_input_message(output_path.name, producer_step)
        return strip_fenced_block(raw_text)

    def raise_if_incomplete(self, filename: str, producer_step: str, current_step: int) -> None:
        if self.allow_incomplete:
            return
        raise RuntimeError(
            "\n".join(
                [
                    f"Cannot compose step {current_step:02d}: upstream output '{filename}' is missing or still a placeholder.",
                    f"Complete step {producer_step} first, save it to outputs/order/{self.run_id}/{filename}, then rerun.",
                    "If you intentionally want downstream prompts with pending markers, rerun with --allow-incomplete.",
                ]
            )
        )

    def pending_input_message(self, filename: str, producer_step: str) -> str:
        return "\n".join(
            [
                f"[PENDING INPUT: {filename} is not filled yet.]",
                f"Replace outputs/order/{self.run_id}/{filename} with the model output from step {producer_step}.",
                f"Then rerun: python scripts/run_order_manual.py --run-id {self.run_id}",
            ]
        )

    def print_prompt(self, step: StepSpec, prompt_text: str) -> None:
        separator = "=" * 80
        safe_print(separator)
        safe_print(f"STEP {step.number:02d} PROMPT -> {step.output_file}")
        safe_print(separator)
        safe_print(prompt_text)
        safe_print("")

    @staticmethod
    def is_placeholder(text: str) -> bool:
        return text.lstrip().startswith(PLACEHOLDER_MARKER)

    @staticmethod
    def read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace").strip()


def strip_fenced_block(text: str) -> str:
    normalized = text.lstrip("\ufeff").strip()
    if not normalized.startswith("```"):
        return normalized

    lines = normalized.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return normalized


def safe_print(text: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.buffer.write((text + "\n").encode(encoding, errors="backslashreplace"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate manual Order pipeline prompts.")
    parser.add_argument(
        "--run-id",
        help="Resume or regenerate an existing run folder. If omitted, a new run id is created.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Generate downstream prompts with pending-input markers instead of aborting on missing upstream artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    runner = ManualRunner(
        repo_root=repo_root,
        run_id=args.run_id,
        allow_incomplete=args.allow_incomplete,
    )
    run_dir = runner.run()
    print(f"Run folder ready: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
