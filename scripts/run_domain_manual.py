from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kb._lib.paths import output_dir as resolve_output_dir
from kb.query_kb import load_index_bundle
from kb.prompt_pack import generate_prompt_pack


PLACEHOLDER_MARKER = "MANUAL OUTPUT PLACEHOLDER"
PENDING_INPUT_PREFIX = "[PENDING INPUT:"
CANONICAL_OUTPUTS = [
    "01_state_machine.json",
    "02_rule_matrix.json",
    "03_testcases_raw.json",
    "04_testcases_refined.json",
    "05_regression_suite.json",
    "06_release_checklist.md",
]


@dataclass(frozen=True)
class StepSpec:
    number: int
    prompt_template: str
    prompt_file: str
    output_file: str
    output_format: str
    replacements: Dict[str, Dict[str, str]]


DOMAIN_MODES = {
    "order": {
        "mode": "legacy_static",
        "kb_enabled": False,
    },
    "didaunao_release_audit": {
        "mode": "kb_context",
        "kb_enabled": True,
    },
    "store_verify": {
        "mode": "kb_context",
        "kb_enabled": True,
    },
}


DOMAIN_STEPS = {
    "order": [
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
    ],
    "store_verify": [
        StepSpec(
            number=1,
            prompt_template="domains/store_verify/prompts/01_extract_state_machine.md",
            prompt_file="step_01_prompt.txt",
            output_file="01_state_machine.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "01"},
                "KB_CONTEXT": {"type": "kb_context", "step": "01"},
                "API_CONTRACT_DOC": {"type": "static", "path": "domains/store_verify/design/api_contract.md"},
                "RULES_DOC": {"type": "static", "path": "domains/store_verify/design/rules.md"},
            },
        ),
        StepSpec(
            number=2,
            prompt_template="domains/store_verify/prompts/02_build_rule_matrix.md",
            prompt_file="step_02_prompt.txt",
            output_file="02_rule_matrix.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "02"},
                "KB_CONTEXT": {"type": "kb_context", "step": "02"},
                "STATE_MACHINE_JSON": {
                    "type": "run_output",
                    "path": "01_state_machine.json",
                    "producer_step": "01",
                },
            },
        ),
        StepSpec(
            number=3,
            prompt_template="domains/store_verify/prompts/03_generate_testcases.md",
            prompt_file="step_03_prompt.txt",
            output_file="03_testcases_raw.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "03"},
                "KB_CONTEXT": {"type": "kb_context", "step": "03"},
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
                "API_CONTRACT_DOC": {"type": "static", "path": "domains/store_verify/design/api_contract.md"},
                "RULES_DOC": {"type": "static", "path": "domains/store_verify/design/rules.md"},
            },
        ),
        StepSpec(
            number=4,
            prompt_template="domains/store_verify/prompts/04_review_refine.md",
            prompt_file="step_04_prompt.txt",
            output_file="04_testcases_refined.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "04"},
                "KB_CONTEXT": {"type": "kb_context", "step": "04"},
                "TESTCASES_JSON": {
                    "type": "run_output",
                    "path": "03_testcases_raw.json",
                    "producer_step": "03",
                },
            },
        ),
        StepSpec(
            number=5,
            prompt_template="domains/store_verify/prompts/05_build_regression.md",
            prompt_file="step_05_prompt.txt",
            output_file="05_regression_suite.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "05"},
                "KB_CONTEXT": {"type": "kb_context", "step": "05"},
                "TESTCASES_REFINED_JSON": {
                    "type": "run_output",
                    "path": "04_testcases_refined.json",
                    "producer_step": "04",
                },
            },
        ),
        StepSpec(
            number=6,
            prompt_template="domains/store_verify/prompts/06_release_checklist.md",
            prompt_file="step_06_prompt.txt",
            output_file="06_release_checklist.md",
            output_format="Markdown",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "06"},
                "KB_CONTEXT": {"type": "kb_context", "step": "06"},
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
    ],
    "didaunao_release_audit": [
        StepSpec(
            number=1,
            prompt_template="domains/didaunao_release_audit/prompts/01_extract_state_machine.md",
            prompt_file="step_01_prompt.txt",
            output_file="01_state_machine.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "01"},
                "KB_CONTEXT": {"type": "kb_context", "step": "01"},
                "API_CONTRACT_DOC": {
                    "type": "static",
                    "path": "domains/didaunao_release_audit/design/api_contract.md",
                },
                "RULES_DOC": {
                    "type": "static",
                    "path": "domains/didaunao_release_audit/design/rules.md",
                },
            },
        ),
        StepSpec(
            number=2,
            prompt_template="domains/didaunao_release_audit/prompts/02_build_rule_matrix.md",
            prompt_file="step_02_prompt.txt",
            output_file="02_rule_matrix.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "02"},
                "KB_CONTEXT": {"type": "kb_context", "step": "02"},
                "STATE_MACHINE_JSON": {
                    "type": "run_output",
                    "path": "01_state_machine.json",
                    "producer_step": "01",
                },
            },
        ),
        StepSpec(
            number=3,
            prompt_template="domains/didaunao_release_audit/prompts/03_generate_testcases.md",
            prompt_file="step_03_prompt.txt",
            output_file="03_testcases_raw.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "03"},
                "KB_CONTEXT": {"type": "kb_context", "step": "03"},
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
                "API_CONTRACT_DOC": {
                    "type": "static",
                    "path": "domains/didaunao_release_audit/design/api_contract.md",
                },
                "RULES_DOC": {
                    "type": "static",
                    "path": "domains/didaunao_release_audit/design/rules.md",
                },
            },
        ),
        StepSpec(
            number=4,
            prompt_template="domains/didaunao_release_audit/prompts/04_review_refine.md",
            prompt_file="step_04_prompt.txt",
            output_file="04_testcases_refined.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "04"},
                "KB_CONTEXT": {"type": "kb_context", "step": "04"},
                "TESTCASES_JSON": {
                    "type": "run_output",
                    "path": "03_testcases_raw.json",
                    "producer_step": "03",
                },
            },
        ),
        StepSpec(
            number=5,
            prompt_template="domains/didaunao_release_audit/prompts/05_build_regression.md",
            prompt_file="step_05_prompt.txt",
            output_file="05_regression_suite.json",
            output_format="JSON",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "05"},
                "KB_CONTEXT": {"type": "kb_context", "step": "05"},
                "TESTCASES_REFINED_JSON": {
                    "type": "run_output",
                    "path": "04_testcases_refined.json",
                    "producer_step": "04",
                },
            },
        ),
        StepSpec(
            number=6,
            prompt_template="domains/didaunao_release_audit/prompts/06_release_checklist.md",
            prompt_file="step_06_prompt.txt",
            output_file="06_release_checklist.md",
            output_format="Markdown",
            replacements={
                "KB_CONTEXT_PATH": {"type": "kb_context_path", "step": "06"},
                "KB_CONTEXT": {"type": "kb_context", "step": "06"},
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
    ],
}


class ManualDomainRunner:
    def __init__(
        self,
        repo_root: Path,
        *,
        domain: str,
        run_id: str | None = None,
        allow_incomplete: bool = False,
        runner_name: str = "run_domain_manual",
    ) -> None:
        if domain not in DOMAIN_MODES:
            raise ValueError(f"Unsupported domain: {domain}")
        self.repo_root = repo_root
        self.domain = domain
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = resolve_output_dir(domain, self.run_id)
        self.allow_incomplete = allow_incomplete
        self.runner_name = runner_name
        self.mode = DOMAIN_MODES[domain]["mode"]
        self.kb_enabled = bool(DOMAIN_MODES[domain]["kb_enabled"])
        self.steps = DOMAIN_STEPS[domain]

    def run(self) -> Path:
        self.ensure_required_files()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.write_run_meta()
        self.write_run_guide()
        self.ensure_output_placeholders()
        self.write_kb_context_files()
        self.write_prompt_files()
        return self.run_dir

    def ensure_required_files(self) -> None:
        required_paths = [step.prompt_template for step in self.steps]
        for step in self.steps:
            for source in step.replacements.values():
                if source["type"] == "static":
                    required_paths.append(source["path"])
        missing = [path for path in sorted(set(required_paths)) if not (self.repo_root / path).exists()]
        if missing:
            lines = "\n".join(f"- {path}" for path in missing)
            raise FileNotFoundError(f"Missing required files:\n{lines}")

    def write_run_meta(self) -> None:
        payload = {
            "domain": self.domain,
            "run_id": self.run_id,
            "allow_incomplete": self.allow_incomplete,
            "runner": self.runner_name,
            "mode": self.mode,
            "kb_enabled": self.kb_enabled,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.run_dir / "run_meta.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def write_run_guide(self) -> None:
        command = (
            f"python scripts/run_order_manual.py --run-id {self.run_id}"
            if self.domain == "order"
            else f"python scripts/run_domain_manual.py --domain {self.domain} --run-id {self.run_id}"
        )
        lines = [
            f"Manual {self.domain} pipeline run: {self.run_id}",
            "",
            "Workflow:",
            "1. Open the next step_XX_prompt.txt file in this folder.",
            "2. Paste the full prompt into ChatGPT or Codex.",
            "3. Replace the matching output file contents with only the model output.",
            f"4. Rerun: {command}",
            f"5. Validate JSON outputs with: python scripts/validate_outputs.py outputs/{self.domain}/{self.run_id}",
            "6. Use --allow-incomplete only if you intentionally want downstream prompts with pending-input markers.",
            "",
            "Output files for this run:",
        ]
        lines.extend(CANONICAL_OUTPUTS)
        if self.kb_enabled:
            lines.extend(
                [
                    "",
                    "KB context files:",
                    "kb_context_step01.txt",
                    "kb_context_step02.txt",
                    "kb_context_step03.txt",
                    "kb_context_step04.txt",
                    "kb_context_step05.txt",
                    "kb_context_step06.txt",
                ]
            )
        (self.run_dir / "HOW_TO_USE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def ensure_output_placeholders(self) -> None:
        for step in self.steps:
            output_path = self.run_dir / step.output_file
            if output_path.exists():
                continue
            output_path.write_text(self.placeholder_text(step), encoding="utf-8")

    def placeholder_text(self, step: StepSpec) -> str:
        rerun = (
            f"python scripts/run_order_manual.py --run-id {self.run_id}"
            if self.domain == "order"
            else f"python scripts/run_domain_manual.py --domain {self.domain} --run-id {self.run_id}"
        )
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
                f"4. Rerun: {rerun}",
            ]
        )

    def write_kb_context_files(self) -> None:
        if not self.kb_enabled:
            return
        if not self.kb_index_ready():
            if not self.allow_incomplete:
                raise RuntimeError(
                    "KB index is missing for this domain. "
                    f"Run 'python kb/build_kb.py --domain {self.domain}' first, or rerun with --allow-incomplete."
                )
            for step in self.steps:
                self.kb_context_path(step.number).write_text(
                    self.pending_kb_message(),
                    encoding="utf-8",
                )
            return

        for step in self.steps:
            content = generate_prompt_pack(self.domain, f"{step.number:02d}")
            self.kb_context_path(step.number).write_text(content, encoding="utf-8")

    def kb_index_ready(self) -> bool:
        try:
            manifest, _ = load_index_bundle(self.domain)
        except RuntimeError:
            return False
        backend = str(manifest.get("backend", ""))
        if backend == "faiss":
            return (self.repo_root / "kb" / "index" / self.domain / "faiss.index").exists()
        if backend == "hnsw":
            return (self.repo_root / "kb" / "index" / self.domain / "hnsw.bin").exists()
        return False

    def pending_kb_message(self) -> str:
        return "\n".join(
            [
                f"[PENDING INPUT: KB index for domain '{self.domain}' is not built yet.]",
                f"Run: python kb/build_kb.py --domain {self.domain}",
                "Then rerun the manual runner to refresh the KB context files.",
            ]
        )

    def write_prompt_files(self) -> None:
        for step in self.steps:
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
        if source_type == "kb_context":
            return self.read_kb_context(source["step"], current_step)
        if source_type == "kb_context_path":
            return str(self.kb_context_path(int(source["step"])).resolve())
        raise ValueError(f"Unsupported source type: {source_type}")

    def read_kb_context(self, step: str, current_step: int) -> str:
        path = self.kb_context_path(int(step))
        if not path.exists():
            if self.allow_incomplete:
                return self.pending_kb_message()
            raise RuntimeError(
                f"Cannot compose step {current_step:02d}: missing KB context file '{path.name}'."
            )
        text = self.read_text(path)
        if self.is_pending(text):
            if self.allow_incomplete:
                return text
            raise RuntimeError(
                "Cannot compose a prompt because the KB context is still pending. "
                f"Refresh the KB index for domain '{self.domain}' and rerun."
            )
        return text

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
                    f"Complete step {producer_step} first, save it to outputs/{self.domain}/{self.run_id}/{filename}, then rerun.",
                    "If you intentionally want downstream prompts with pending markers, rerun with --allow-incomplete.",
                ]
            )
        )

    def pending_input_message(self, filename: str, producer_step: str) -> str:
        rerun = (
            f"python scripts/run_order_manual.py --run-id {self.run_id}"
            if self.domain == "order"
            else f"python scripts/run_domain_manual.py --domain {self.domain} --run-id {self.run_id}"
        )
        return "\n".join(
            [
                f"[PENDING INPUT: {filename} is not filled yet.]",
                f"Replace outputs/{self.domain}/{self.run_id}/{filename} with the model output from step {producer_step}.",
                f"Then rerun: {rerun}",
            ]
        )

    def kb_context_path(self, step_number: int) -> Path:
        return self.run_dir / f"kb_context_step{step_number:02d}.txt"

    def print_prompt(self, step: StepSpec, prompt_text: str) -> None:
        separator = "=" * 80
        safe_print(separator)
        safe_print(f"{self.domain.upper()} STEP {step.number:02d} PROMPT -> {step.output_file}")
        safe_print(separator)
        safe_print(prompt_text)
        safe_print("")

    @staticmethod
    def is_placeholder(text: str) -> bool:
        return text.lstrip().startswith(PLACEHOLDER_MARKER)

    @staticmethod
    def is_pending(text: str) -> bool:
        return text.lstrip().startswith(PENDING_INPUT_PREFIX)

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
    parser = argparse.ArgumentParser(description="Generate manual pipeline prompts for a domain.")
    parser.add_argument("--domain", required=True, choices=sorted(DOMAIN_MODES.keys()))
    parser.add_argument("--run-id", help="Resume or regenerate an existing run folder.")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Generate downstream prompts with pending-input markers instead of aborting on missing upstream artifacts.",
    )
    return parser.parse_args()


def run_manual_flow(
    *,
    domain: str,
    run_id: str | None,
    allow_incomplete: bool,
    runner_name: str = "run_domain_manual",
) -> Path:
    runner = ManualDomainRunner(
        repo_root=REPO_ROOT,
        domain=domain,
        run_id=run_id,
        allow_incomplete=allow_incomplete,
        runner_name=runner_name,
    )
    return runner.run()


def main() -> int:
    args = parse_args()
    run_dir = run_manual_flow(
        domain=args.domain,
        run_id=args.run_id,
        allow_incomplete=args.allow_incomplete,
    )
    print(f"Run folder ready: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
